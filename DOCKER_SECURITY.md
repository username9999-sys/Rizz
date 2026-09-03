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

## 🆕 NEW SECURITY FEATURES (2026-09)

### JWT Token Security

All JWT tokens now include enhanced security features:

1. **JTI (JWT ID) Claim** - Unique identifier for each token, enabling revocation
2. **Token Type** - Access vs Refresh tokens clearly distinguished
3. **Redis Blacklist** - Revoked tokens stored with TTL matching expiration
4. **Refresh Token Rotation** - New refresh token issued on each use, old one revoked

**Implementation:**
- Access tokens: 1-hour expiry (configurable via `JWT_ACCESS_TOKEN_EXPIRES_HOURS`)
- Refresh tokens: 30-day expiry (configurable via `JWT_REFRESH_TOKEN_EXPIRES_DAYS`)
- Both include `jti`, `type`, `iss`, `aud` claims

### Email Verification Flow

Secure email verification with signed tokens:

```python
# Token generation (in auth.py register endpoint)
serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
verification_token = serializer.dumps(email, salt='email-verify')
# Token expires after 24 hours
```

**Security Properties:**
- Signed with application secret key
- 24-hour expiration (`max_age=24*3600`)
- Tamper-proof (BadSignature on modification)
- One-time use (verified email marked in database)

### Password Reset Flow

Secure password reset with time-limited tokens:

```python
# Token generation (in request-reset endpoint)
reset_token = serializer.dumps(email, salt='password-reset')
# Token expires after 1 hour
```

**Security Properties:**
- 1-hour expiration (`max_age=2*3600`)
- Same tamper-proof properties as verification tokens
- Rate limited (5 requests/minute)
- Password strength enforced on reset

### Audit Logging

Structured JSON audit logs for all privileged actions:

```json
{
  "timestamp": "2026-09-03T10:00:00.123Z",
  "level": "INFO",
  "action": "USER_LOGIN",
  "user_id": "abc123",
  "ip": "192.168.1.1",
  "request_id": "req-123",
  "details": {
    "username": "testuser",
    "success": true
  }
}
```

**Logged Actions:**
- `USER_REGISTER` - New user registration
- `USER_LOGIN` - Successful login
- `USER_LOGOUT` - Explicit logout
- `TOKEN_REFRESH` - Access token refresh
- `EMAIL_VERIFIED` - Email verification completed
- `PASSWORD_RESET_REQUEST` - Password reset email sent
- `PASSWORD_RESET` - Password changed
- `POST_CREATED` / `POST_UPDATED` / `POST_DELETED` - Content changes
- `ACCOUNT_LOCKED` - Too many failed attempts

**Implementation:**
- Stored in `audit_log` database table
- Emits JSON to application logger
- Includes IP, User-Agent, Request-ID for tracing

### Docker Image Security

Enhanced Dockerfile security practices:

```dockerfile
# Use official base images
FROM python:3.11-slim

# Create non-root user
RUN useradd --no-create-home --uid 1000 appuser

# Install dependencies as root, then switch
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=appuser:appuser . /app

# Switch to non-root
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Run with security options
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]
```

### Kubernetes Security Hardening

Updated K8s manifests with security context:

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    readOnlyRootFilesystem: true
    capabilities:
      drop:
        - ALL
  containers:
    - name: api-server
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop:
            - ALL
```

### Environment Variable Security

All secrets externalized:

```env
# Required secrets (no defaults in production)
SECRET_KEY=
JWT_SECRET_KEY=
POSTGRES_PASSWORD=
REDIS_PASSWORD=
MONGO_PASSWORD=
SMTP_PASS=

# Configurable settings
FLASK_ENV=production
LOG_LEVEL=INFO
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
FEATURE_EMAIL_VERIFICATION=true
FEATURE_PASSWORD_RESET=true
FEATURE_AUDIT_LOG=true
```

### CI/CD Security Gates

GitHub Actions pipeline includes security checks:

```yaml
# .github/workflows/ci.yml
steps:
  - name: Security scan (bandit)
    run: bandit -r api-server/app/ -f json -o bandit-report.json
  
  - name: Dependency audit (pip-audit)
    run: pip-audit --desc
  
  - name: Secret scan (gitleaks)
    run: gitleaks detect --source .
```

---

## 📋 COMPLETE HARDENING CHECKLIST (UPDATED)

### Pre-Deployment
- [ ] All passwords changed from defaults
- [ ] Elasticsearch security enabled
- [ ] Vault not in dev mode
- [ ] HTTPS configured with valid certificates
- [ ] Non-root users in all containers
- [ ] Network isolation implemented
- [ ] Resource limits set for all services
- [ ] Health checks working for all services
- [ ] Logging configured with rotation
- [ ] Secrets managed via Docker secrets/external vault
- [ ] JWT secrets rotated (not defaults)
- [ ] SMTP credentials configured for production
- [ ] Redis password set
- [ ] Database users with minimal privileges

### Runtime Security
- [ ] Rate limiting enabled on all endpoints
- [ ] Account lockout after 5 failed attempts
- [ ] JWT tokens include JTI for revocation
- [ ] Refresh token rotation enabled
- [ ] Email verification flow working
- [ ] Password reset flow working
- [ ] Audit logging to database enabled
- [ ] Structured JSON logging configured
- [ ] Security headers present (CSP, HSTS, X-Frame-Options)
- [ ] CORS properly configured
- [ ] Error messages don't leak sensitive info

### Monitoring & Alerting
- [ ] Prometheus scraping /metrics endpoint
- [ ] Grafana dashboards imported
- [ ] Alert rules configured (HighCPU, ServiceDown)
- [ ] Log aggregation (Loki) collecting audit logs
- [ ] Distributed tracing (Jaeger) operational
- [ ] Health checks monitored (liveness/readiness)

### Post-Deployment
- [ ] Smoke tests pass (register → login → refresh → logout)
- [ ] Email verification tested
- [ ] Password reset tested
- [ ] Token revocation tested
- [ ] Audit logs visible in database
- [ ] Swagger UI accessible at /docs
- [ ] CI/CD pipeline passing
- [ ] Docker image scanned (trivy)
- [ ] Dependencies audited (pip-audit)

---

## 🎯 STATUS SUMMARY

| Security Feature | Status | Implementation |
|-----------------|--------|----------------|
| JWT Access Tokens | ✅ Done | With JTI claim |
| JWT Refresh Tokens | ✅ Done | With rotation |
| Token Revocation | ✅ Done | Redis blacklist |
| Email Verification | ✅ Done | itsdangerous + 24h expiry |
| Password Reset | ✅ Done | itsdangerous + 1h expiry |
| Audit Logging | ✅ Done | JSON to DB + logger |
| Rate Limiting | ✅ Done | Flask-Limiter |
| Account Lockout | ✅ Done | 5 attempts / 15 min |
| Security Headers | ✅ Done | CSP, HSTS, X-Frame-Options |
| Docker Non-root | ✅ Done | appuser (uid 1000) |
| K8s Security Context | ✅ Done | readOnlyRootFilesystem, drop ALL |
| CI/CD Security Gates | ✅ Done | bandit, pip-audit, gitleaks |

---

**Status:** 🟢 **Substantially Implemented**  
**Priority:** 🔴 CRITICAL for Production  
**Last Updated:** 2026-09-03