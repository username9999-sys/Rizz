# Security Guidance for Rizz Project

## Quick Security Scan

You can run the bundled security scan script to detect high‑severity issues in the Python codebase:

```bash
chmod +x security_scan.sh   # make executable (once)
./security_scan.sh
```

The script installs **bandit** if it is missing, scans the repository (excluding tests), and fails with exit code 1 if any **HIGH** severity findings are reported.  Fix the reported issues before committing.

## Hardening Checklist

- **Environment Secrets** – `SECRET_KEY` and `JWT_SECRET_KEY` must be provided via environment variables in production; the application will raise an error if they are missing.
- **Password Policy** – Passwords now require a minimum of 8 characters, an uppercase letter, a lowercase letter, a digit, and a special character.  The `User` model validates this on creation.
- **Rate Limiting** – All authentication and post endpoints are protected with Flask‑Limiter (e.g., 5 req/min for login, 30 req/min for writes).
- **Account Lockout** – After 5 failed login attempts within a 15‑minute window the account is temporarily locked (HTTP 429).
- **Response Headers** – Added `Content‑Security‑Policy`, `X‑Content‑Type‑Options`, `X‑Frame‑Options`, `X‑XSS‑Protection`, and `Strict‑Transport‑Security` to every response.
- **Secure Cookies** – Flask cookie settings enforce `HttpOnly`, `Secure`, and `SameSite=Lax`.
- **CSP** – Default policy `default-src 'self'`. Adjust `app.config['CSP_POLICY']` for custom needs.
- **Logging** – Structured JSON logging includes request IDs and timestamps; failed auth attempts are logged at warning level.
- **Dependency Auditing** – Run `bandit -r .` manually or integrate it into CI for continuous checks.

## Next Steps

- Move the in‑memory login‑attempt tracker to Redis or another persistent store for multi‑process deployments.
- Integrate Vault or another secret manager for production secret handling.
- Add MFA/2FA for admin accounts.
- Harden Docker compose with network isolation and resource limits (already added).
- Enforce HTTPS with real certificates in production (update Nginx config).

For any further hardening or feature work, refer to the project’s `CLAUDE.md` and the ECC rule set for Python.
