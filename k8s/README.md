# Kubernetes Deployment for Wildfire Intelligence Platform

This directory contains Kubernetes manifests for deploying the Wildfire Intelligence Platform using Kustomize.

## Structure

```
k8s/
├── base/                      # Base configuration
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── postgres-statefulset.yaml
│   ├── redis-deployment.yaml
│   ├── kafka-statefulset.yaml
│   ├── data-ingestion-deployment.yaml
│   ├── data-consumption-deployment.yaml
│   ├── fire-risk-deployment.yaml
│   ├── frontend-deployment.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── production/           # Production overrides
│   └── development/          # Development overrides
└── README.md
```

## Prerequisites

- Kubernetes cluster (1.25+)
- kubectl CLI
- kustomize (v5.0+)
- Persistent volume provisioner

## Quick Start

### Development Deployment

```bash
# Apply base configuration
kubectl apply -k k8s/base

# Verify deployment
kubectl get pods -n wildfire-platform
```

### Production Deployment

```bash
# 1. Update secrets in overlays/production/
# Edit: secrets.env and api-keys.env

# 2. Apply production configuration
kubectl apply -k k8s/overlays/production

# 3. Get LoadBalancer IP
kubectl get svc frontend -n wildfire-platform
```

## Services

| Service | Port | Replicas | HPA Max |
|---------|------|----------|---------|
| frontend | 80 | 2-5 | 10 |
| data-ingestion-service | 8001 | 2-5 | 10 |
| data-consumption-service | 8004 | 2-5 | 15 |
| fire-risk-service | 8003 | 3-10 | 20 |
| postgres | 5432 | 1 | N/A |
| redis | 6379 | 1 | N/A |
| kafka | 9092 | 1 | N/A |

## Horizontal Pod Autoscaling

All application services are configured with HPA based on:
- CPU utilization (60-75%)
- Memory utilization (70-85%)

Fire Risk Service scales most aggressively (3-20 replicas) due to compute-intensive ML predictions.

## Resource Requirements

### Minimum Cluster Resources
- **Development**: 8 CPU cores, 16GB RAM
- **Production**: 32 CPU cores, 64GB RAM

### Storage Requirements
- PostgreSQL: 20GB (dev), 100GB (prod)
- Kafka: 50GB
- Redis: 5GB

## Configuration

### Secrets (MUST UPDATE FOR PRODUCTION)

Edit `k8s/base/secrets.yaml` or use overlay secrets:

```yaml
postgres-secret:
  database: wildfire_db
  username: wildfire_user
  password: CHANGE_ME

api-keys:
  firms-map-key: YOUR_NASA_FIRMS_KEY
  usgs-username: YOUR_USGS_USERNAME
  copernicus-username: YOUR_COPERNICUS_USERNAME
```

### ConfigMap

Common configuration in `k8s/base/configmap.yaml`:
- API base URLs
- Logging levels
- Cache TTL
- Worker counts

## Monitoring

### Health Checks

All services include:
- **Liveness probes**: Restart unhealthy containers
- **Readiness probes**: Remove from load balancing when not ready

### Logs

```bash
# View logs for specific service
kubectl logs -n wildfire-platform -l app=fire-risk-service --tail=100

# Stream logs
kubectl logs -n wildfire-platform -l app=data-ingestion-service -f
```

## Scaling

### Manual Scaling

```bash
# Scale fire-risk-service to 10 replicas
kubectl scale deployment fire-risk-service -n wildfire-platform --replicas=10
```

### Auto-scaling

HPA automatically scales based on metrics. View HPA status:

```bash
kubectl get hpa -n wildfire-platform
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n wildfire-platform
kubectl describe pod <pod-name> -n wildfire-platform
```

### Check Service Connectivity

```bash
# Port-forward to test locally
kubectl port-forward -n wildfire-platform svc/fire-risk-service 8003:8003

# Test endpoint
curl http://localhost:8003/health
```

### Database Issues

```bash
# Connect to PostgreSQL
kubectl exec -it -n wildfire-platform postgres-0 -- psql -U wildfire_user -d wildfire_db

# Check database tables
\dt
```

## Production Considerations

1. **Use external secrets manager**: Replace plaintext secrets with AWS Secrets Manager, HashiCorp Vault, etc.
2. **Enable ingress controller**: Configure Nginx/Traefik for routing
3. **Add TLS**: Use cert-manager for automatic SSL certificates
4. **Configure persistent volumes**: Use cloud provider storage classes
5. **Enable monitoring**: Deploy Prometheus + Grafana
6. **Set resource quotas**: Limit namespace resource usage
7. **Implement network policies**: Restrict pod-to-pod communication

## Cleanup

```bash
# Delete all resources
kubectl delete -k k8s/base

# Or delete namespace (cascading delete)
kubectl delete namespace wildfire-platform
```

## Support

For issues or questions, contact the platform team.
