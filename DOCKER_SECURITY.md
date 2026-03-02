# 🔒 DOCKER SECURITY HARDENING GUIDE

**CRITICAL:** Before ANY deployment, you MUST:

## 1. Change ALL Default Passwords

Edit `.env` file with strong passwords:

```bash
# Generate strong passwords
openssl rand -base64 32
python -c "import secrets; print(secrets.token_hex(32))"
```

## 2. Enable Elasticsearch Security

In `docker-compose.yml` or `docker-compose.hyperscale.yml`:

```yaml
elasticsearch:
  environment:
    xpack.security.enabled: "true"  # Change from false!
    ELASTIC_PASSWORD: ${ELASTIC_PASSWORD:-CHANGE_ME}
```

## 3. Disable Vault Dev Mode

```yaml
vault:
  # Remove: command: server -dev
  # Use proper configuration:
  command: server -config=/vault/config/vault.hcl
```

## 4. Enable HTTPS

```yaml
nginx:
  ports:
    - "443:443"  # HTTPS
    - "80:80"    # HTTP (redirect to HTTPS)
  volumes:
    - ./ssl:/etc/nginx/ssl
```

## 5. Non-Root Containers

All Dockerfiles should use non-root users (already implemented):
- ✅ `api-server/Dockerfile` - appuser
- ✅ `web-app/Dockerfile` - nodejs

## 6. Network Isolation

```yaml
networks:
  frontend:
  backend:
  database:

services:
  nginx:
    networks:
      - frontend
  
  api:
    networks:
      - frontend
      - backend
  
  database:
    networks:
      - backend  # Not accessible from frontend!
```

## 7. Resource Limits

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## 8. Health Checks

All services should have health checks (already implemented in most):

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## 9. Logging

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 10. Secrets Management

For production, use Docker Secrets or external vault:

```yaml
secrets:
  db_password:
    external: true
  jwt_secret:
    external: true

services:
  api:
    secrets:
      - db_password
      - jwt_secret
```

---

## ✅ SECURITY CHECKLIST

Before deployment:

- [ ] All passwords changed from defaults
- [ ] Elasticsearch security enabled
- [ ] Vault not in dev mode
- [ ] HTTPS configured
- [ ] Non-root users in containers
- [ ] Network isolation implemented
- [ ] Resource limits set
- [ ] Health checks working
- [ ] Logging configured
- [ ] Secrets managed properly

---

**Status:** 🟡 Partially Implemented  
**Priority:** 🔴 CRITICAL for Production  
