# Wildfire Intelligence Platform - Deployment Guide

This guide covers deployment of the complete Wildfire Intelligence Platform with all integrated components.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Deployment](#local-development-deployment)
3. [Kubernetes Production Deployment](#kubernetes-production-deployment)
4. [Service Configuration](#service-configuration)
5. [Verification & Testing](#verification--testing)
6. [Monitoring & Troubleshooting](#monitoring--troubleshooting)

---

## Prerequisites

### Required Software

- **Docker** (20.10+)
- **Docker Compose** (2.0+)
- **Kubernetes** (1.25+) - for production
- **kubectl** - Kubernetes CLI
- **Python** (3.10+)
- **Node.js** (18+)
- **Git**

### API Keys Required

Obtain the following API keys before deployment:

1. **NASA FIRMS Map Key**
   - Register at: https://firms.modaps.eosdis.nasa.gov/api/area/
   - Used for: Active fire detection data

2. **USGS Credentials** (optional)
   - Register at: https://ers.cr.usgs.gov/register
   - Used for: Landsat satellite imagery

3. **Copernicus Credentials** (optional)
   - Register at: https://scihub.copernicus.eu/
   - Used for: Sentinel satellite imagery

---

## Local Development Deployment

### 1. Clone Repository

```bash
git clone <repository-url>
cd wildfire-intelligence-platform
```

### 2. Configure Environment

Create `.env` file:

```bash
# Database
POSTGRES_DB=wildfire_db
POSTGRES_USER=wildfire_user
POSTGRES_PASSWORD=your_secure_password_here

# Redis
REDIS_PASSWORD=your_redis_password_here

# S3/MinIO
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# API Keys
FIRMS_MAP_KEY=your_nasa_firms_key
USGS_USERNAME=your_usgs_username
USGS_PASSWORD=your_usgs_password
COPERNICUS_USERNAME=your_copernicus_username
COPERNICUS_PASSWORD=your_copernicus_password

# NOAA API
NOAA_USER_AGENT=WildfireIntelligence/1.0 (your_email@example.com)
```

### 3. Start Infrastructure

```bash
# Start PostgreSQL, Redis, Kafka, MinIO
docker-compose up -d postgres redis zookeeper kafka minio
```

### 4. Initialize Database

```bash
# Run database migrations
python scripts/init_database.py
```

### 5. Start Backend Services

```bash
# Data Ingestion Service
docker-compose up -d data-ingestion-service

# Data Storage Service
docker-compose up -d data-storage-service

# Data Consumption Service
docker-compose up -d data-consumption-service

# Fire Risk Service
docker-compose up -d fire-risk-service
```

### 6. Start Frontend

```bash
cd frontend/fire-chief-dashboard
npm install
npm start
```

### 7. Verify Deployment

```bash
# Check service health
curl http://localhost:8001/health  # Data Ingestion
curl http://localhost:8004/health  # Data Consumption
curl http://localhost:8003/health  # Fire Risk

# Check frontend
open http://localhost:3000
```

---

## Kubernetes Production Deployment

### 1. Prepare Cluster

Ensure you have a Kubernetes cluster with:
- **Minimum**: 32 CPU cores, 64GB RAM
- **Storage**: Persistent volume provisioner
- **Networking**: LoadBalancer support

### 2. Configure Secrets

Edit `k8s/overlays/production/secrets.env`:

```bash
# Create secrets file
cat > k8s/overlays/production/secrets.env <<EOF
database=wildfire_db
username=wildfire_user
password=YOUR_PRODUCTION_PASSWORD
EOF

# Create API keys file
cat > k8s/overlays/production/api-keys.env <<EOF
firms-map-key=YOUR_NASA_FIRMS_KEY
usgs-username=YOUR_USGS_USERNAME
usgs-password=YOUR_USGS_PASSWORD
copernicus-username=YOUR_COPERNICUS_USERNAME
copernicus-password=YOUR_COPERNICUS_PASSWORD
EOF
```

### 3. Build Docker Images

```bash
# Build all service images
docker build -t wildfire/data-ingestion-service:latest ./services/data-ingestion-service
docker build -t wildfire/data-consumption-service:latest ./services/data-consumption-service
docker build -t wildfire/fire-risk-service:latest ./services/fire-risk-service
docker build -t wildfire/fire-chief-dashboard:latest ./frontend/fire-chief-dashboard

# Push to container registry
docker tag wildfire/data-ingestion-service:latest YOUR_REGISTRY/wildfire/data-ingestion-service:latest
docker push YOUR_REGISTRY/wildfire/data-ingestion-service:latest
# Repeat for all images
```

### 4. Deploy to Kubernetes

```bash
# Apply production configuration
kubectl apply -k k8s/overlays/production

# Wait for all pods to be ready
kubectl wait --for=condition=ready pod --all -n wildfire-platform --timeout=300s

# Check deployment status
kubectl get pods -n wildfire-platform
```

### 5. Expose Services

```bash
# Get LoadBalancer IP for frontend
kubectl get svc frontend -n wildfire-platform

# Output:
# NAME       TYPE           CLUSTER-IP      EXTERNAL-IP      PORT(S)
# frontend   LoadBalancer   10.96.100.123   203.0.113.10     80:30123/TCP

# Access dashboard at: http://203.0.113.10
```

---

## Service Configuration

### Data Ingestion Service (Port 8001)

**Configuration** (`services/data-ingestion-service/config.yaml`):

```yaml
data_sources:
  nasa_firms:
    enabled: true
    interval_minutes: 15

  noaa_raws:
    enabled: true
    interval_minutes: 30

  firesat_nost:
    enabled: true
    interval_minutes: 10

  terrain:
    enabled: true
    cache_ttl_hours: 24

  infrastructure:
    enabled: true
    cache_ttl_hours: 168  # 1 week

kafka:
  bootstrap_servers: kafka:9092
  topics:
    - firms.detections
    - noaa.weather
    - firesat.detections
    - terrain.elevation
    - infrastructure.osm
```

### Fire Risk Service (Port 8003)

**Configuration** (`services/fire-risk-service/config.yaml`):

```yaml
models:
  ensemble_weights:
    baseline: 0.20
    lstm_temporal: 0.25
    cnn_satellite: 0.20
    firesat_realtime: 0.35

risk_thresholds:
  low: 0.2
  medium: 0.5
  high: 0.8
  extreme: 1.0

cache:
  ttl_seconds: 300
  max_size: 10000
```

---

## Verification & Testing

### 1. Run Integration Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run integration tests
cd tests/integration
pytest test_end_to_end_pipeline.py -v
```

### 2. Run Performance Benchmarks

```bash
cd tests/performance
python benchmark_fire_risk.py
```

Expected results:
- **Single prediction latency**: < 500ms (p95)
- **Concurrent load**: 50+ requests/second
- **Pipeline latency**: < 10 seconds (ingestion → consumption)

### 3. Verify Data Flow

```bash
# Trigger FireSat ingestion
curl -X POST http://localhost:8001/ingest/firesat/manual

# Wait 5 seconds, then check consumption
curl http://localhost:8004/consume/latest/firesat_detections?limit=10

# Request fire risk prediction
curl -X POST http://localhost:8003/predict \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 38.5816,
    "longitude": -121.4944,
    "temperature_c": 35.0,
    "relative_humidity": 15.0,
    "wind_speed": 20.0
  }'
```

---

## Monitoring & Troubleshooting

### View Service Logs

**Docker Compose**:
```bash
docker-compose logs -f fire-risk-service
docker-compose logs -f data-ingestion-service
```

**Kubernetes**:
```bash
kubectl logs -n wildfire-platform -l app=fire-risk-service --tail=100 -f
kubectl logs -n wildfire-platform -l app=data-ingestion-service --tail=100 -f
```

### Common Issues

#### 1. FireSat No Detections

**Symptom**: `/consume/latest/firesat_detections` returns empty array

**Solutions**:
- Check NOS Testbed simulator is running
- Verify orbital mechanics allow California coverage
- Check Kafka topic: `docker exec -it wildfire-kafka kafka-console-consumer --topic firesat.detections --from-beginning`

#### 2. High Prediction Latency

**Symptom**: Fire risk predictions take > 2 seconds

**Solutions**:
- Scale fire-risk-service: `kubectl scale deployment fire-risk-service --replicas=10`
- Check Redis cache: `redis-cli -h localhost -p 6379 PING`
- Review database query performance

#### 3. Kafka Message Backlog

**Symptom**: Messages not being consumed

**Solutions**:
- Check consumer group lag: `kafka-consumer-groups --group storage-service --describe`
- Scale data-storage-service replicas
- Increase Kafka partition count

### Health Dashboard

Access PgAdmin for database monitoring:
```
URL: http://localhost:5050
Email: admin@wildfire.gov
Password: admin123
```

---

## Scaling Guidelines

### Horizontal Scaling (Kubernetes)

All services have HorizontalPodAutoscaler configured:

```bash
# View HPA status
kubectl get hpa -n wildfire-platform

# Manually scale service
kubectl scale deployment fire-risk-service -n wildfire-platform --replicas=20
```

### Resource Limits

Recommended production resource allocation:

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|-------------|-----------|----------------|--------------|
| fire-risk-service | 1000m | 4000m | 2Gi | 8Gi |
| data-ingestion-service | 250m | 1000m | 512Mi | 2Gi |
| data-consumption-service | 250m | 1000m | 512Mi | 2Gi |
| postgres | 1000m | 4000m | 2Gi | 8Gi |
| kafka | 500m | 2000m | 1Gi | 4Gi |

---

## Production Checklist

Before going to production:

- [ ] Update all default passwords
- [ ] Configure TLS/SSL certificates
- [ ] Set up automated backups (PostgreSQL, MinIO)
- [ ] Configure monitoring (Prometheus + Grafana)
- [ ] Set up log aggregation (ELK/Loki)
- [ ] Configure alerting rules
- [ ] Review and update resource limits
- [ ] Enable pod security policies
- [ ] Configure network policies
- [ ] Set up disaster recovery plan
- [ ] Document incident response procedures

---

## Support

For issues or questions:
- GitHub Issues: <repository-url>/issues
- Documentation: `/docs`
- Integration Tests: `/tests/integration`
