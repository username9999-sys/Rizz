# 🚀 DEPLOYMENT GUIDE

**Complete guide for deploying Rizz Platform to production**

---

## 📋 TABLE OF CONTENTS

1. [Prerequisites](#prerequisites)
2. [Production Checklist](#production-checklist)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Backup & Recovery](#backup--recovery)
7. [Monitoring Setup](#monitoring-setup)
8. [Security Hardening](#security-hardening)

---

## ✅ PREREQUISITES

### Required Software
- Docker 20.10+
- Docker Compose 2.0+
- Kubernetes 1.25+ (for K8s deployment)
- Helm 3.0+ (for Helm charts)

### Infrastructure Requirements
- **Minimum:** 8 CPU, 16GB RAM, 100GB Storage
- **Recommended:** 16 CPU, 32GB RAM, 500GB SSD
- **Production:** 32+ CPU, 64GB+ RAM, 1TB+ NVMe

### Domain & SSL
- Domain name configured
- SSL certificates (Let's Encrypt or commercial)
- DNS records configured

---

## ✅ PRODUCTION CHECKLIST

### Before Deployment

- [ ] All tests passing (`npm test` / `pytest`)
- [ ] Code review completed
- [ ] Security scan completed
- [ ] Performance tests passed
- [ ] Documentation updated
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] Backup strategy in place
- [ ] Monitoring configured
- [ ] Rollback plan ready

### Security

- [ ] Change all default passwords
- [ ] Rotate all secrets and keys
- [ ] Enable firewall rules
- [ ] Configure SSL/TLS
- [ ] Enable rate limiting
- [ ] Configure CORS properly
- [ ] Enable security headers
- [ ] Set up WAF (Web Application Firewall)

### Database

- [ ] Database backups configured
- [ ] Replication configured (for HA)
- [ ] Connection pooling configured
- [ ] Indexes optimized
- [ ] Query performance tested

---

## 🐳 DOCKER DEPLOYMENT

### Single Server Deployment

```bash
# 1. Clone repository
git clone https://github.com/username9999-sys/Rizz.git
cd Rizz-Project

# 2. Create .env file
cp .env.example .env
# Edit .env with production values

# 3. Build images
docker-compose build

# 4. Start services
docker-compose up -d

# 5. Check status
docker-compose ps

# 6. View logs
docker-compose logs -f

# 7. Run health checks
curl http://localhost:5000/api/health
```

### Multi-Server Deployment

```bash
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    image: rizz-api:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure
    
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
```

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml rizz

# Check status
docker service ls
docker service ps rizz_api

# Scale service
docker service scale rizz_api=5
```

---

## ☸️ KUBERNETES DEPLOYMENT

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Deploy to Kubernetes

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Create secrets
kubectl create secret generic rizz-secrets \
  --from-literal=jwt-secret='your-secret' \
  --from-literal=db-password='db-password' \
  -n rizz

# 3. Apply configurations
kubectl apply -f k8s/configmap.yaml -n rizz

# 4. Deploy databases
kubectl apply -f k8s/postgres-statefulset.yaml -n rizz
kubectl apply -f k8s/redis-deployment.yaml -n rizz

# 5. Deploy applications
kubectl apply -f k8s/api-deployment.yaml -n rizz
kubectl apply -f k8s/api-service.yaml -n rizz

# 6. Check status
kubectl get pods -n rizz
kubectl get services -n rizz

# 7. Access application
kubectl port-forward svc/rizz-api 5000:5000 -n rizz
```

### Helm Deployment

```bash
# Add Helm repo
helm repo add rizz https://charts.rizz.dev

# Install chart
helm install rizz rizz/rizz-platform \
  --namespace rizz \
  --create-namespace \
  -f values.prod.yaml

# Check status
helm list -n rizz

# Upgrade
helm upgrade rizz rizz/rizz-platform -n rizz -f values.prod.yaml

# Uninstall
helm uninstall rizz -n rizz
```

### Auto-scaling

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: rizz
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 10
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
```

```bash
# Apply HPA
kubectl apply -f k8s/hpa.yaml

# Check HPA
kubectl get hpa -n rizz
```

---

## ☁️ CLOUD DEPLOYMENT

### AWS Deployment

```bash
# Using ECS
aws ecs create-cluster --cluster-name rizz-cluster

# Create task definition
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
  --cluster rizz-cluster \
  --service-name rizz-api \
  --task-definition rizz-api \
  --desired-count 3 \
  --launch-type FARGATE
```

### Google Cloud

```bash
# Using GKE
gcloud container clusters create rizz-cluster \
  --num-nodes=3 \
  --machine-type=e2-standard-4

# Deploy
kubectl apply -f k8s/

# Expose
kubectl expose deployment api \
  --type=LoadBalancer \
  --port=80 \
  --target-port=5000
```

### Azure

```bash
# Using AKS
az aks create \
  --resource-group rizz-rg \
  --name rizz-aks \
  --node-count 3

# Deploy
kubectl apply -f k8s/
```

---

## 💾 BACKUP & RECOVERY

### Database Backup

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# PostgreSQL
pg_dump -U postgres rizz > ${BACKUP_DIR}/postgres_${DATE}.sql

# MongoDB
mongodump --db rizz --out ${BACKUP_DIR}/mongo_${DATE}

# Redis
redis-cli SAVE
cp /var/lib/redis/dump.rdb ${BACKUP_DIR}/redis_${DATE}.rdb

# Compress
tar -czf ${BACKUP_DIR}/backup_${DATE}.tar.gz ${BACKUP_DIR}/*.sql ${BACKUP_DIR}/mongo_* ${BACKUP_DIR}/*.rdb

# Upload to S3
aws s3 cp ${BACKUP_DIR}/backup_${DATE}.tar.gz s3://rizz-backups/

# Keep only last 7 days
find ${BACKUP_DIR} -name "backup_*.tar.gz" -mtime +7 -delete
```

### Automated Backups (Cron)

```bash
# Edit crontab
crontab -e

# Add backup job (daily at 2 AM)
0 2 * * * /path/to/backup.sh
```

### Disaster Recovery

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

# Download from S3
aws s3 cp s3://rizz-backups/${BACKUP_FILE} .

# Extract
tar -xzf ${BACKUP_FILE}

# Restore PostgreSQL
psql -U postgres rizz < postgres_*.sql

# Restore MongoDB
mongorestore mongo_*/

# Restore Redis
cp redis_*.rdb /var/lib/redis/dump.rdb
redis-cli BGSAVE
```

---

## 📊 MONITORING SETUP

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['api:5000']
    metrics_path: '/metrics'
  
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

### Grafana Dashboards

Import these dashboards:
- **API Performance:** ID 10826
- **Node Exporter:** ID 1860
- **PostgreSQL:** ID 9628
- **MongoDB:** ID 2583
- **Redis:** ID 763

### Alert Rules

```yaml
# alert_rules.yml
groups:
- name: rizz_alerts
  rules:
  - alert: HighCPU
    expr: avg(rate(process_cpu_seconds_total[5m])) > 0.8
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage detected"
  
  - alert: ServiceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service {{ $labels.job }} is down"
```

---

## 🔒 SECURITY HARDENING

### Nginx Security Configuration

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.rizz.dev;
    
    # SSL
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'" always;
    
    # Rate Limiting
    limit_req zone=api_limit burst=20 nodelay;
    
    location / {
        proxy_pass http://api:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Firewall Rules (UFW)

```bash
# Enable firewall
ufw enable

# Allow SSH
ufw allow 22/tcp

# Allow HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow specific service ports
ufw allow 5000/tcp  # API
ufw allow 3000/tcp  # Web

# Deny all other incoming
ufw default deny incoming

# Check status
ufw status verbose
```

### Security Scanning

```bash
# Scan Docker images
trivy image rizz-api:latest

# Scan code
npm audit
snyk test

# Scan dependencies
pip-audit
```

---

## 📞 SUPPORT

For deployment issues:
- **Documentation:** DOCS.md
- **GitHub Issues:** https://github.com/username9999-sys/Rizz/issues
- **Email:** support@rizz.dev

---

**Last Updated:** March 2026
