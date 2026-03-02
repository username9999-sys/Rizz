# 🚀 Rizz Platform - Deployment Guide

**Enterprise-scale deployment guide** untuk production environment.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Helm Deployment](#helm-deployment)
6. [Production Checklist](#production-checklist)
7. [Monitoring & Logging](#monitoring--logging)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Docker** 20.10+
- **Docker Compose** 2.0+
- **kubectl** 1.28+ (for K8s)
- **helm** 3.13+ (for Helm)
- **Python** 3.11+ (for local dev)

### Infrastructure Requirements
- **Minimum**: 2 CPU, 4GB RAM, 20GB Storage
- **Recommended**: 4 CPU, 8GB RAM, 50GB Storage
- **Production**: 8+ CPU, 16GB+ RAM, 100GB+ SSD

---

## Local Development

### Option 1: Docker Compose

```bash
# Clone repository
git clone https://github.com/username9999-sys/Rizz.git
cd Rizz-Project

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Option 2: Local Python Environment

```bash
# Navigate to API server
cd api-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_ENV=development
export DATABASE_URL=postgresql://user:pass@localhost/rizz_api
export SECRET_KEY=dev-secret-key

# Start PostgreSQL (Docker)
docker run -d --name postgres \
  -e POSTGRES_DB=rizz_api \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=pass \
  -p 5432:5432 \
  postgres:15-alpine

# Run migrations
alembic upgrade head

# Start server
python app.py
```

---

## Docker Deployment

### Build Images

```bash
# Build API server
docker build -t rizz-api:latest ./api-server

# Build all services
docker-compose build

# Push to registry
docker tag rizz-api:latest registry.com/rizz-api:latest
docker push registry.com/rizz-api:latest
```

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    image: registry.com/rizz-api:latest
    environment:
      FLASK_ENV: production
      SECRET_KEY: ${SECRET_KEY}
      DATABASE_URL: ${DATABASE_URL}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: always
```

```bash
# Deploy with production config
docker-compose -f docker-compose.prod.yml up -d
```

---

## Kubernetes Deployment

### Manual K8s Deployment

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets (update values first!)
kubectl apply -f k8s/secrets.yaml -n rizz-platform

# Create ConfigMap
kubectl apply -f k8s/configmap.yaml -n rizz-platform

# Deploy PostgreSQL
kubectl apply -f k8s/postgres-statefulset.yaml -n rizz-platform
kubectl apply -f k8s/postgres-service.yaml -n rizz-platform

# Deploy Redis
kubectl apply -f k8s/redis-deployment.yaml -n rizz-platform
kubectl apply -f k8s/redis-service.yaml -n rizz-platform

# Deploy API
kubectl apply -f k8s/api-deployment.yaml -n rizz-platform
kubectl apply -f k8s/api-service.yaml -n rizz-platform

# Deploy Ingress
kubectl apply -f k8s/ingress.yaml -n rizz-platform

# Check deployment
kubectl get all -n rizz-platform
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -n rizz-platform

# Check services
kubectl get svc -n rizz-platform

# View logs
kubectl logs -f deployment/rizz-api -n rizz-platform

# Test health endpoint
kubectl port-forward svc/rizz-api 5000:5000 -n rizz-platform
curl http://localhost:5000/health
```

---

## Helm Deployment

### Install Chart

```bash
# Navigate to helm chart
cd helm/rizz-platform

# Add Helm repo (if publishing)
helm repo add rizz https://your-helm-repo.com
helm repo update

# Install with default values
helm install rizz-release . -n rizz-platform --create-namespace

# Install with custom values
helm install rizz-release . \
  -n rizz-platform \
  --create-namespace \
  --set api.replicaCount=5 \
  --set api.secrets.secretKey=$(openssl rand -hex 32) \
  --set api.secrets.jwtSecretKey=$(openssl rand -hex 32) \
  --set postgresql.auth.password=$(openssl rand -base64 24)

# Install with values file
helm install rizz-release . \
  -n rizz-platform \
  --create-namespace \
  -f values-production.yaml
```

### Upgrade & Rollback

```bash
# Upgrade release
helm upgrade rizz-release . -n rizz-platform

# Rollback to previous version
helm rollback rizz-release -n rizz-platform

# View history
helm history rizz-release -n rizz-platform
```

### Uninstall

```bash
# Uninstall release
helm uninstall rizz-release -n rizz-platform

# Uninstall with PVCs
helm uninstall rizz-release -n rizz-platform --purge
```

---

## Production Checklist

### Security
- [ ] Change all default passwords
- [ ] Generate secure SECRET_KEY and JWT_SECRET_KEY
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure CORS for specific domains
- [ ] Enable rate limiting
- [ ] Review and restrict network policies
- [ ] Enable pod security policies
- [ ] Configure secrets management (Vault/AWS Secrets Manager)

### Database
- [ ] Enable PostgreSQL WAL archiving
- [ ] Configure automated backups
- [ ] Set up replication for HA
- [ ] Tune PostgreSQL configuration (shared_buffers, work_mem)
- [ ] Create database users with minimal privileges

### Monitoring
- [ ] Deploy Prometheus stack
- [ ] Configure alerting rules
- [ ] Set up Grafana dashboards
- [ ] Enable distributed tracing (Jaeger)
- [ ] Configure log aggregation (ELK/Loki)

### Performance
- [ ] Configure HPA for auto-scaling
- [ ] Set resource requests/limits
- [ ] Enable Redis caching
- [ ] Configure database connection pooling
- [ ] Enable CDN for static assets

### High Availability
- [ ] Deploy across multiple availability zones
- [ ] Configure pod disruption budgets
- [ ] Set up load balancing
- [ ] Enable database replication
- [ ] Test failover procedures

---

## Monitoring & Logging

### Prometheus Metrics

Access metrics at: `/metrics`

Key metrics:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `python_gc_collections_total` - Garbage collection

### Grafana Dashboard

Import dashboard ID: (create custom dashboard)

Panels:
- Request rate (req/s)
- Response time (p50, p95, p99)
- Error rate (%)
- CPU/Memory usage
- Database connections
- Cache hit rate

### Log Aggregation

```yaml
# Fluentd configuration example
<match rizz.**>
  @type elasticsearch
  host elasticsearch.logging.svc
  port 9200
  logstash_format true
  logstash_prefix rizz-logs
</match>
```

---

## Troubleshooting

### Common Issues

#### Pod Not Starting
```bash
# Check pod status
kubectl describe pod <pod-name> -n rizz-platform

# View logs
kubectl logs <pod-name> -n rizz-platform

# Check events
kubectl get events -n rizz-platform --sort-by='.lastTimestamp'
```

#### Database Connection Error
```bash
# Test connectivity
kubectl exec -it <pod-name> -n rizz-platform -- \
  psql -h postgres -U rizz_user -d rizz_api

# Check secrets
kubectl get secret rizz-api-secret -n rizz-platform -o jsonpath='{.data.DATABASE_URL}' | base64 -d
```

#### High Memory Usage
```bash
# Check resource usage
kubectl top pods -n rizz-platform

# Adjust limits
kubectl edit deployment rizz-api -n rizz-platform
```

#### Slow Responses
```bash
# Check database queries
kubectl logs -f deployment/rizz-api -n rizz-platform | grep "slow_query"

# Enable query logging in PostgreSQL
kubectl exec -it postgres-0 -n rizz-platform -- \
  psql -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"
```

### Emergency Rollback

```bash
# Kubernetes rollback
kubectl rollout undo deployment/rizz-api -n rizz-platform

# Helm rollback
helm rollback rizz-release -n rizz-platform

# Scale down for emergency
kubectl scale deployment rizz-api --replicas=0 -n rizz-platform
```

---

## Performance Tuning

### PostgreSQL Tuning

```sql
-- Recommended settings for 8GB RAM
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET max_connections = 100;
SELECT pg_reload_conf();
```

### Application Tuning

```python
# gunicorn.conf.py
workers = 4
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5
threads = 2
```

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/username9999-sys/Rizz/issues
- Email: faridalfarizi179@gmail.com
- Documentation: https://github.com/username9999-sys/Rizz/wiki

---

**Version**: 2.0.0  
**Last Updated**: 2024  
**Maintained by**: username9999
