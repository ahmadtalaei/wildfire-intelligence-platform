# Deployment Architecture

## Overview

This document outlines the deployment architecture for the Wildfire Intelligence Platform across different environments (development, staging, production) and infrastructure platforms (local, cloud, hybrid).

## Environment Strategy

### 1. Environment Progression

```mermaid
graph LR
    A[Development] --> B[Staging]
    B --> C[Production]
    
    A --> D[Feature Testing]
    B --> E[Integration Testing]
    C --> F[Production Monitoring]
    
    D --> G[Unit Tests]
    E --> H[E2E Tests]
    F --> I[Health Monitoring]
```

### 2. Environment Specifications

| Environment | Purpose | Infrastructure | Data | Monitoring |
|-------------|---------|---------------|------|------------|
| Development | Feature development | Local Docker Compose | Mock/Sample data | Basic logging |
| Staging | Integration testing | Kubernetes (single cluster) | Production-like data | Full monitoring |
| Production | Live system | Multi-region Kubernetes | Live data streams | Advanced monitoring |

## Development Environment

### 1. Local Docker Compose Setup

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  # Infrastructure Services
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: wildfire_dev
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - dev_postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
  
  kafka:
    image: confluentinc/cp-kafka:7.4.0
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"
    depends_on:
      - zookeeper
  
  # Application Services (with hot reloading)
  data-ingestion-service:
    build:
      context: ./services/data-ingestion-service
      dockerfile: Dockerfile.dev
    volumes:
      - ./services/data-ingestion-service/src:/app/src
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
      - DATABASE_URL=postgresql://dev_user:dev_password@postgres:5432/wildfire_dev
    ports:
      - "8002:8000"
    command: uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

volumes:
  dev_postgres_data:
```

### 2. Development Workflow

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Run service in development mode (hot reload)
cd services/data-ingestion-service
python -m uvicorn src.main:app --reload

# Run tests
pytest tests/

# Code quality checks
black src/
flake8 src/
mypy src/
```

### 3. Development Configuration

```yaml
# config/development.yml
database:
  url: "postgresql://dev_user:dev_password@localhost:5432/wildfire_dev"
  echo_sql: true
  
kafka:
  bootstrap_servers: ["localhost:9092"]
  auto_create_topics: true
  
external_apis:
  nasa_firms:
    base_url: "https://firms.modaps.eosdis.nasa.gov"
    api_key: "mock_api_key"
    use_mock: true
  
  copernicus_cds:
    base_url: "https://cds.climate.copernicus.eu/api"
    use_mock: true

logging:
  level: "DEBUG"
  format: "detailed"
  
monitoring:
  enabled: false
```

## Staging Environment

### 1. Kubernetes Staging Cluster

```yaml
# k8s/staging/namespace.yml
apiVersion: v1
kind: Namespace
metadata:
  name: wildfire-staging
  labels:
    environment: staging
    project: wildfire-intelligence

---
# k8s/staging/configmap.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: wildfire-config
  namespace: wildfire-staging
data:
  environment: "staging"
  database_url: "postgresql://staging_user:${DB_PASSWORD}@postgres-service:5432/wildfire_staging"
  kafka_bootstrap_servers: "kafka-service:9092"
  log_level: "INFO"

---
# k8s/staging/secrets.yml
apiVersion: v1
kind: Secret
metadata:
  name: wildfire-secrets
  namespace: wildfire-staging
type: Opaque
data:
  db_password: <base64-encoded-password>
  nasa_api_key: <base64-encoded-key>
  cds_api_key: <base64-encoded-key>
```

### 2. Service Deployments

```yaml
# k8s/staging/data-ingestion-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-ingestion-service
  namespace: wildfire-staging
  labels:
    app: data-ingestion-service
    version: v1.0.0
spec:
  replicas: 2
  selector:
    matchLabels:
      app: data-ingestion-service
  template:
    metadata:
      labels:
        app: data-ingestion-service
    spec:
      containers:
      - name: data-ingestion
        image: wildfire/data-ingestion-service:staging-latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "staging"
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: wildfire-config
              key: database_url
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: wildfire-secrets
              key: db_password
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: data-ingestion-service
  namespace: wildfire-staging
spec:
  selector:
    app: data-ingestion-service
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

### 3. Infrastructure Services

```yaml
# k8s/staging/postgres.yml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: wildfire-staging
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: wildfire_staging
        - name: POSTGRES_USER
          value: staging_user
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: wildfire-secrets
              key: db_password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi
```

### 4. Ingress Configuration

```yaml
# k8s/staging/ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: wildfire-ingress
  namespace: wildfire-staging
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-staging"
spec:
  tls:
  - hosts:
    - staging.wildfire.calfire.gov
    secretName: wildfire-tls
  rules:
  - host: staging.wildfire.calfire.gov
    http:
      paths:
      - path: /api/ingest
        pathType: Prefix
        backend:
          service:
            name: data-ingestion-service
            port:
              number: 8000
      - path: /api/risk
        pathType: Prefix
        backend:
          service:
            name: fire-risk-service
            port:
              number: 8000
