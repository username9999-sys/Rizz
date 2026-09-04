# Security Checklist — Rizz API

This checklist enumerates the security controls that **must** hold for
every public endpoint. The accompanying script
`scripts/check-security.py` reads `api-server/openapi.yaml` and
asserts that each endpoint has the required controls configured.

Use this checklist when:
  - Reviewing a new endpoint before merge
  - Auditing an existing endpoint
  - Running `python3 scripts/check-security.py` in CI

---

## Per-endpoint Controls

For every endpoint, verify the following are in place:

| # | Control | Where | How to verify |
|---|---------|-------|---------------|
| 1 | Content-Type guard | `app/__init__.py` `_before_request` | POST/PUT/PATCH with non-JSON returns 415 |
| 2 | Field allowlist | `@validate_json(allowed_fields=...)` | Unknown fields return 400 |
| 3 | Required field check | `@validate_json(required_fields=...)` | Missing fields return 400 |
| 4 | Input validators | `_VALIDATORS` in `app/utils/security.py` | Bad email/username/password/etc. return 400 |
| 5 | HTML sanitization | `_SANITIZE_FIELDS` in `app/utils/security.py` | `<script>` and event handlers stripped from string fields |
| 6 | Rate limiting | `@limiter.limit("N per minute")` | Exceeding limit returns 429 |
| 7 | Auth check | `@require_auth` decorator on protected routes | Missing/invalid token returns 401 |
| 8 | Owner-only authz | Manual check in view (`if rows[0].user_id != g.user_id`) | Other-user returns 403 |
| 9 | Security headers | `app/__init__.py` `after_request` + `nginx.conf` | All responses include CSP, HSTS, X-Frame-Options, etc. |
| 10 | Audit log | `log_action(user_id, action, ...)` | Sensitive actions recorded in AuditLog table |
| 11 | HTTPS only | `nginx.conf` + `ENFORCE_HTTPS` | All 80 traffic redirected to 443 |
| 12 | Error sanitization | All views return JSON, never raw stack traces | 500 errors don't leak internals |
| 13 | Constant-time compare | `hmac.compare_digest` for tokens/passwords | No timing oracle for credentials |
| 14 | Pagination | `LIMIT N OFFSET M` on list endpoints | Prevents DoS via `?limit=999999999` |
| 15 | Account lockout | `AccountLockout` utility called on failure | 5 failed logins → 15-min lockout |
| 16 | MFA for admins | TOTP verification on admin endpoints | `/api/auth/me` returns `mfa_required` flag |
| 17 | Refresh rotation | `SessionManager.rotate_refresh` | Old refresh token invalid after one use |
| 18 | Revocation list | `SessionManager.revoke_user` | Password change revokes all sessions |

## Endpoint Coverage Matrix

| Endpoint | Method | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 |
|----------|--------|---|---|---|---|---|---|---|---|---|----|----|----|----|----|----|----|----|----|
| /api/auth/register | POST | ✓ | ✓ | ✓ | ✓ | n/a | ✓ | n/a | n/a | ✓ | ✓ | ✓ | ✓ | n/a | n/a | n/a | n/a | n/a | n/a |
| /api/auth/login | POST | ✓ | ✓ | ✓ | ✓ | n/a | ✓ | n/a | n/a | ✓ | ✓ | ✓ | ✓ | ✓ | n/a | ✓ | opt | n/a | n/a |
| /api/auth/me | GET | ✓ | n/a | n/a | n/a | n/a | ✓ | ✓ | n/a | ✓ | n/a | ✓ | ✓ | n/a | n/a | n/a | opt | n/a | n/a |
| /api/posts | GET | ✓ | n/a | n/a | n/a | n/a | ✓ | n/a | n/a | ✓ | n/a | ✓ | ✓ | n/a | ✓ | n/a | n/a | n/a | n/a |
| /api/posts | POST | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/a | ✓ | ✓ | ✓ | ✓ | n/a | n/a | n/a | opt | ✓ | n/a |
| /api/posts/{id} | GET | ✓ | n/a | n/a | n/a | n/a | ✓ | n/a | n/a | ✓ | n/a | ✓ | ✓ | n/a | n/a | n/a | n/a | n/a | n/a |
| /api/posts/{id} | PUT | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/a | n/a | n/a | opt | ✓ | n/a |
| /api/posts/{id} | DELETE | ✓ | n/a | n/a | n/a | n/a | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/a | n/a | n/a | opt | n/a | n/a |
| /health | GET | ✓ | n/a | n/a | n/a | n/a | n/a | n/a | n/a | ✓ | n/a | ✓ | ✓ | n/a | n/a | n/a | n/a | n/a | n/a |
| /metrics | GET | ✓ | n/a | n/a | n/a | n/a | n/a | opt | n/a | ✓ | n/a | ✓ | ✓ | n/a | n/a | n/a | n/a | n/a | n/a |
| /api/v2 | GET | ✓ | n/a | n/a | n/a | n/a | n/a | n/a | n/a | ✓ | n/a | ✓ | ✓ | n/a | n/a | n/a | n/a | n/a | n/a |

Legend:
  ✓ required  ·  opt optional  ·  n/a not applicable

## Verification

Run the automated checker:

```bash
python3 scripts/check-security.py
```

It will:
  1. Read `api-server/openapi.yaml`
  2. Verify each endpoint has a description
  3. Verify 4xx/5xx responses are documented
  4. Verify security schemes are referenced for protected endpoints
  5. Print a pass/fail summary

## Adding a New Endpoint

When adding a new route, complete **all** applicable controls above
and tick the appropriate cells in the matrix. Then add a row to the
OpenAPI spec under `api-server/openapi.yaml` so the checker picks it
up.

## Re-audit

Re-run `python3 scripts/check-security.py` after:
  - Adding a new endpoint
  - Changing an existing route's auth/rate-limit/validation
  - Modifying `app/utils/security.py` or `app/utils/session.py`
