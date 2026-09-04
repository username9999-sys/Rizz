# Scaling Strategy

This document covers horizontal and vertical scaling for the Rizz
platform, from a single host up to multi-region active-active.

## Tiers

### Tier 0: Single Host (current)

  - 1 server, 4-8 GB RAM
  - All services in docker compose
  - Suitable for: development, personal projects, ~100 RPS

### Tier 1: Single Region, Scaled Out

  - 3 API replicas behind nginx
  - 1 Postgres primary + 1 read replica
  - 1 Redis primary
  - 1 Elasticsearch cluster (1-3 nodes)
  - Suitable for: production, ~1k RPS

### Tier 2: Multi-Region, Active-Active

  - 2+ regions, each with full Tier 1 stack
  - GeoDNS or anycast routing
  - Cross-region Postgres replication (logical or BDR)
  - Suitable for: 10k+ RPS, latency-sensitive global users

## Vertical Scaling (Single Host)

Increase container resource limits:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4.0'        # was 1.0
          memory: 2G        # was 512M
```

Useful when:
  - Single request CPU/memory profile is the bottleneck
  - You want to avoid distributed-system complexity

## Horizontal Scaling (Docker Compose)

Scale stateless services (api, portfolio) horizontally:

```bash
# Scale API to 4 replicas
docker compose up -d --scale api=4
```

nginx picks up new replicas via the upstream block (DNS-based discovery
is **not** automatic; you need to list them explicitly OR use
`docker compose run` + service-discovery).

For dynamic scaling, switch to Kubernetes (see below).

## Kubernetes Migration Path

`k8s/` and `helm/` directories contain starter manifests. To migrate:

  1. Provision a Kubernetes cluster (EKS / GKE / AKS / k3s).
  2. Install ingress-nginx + cert-manager.
  3. Apply `helm/` charts.
  4. Migrate persistent volumes (StatefulSet for Postgres/Mongo/Redis).
  5. Configure Horizontal Pod Autoscaler (HPA):

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rizz-api
  namespace: rizz
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rizz-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "500"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 300
```

## Database Scaling

### Postgres (read-heavy workload)

  - Vertical: bump `shared_buffers`, `work_mem`, `effective_cache_size`
  - Horizontal: streaming replication (1 primary, N replicas)
  - Connection pooling: PgBouncer in transaction mode (cuts connections
    by 10x for typical web workloads)
  - Partitioning: large tables (audit_log, events) by time

### MongoDB

  - Replica set for high availability
  - Sharding for collections > 100GB
  - Run `db.adminCommand({serverStatus: 1})` regularly to check
    opcounters and connections

### Redis

  - Sentinel for automatic failover (Tier 1)
  - Cluster mode for >25GB datasets (Tier 2)
  - `maxmemory-policy allkeys-lru` for cache workloads

## Cache Strategy

The `app/utils/cache.py` module (see Week 5-6 commit) provides
cache-aside helpers. Recommended TTLs:

| Data | TTL | Notes |
|------|-----|-------|
| User profile | 5 min | invalidate on update |
| Post listing | 1 min | OK to serve slightly stale |
| Rate-limit counters | per-request |  |
| Session metadata | matches token TTL |  |
| Search results | 10 min | warm cache, long TTL safe |

## CDN

Static assets (logos, fonts, JS bundles) are served through Cloudflare
or AWS CloudFront. See `docs/CDN_SETUP.md` for the configuration. Do
NOT cache authenticated responses.

## Load Balancing

nginx upstream block (already in `nginx.conf`) supports multiple
backends. For sticky sessions (when using Flask sessions), add the
`ip_hash` directive:

```nginx
upstream api_server {
    ip_hash;
    server api1:5000;
    server api2:5000;
    server api3:5000;
}
```

For stateless APIs (which Rizz is — JWT in headers), prefer
`least_conn` or `random` for better distribution.

## When to Scale

Monitor these signals:

  - p95 latency > 500ms sustained
  - CPU > 70% sustained
  - Request queue depth > N (depends on worker count)
  - Postgres connections > 80% of `max_connections`
  - Redis memory > 80% of `maxmemory`

The alerts in `monitoring/prometheus/alerts.yml` already cover most
of these. Tune thresholds for your specific workload.

## Cost Optimization

  - **Reserved instances** for steady-state baseline
  - **Spot/preemptible** for batch workers (analytics, ML training)
  - **Autoscaler scaleDown stabilizationWindowSeconds=300** to avoid
    thrashing and over-scaling
  - Use **S3 + CloudFront** instead of running a static-file nginx
  - **Right-size Postgres** (vertical > horizontal for OLTP up to ~1TB)