```

## Production Environment

### 1. Multi-Region Deployment Strategy

```mermaid
graph TD
    subgraph "Primary Region (us-west-1)"
    A[Load Balancer] --> B[API Gateway Cluster]
    B --> C[Microservices Cluster]
    C --> D[Database Primary]
    C --> E[Kafka Cluster]
    end
    
    subgraph "Secondary Region (us-west-2)"
    F[Load Balancer] --> G[API Gateway Cluster]
    G --> H[Microservices Cluster]
    H --> I[Database Replica]
    H --> J[Kafka Cluster]
    end
    
    D --> I
    E --> J
    
    K[Global DNS] --> A
    K --> F
```

### 2. High Availability Configuration

```yaml
# k8s/production/cluster-autoscaler.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  template:
    spec:
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.21.0
        name: cluster-autoscaler
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/wildfire-production
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false

---
# k8s/production/horizontal-pod-autoscaler.yml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: data-ingestion-hpa
  namespace: wildfire-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: data-ingestion-service
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: kafka_consumer_lag
      target:
        type: AverageValue
        averageValue: "1000"
```

### 3. Database Production Setup

```yaml
# k8s/production/postgres-cluster.yml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster
  namespace: wildfire-production
spec:
  instances: 3
  
  postgresql:
    parameters:
      max_connections: "200"
      shared_buffers: "256MB"
      effective_cache_size: "1GB"
      maintenance_work_mem: "64MB"
      checkpoint_completion_target: "0.9"
      wal_buffers: "16MB"
      default_statistics_target: "100"
      random_page_cost: "1.1"
      effective_io_concurrency: "200"
  
  bootstrap:
    initdb:
      database: wildfire_production
      owner: wildfire_user
      secret:
        name: postgres-credentials
  
  storage:
    size: 100Gi
    storageClass: fast-ssd
  
  monitoring:
    enabled: true
  
  backup:
    retention: "30d"
    barmanObjectStore:
      destinationPath: "s3://wildfire-backups/postgres"
      s3Credentials:
        accessKeyId:
          name: backup-credentials
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: backup-credentials
          key: SECRET_ACCESS_KEY
```

### 4. Service Mesh Configuration (Istio)

```yaml
# k8s/production/istio-gateway.yml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: wildfire-gateway
  namespace: wildfire-production
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: wildfire-tls-credential
    hosts:
    - api.wildfire.calfire.gov

---
# Virtual Service for traffic routing
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: wildfire-api
  namespace: wildfire-production
spec:
  hosts:
  - api.wildfire.calfire.gov
  gateways:
  - wildfire-gateway
  http:
  - match:
    - uri:
        prefix: /api/ingest
    route:
    - destination:
        host: data-ingestion-service
        port:
          number: 8000
      weight: 90
    - destination:
        host: data-ingestion-service-canary
        port:
          number: 8000
      weight: 10
    fault:
      delay:
        percentage:
          value: 0.1
        fixedDelay: 5s
    retries:
      attempts: 3
      perTryTimeout: 10s

---
# Destination Rule for circuit breaker
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: data-ingestion-circuit-breaker
  namespace: wildfire-production
spec:
  host: data-ingestion-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

## Continuous Integration/Continuous Deployment (CI/CD)

### 1. GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy Wildfire Platform

on:
  push:
    branches: [main, staging]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r services/data-ingestion-service/requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        cd services/data-ingestion-service
        pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-west-1
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build and push Docker images
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: wildfire/data-ingestion-service
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG services/data-ingestion-service/
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

  deploy-staging:
    if: github.ref == 'refs/heads/staging'
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to staging
      run: |
        aws eks update-kubeconfig --name wildfire-staging-cluster --region us-west-1
        kubectl set image deployment/data-ingestion-service \
          data-ingestion=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
          -n wildfire-staging
        kubectl rollout status deployment/data-ingestion-service -n wildfire-staging

  deploy-production:
    if: github.ref == 'refs/heads/main'
    needs: build
    runs-on: ubuntu-latest
    environment: production
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to production (canary)
      run: |
        aws eks update-kubeconfig --name wildfire-production-cluster --region us-west-1
        # Deploy canary version (10% traffic)
        kubectl set image deployment/data-ingestion-service-canary \
          data-ingestion=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
          -n wildfire-production
        kubectl rollout status deployment/data-ingestion-service-canary -n wildfire-production
    
    - name: Wait for manual approval
      uses: trstringer/manual-approval@v1
      with:
        secret: ${{ github.TOKEN }}
        approvers: fire-chief,system-admin
    
    - name: Promote to production (100% traffic)
      run: |
        kubectl set image deployment/data-ingestion-service \
          data-ingestion=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
          -n wildfire-production
        kubectl rollout status deployment/data-ingestion-service -n wildfire-production
