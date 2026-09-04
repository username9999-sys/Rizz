# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (Week 5-6)
- Monitoring stack: Prometheus + Alertmanager + Grafana + Loki + Promtail
  with 18 alert rules and 2 pre-built dashboards
- Cache-aside helpers (`app/utils/cache.py`) with Redis backend and
  no-op fallback
- Performance index migration (14 indexes for actual query patterns)
- One-command dev setup (`scripts/dev.sh`)
- Docker compose override for hot reload
- DEBUG config preset for dev (no-op in production)
- CDN setup guide (`docs/CDN_SETUP.md`)
- Backup verification & DR plan (`BACKUP_VERIFICATION.md`)
- Scaling strategy (`SCALING.md`)

### Added (Week 3-4)
- TOTP MFA support (`app/utils/totp.py`, RFC 6238, 22 tests)
- Account lockout with progressive backoff (`app/utils/account_security.py`)
- Password complexity policy
- JWT session manager with refresh rotation + replay detection
  (`app/utils/session.py`, 25 tests)
- Penetration test suite (25 OWASP coverage tests in `test_pentest.py`)
- Security CI workflow (pip-audit, npm audit, gitleaks, bandit, hadolint)
- OpenAPI 3.0.3 spec with 11 endpoints and 7 schemas
- Security checklist validator (`scripts/check-security.py`)

### Added (Week 1-2)
- Content-Type guard (415 on non-JSON POST/PUT/PATCH)
- Field allowlist + required field validation via `@validate_json`
- HTML/event-handler sanitization for content fields
- Production config fail-closed (refuses wildcard CORS, missing secrets)
- Hardened nginx.conf: full security headers, TLS 1.2/1.3, ACME
  challenge, rate limit zones per route category
- ESLint + pre-commit hooks
- 22 module QUICKSTART.md files (auto-generated)
- TLS certificate generator (`scripts/generate-tls-certs.sh`)

### Changed
- Renamed `package.json` scripts to use `lint` and `format` consistently
- All compose files: required env vars for admin passwords (no more
  hardcoded defaults like `changeme` or `minioadmin`)
- Compose admin ports now bound to `127.0.0.1` instead of `0.0.0.0`
- All services hardened with `no-new-privileges`, `cap_drop: [ALL]`,
  explicit non-root user

### Security
- Removed hardcoded `admin123` from Grafana config
- Removed `GRAFANA_PASSWORD` placeholder; now required via env
- Vault dev mode is now opt-in via `VAULT_MODE=dev|prod`
- All compose files require generated secrets via `scripts/generate-secrets.sh`

### Fixed
- `app/__init__.py` NameError: `@app.before_request` /
  `@app.after_request` were registered at module scope before `app`
  was defined. App could not start. Now properly registered in factory.
- `from app import limiter` ImportError in routes. Added module-scope
  sentinel and assignment in `init_extensions`.
- Elasticsearch password no longer defaults to `changeme`.
- MinIO `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` no longer default
  to `minioadmin`.

## [0.8.0-alpha] - 2024-01-15

Initial honest assessment release. See `IMPROVEMENTS_SUMMARY.md` for
the cleanup that made this project suitable for learning purposes.
Documented in `PROJECT_STATUS.md` as a learning portfolio, not
production-ready.

[0.8.0-alpha]: https://github.com/username9999-sys/Rizz/releases/tag/v0.8.0-alpha

---

## Versioning policy

  - MAJOR (X.0.0): incompatible API changes, breaking schema changes
  - MINOR (0.X.0): new features, backward-compatible
  - PATCH (0.0.X): bug fixes, backward-compatible

Pre-release tags:
  - `-alpha`: early development, expect breakage
  - `-beta`: feature complete, stabilizing
  - `-rc.N`: release candidate, only critical fixes until GA

Currently at `0.8.0-alpha` (next minor: `0.9.0`).