```

### 2. GitOps with ArgoCD

```yaml
# argocd/applications/wildfire-staging.yml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: wildfire-staging
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/calfire/wildfire-intelligence-platform
    targetRevision: staging
    path: k8s/staging
  destination:
    server: https://kubernetes.default.svc
    namespace: wildfire-staging
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true

---
# argocd/applications/wildfire-production.yml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: wildfire-production
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/calfire/wildfire-intelligence-platform
    targetRevision: main
    path: k8s/production
  destination:
    server: https://kubernetes.default.svc
    namespace: wildfire-production
  syncPolicy:
    syncOptions:
    - CreateNamespace=true
    # Manual sync for production
```

## Infrastructure as Code (IaC)

### 1. Terraform AWS Infrastructure

```hcl
# terraform/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "wildfire-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-west-1"
  }
}

# EKS Cluster
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  
  cluster_name    = "wildfire-production"
  cluster_version = "1.27"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  node_groups = {
    primary = {
      desired_capacity = 3
      max_capacity     = 20
      min_capacity     = 3
      
      instance_types = ["m5.large"]
      
      labels = {
        Environment = "production"
        Application = "wildfire"
      }
    }
    
    ml_workloads = {
      desired_capacity = 1
      max_capacity     = 5
      min_capacity     = 0
      
      instance_types = ["p3.2xlarge"]  # GPU instances
      
      labels = {
        NodeType = "ml-compute"
      }
      
      taints = [
        {
          key    = "nvidia.com/gpu"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      ]
    }
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "wildfire_db" {
  identifier = "wildfire-production"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.r5.xlarge"
  
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_encrypted     = true
  
  db_name  = "wildfire_production"
  username = "wildfire_user"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "wildfire-production-final-snapshot"
  
  tags = {
    Name = "wildfire-production"
    Environment = "production"
  }
}

# MSK (Kafka) Cluster
resource "aws_msk_cluster" "wildfire_kafka" {
  cluster_name           = "wildfire-production"
  kafka_version          = "3.4.0"
  number_of_broker_nodes = 3
  
  broker_node_group_info {
    instance_type   = "kafka.m5.large"
    client_subnets  = module.vpc.private_subnets
    storage_info {
      ebs_storage_info {
        volume_size = 100
      }
    }
    security_groups = [aws_security_group.kafka.id]
  }
  
  encryption_info {
    encryption_at_rest_kms_key_id = aws_kms_key.kafka.arn
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }
  
  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.kafka.name
      }
    }
  }
  
  tags = {
    Name = "wildfire-production"
    Environment = "production"
  }
}
```

### 2. Monitoring Infrastructure

```hcl
# terraform/monitoring.tf

# CloudWatch Dashboards
resource "aws_cloudwatch_dashboard" "wildfire_overview" {
  dashboard_name = "Wildfire-Production-Overview"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EKS", "cluster_node_count", "ClusterName", "wildfire-production"],
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "wildfire-alb"],
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "wildfire-alb"]
          ]
          period = 300
          stat   = "Average"
          region = "us-west-1"
          title  = "EKS and Load Balancer Metrics"
        }
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "wildfire-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EKS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors EKS CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    ClusterName = "wildfire-production"
  }
}

# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "wildfire-production-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = "ops@calfire.gov"
}
```

## Monitoring and Observability

### 1. Prometheus Configuration

```yaml
# k8s/monitoring/prometheus.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    rule_files:
      - /etc/prometheus/rules/*.yml
    
    alerting:
      alertmanagers:
        - static_configs:
            - targets:
              - alertmanager:9093
    
    scrape_configs:
      - job_name: 'kubernetes-apiservers'
        kubernetes_sd_configs:
        - role: endpoints
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
        relabel_configs:
        - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
          action: keep
          regex: default;kubernetes;https
      
      - job_name: 'wildfire-services'
        kubernetes_sd_configs:
        - role: pod
        relabel_configs:
        - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
          action: keep
          regex: true
        - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
          action: replace
          target_label: __metrics_path__
          regex: (.+)
```

### 2. Grafana Dashboards

```json
{
  "dashboard": {
    "title": "Wildfire Intelligence Platform - Overview",
    "panels": [
      {
        "title": "Data Ingestion Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(data_ingestion_requests_total[5m])",
            "legendFormat": "{{source_type}}"
          }
        ]
      },
      {
        "title": "Service Response Times",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "ML Model Prediction Accuracy",
        "type": "stat",
        "targets": [
          {
            "expr": "ml_model_accuracy",
            "legendFormat": "{{model_name}}"
          }
        ]
      }
    ]
  }
}
```

## Security and Compliance

### 1. Pod Security Standards

```yaml
# k8s/security/pod-security-policy.yml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: wildfire-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

### 2. Network Policies

```yaml
# k8s/security/network-policy.yml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: wildfire-network-policy
  namespace: wildfire-production
spec:
  podSelector:
    matchLabels:
      app: data-ingestion-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: kafka
    ports:
    - protocol: TCP
      port: 9092
```

This comprehensive deployment architecture ensures reliable, scalable, and secure operations across all environments of the Wildfire Intelligence Platform.