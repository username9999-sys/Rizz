# GDPR & CCPA Compliance

This document covers the technical and procedural measures the Rizz
platform takes to comply with the EU General Data Protection Regulation
(GDPR) and the California Consumer Privacy Act (CCPA).

> **Disclaimer**: This is engineering documentation, not legal
> advice. Consult a qualified attorney for jurisdiction-specific
> interpretation.

## What data we store

For a logged-in user we store:

| Data | Where | Purpose | Retention |
|------|-------|---------|-----------|
| Email | users.email | login, notifications | until account deletion + 30 days |
| Hashed password | users.password_hash | authentication | until account deletion |
| Username | users.username | display | until account deletion |
| IP address (login) | audit_log.ip_address | security | 90 days |
| Posts authored | posts | service feature | until deletion |
| Comments | comments | service feature | until deletion |
| Session tokens (revoked) | sessions (refresh table) | session continuity | 7 days after expiry |
| Audit log entries | audit_log | security | 1 year |

We do NOT collect:
  - Biometric data
  - Special category data (race, religion, health, sexual orientation)
  - Payment data (none of our services take payment)

## Lawful basis

GDPR Art. 6: our lawful basis is **consent** (account creation) and
**legitimate interest** (security, fraud prevention via audit logs).

## Data subject rights (GDPR Chapter III)

| Right | How we honor it |
|-------|-----------------|
| Right to be informed | This document + privacy policy linked from signup |
| Right of access (Art. 15) | `GET /api/v1/me/data-export` (see below) |
| Right to rectification (Art. 16) | `PUT /api/v1/me` for profile fields |
| Right to erasure (Art. 17) | `DELETE /api/v1/me` (see below) |
| Right to restriction (Art. 18) | Account freeze flag (not yet implemented; tracked in roadmap) |
| Right to data portability (Art. 20) | JSON export via `/me/data-export` |
| Right to object (Art. 21) | Stop processing for marketing — N/A, we don't market |
| Right not to be subject to automated decision-making (Art. 22) | N/A, we don't do this |

## Data subject rights (CCPA)

| Right | Implementation |
|-------|----------------|
| Right to know | Same as GDPR access request |
| Right to delete | Same as GDPR erasure |
| Right to opt-out of "sale" | N/A, we do not sell personal data |
| Right to non-discrimination | All users have same features |

## Data export endpoint (Art. 15 + Art. 20)

A user can request a complete export of their data. This must be
delivered within 30 days (GDPR) or 45 days (CCPA).

### Endpoint spec

```
GET /api/v1/me/data-export
Authorization: Bearer <token>
```

Response: `200 OK` with JSON body:
```json
{
  "user": {
    "id": "123",
    "username": "alice_99",
    "email": "alice@example.com",
    "created_at": "2026-01-15T10:00:00Z"
  },
  "posts": [
    {"id": 1, "title": "Hello", "content": "...", "created_at": "..."}
  ],
  "comments": [...],
  "audit_log": [
    {"action": "login", "timestamp": "...", "ip": "..."}
  ]
}
```

Implementation reference (add to a real route file):
```python
from flask import jsonify, g, request
from flask_jwt_extended import jwt_required, get_jwt_identity

@app.route("/api/v1/me/data-export", methods=["GET"])
@jwt_required
def data_export():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify({
        "user": user.to_export_dict(),
        "posts": [p.to_export_dict() for p in user.posts.all()],
        "comments": [c.to_export_dict() for c in user.comments.all()],
        "audit_log": [a.to_export_dict() for a in user.audit_log.all()],
    }), 200
```

## Erasure endpoint (Art. 17)

```
DELETE /api/v1/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "confirmation": "delete-my-account",
  "reason": "optional, free-form text"
}
```

Effect:
  1. Mark user as `deleted = true`, `email = NULL`, `username = deleted_<hash>`
  2. Anonymize posts (set `user_id = NULL` or transfer to "deleted" sentinel)
  3. Revoke all sessions
  4. Anonymize audit_log entries (remove IP, user-agent, replace user_id with NULL)
  5. Schedule hard delete after 30-day grace period (configurable)

The 30-day grace period exists so that:
  - The user can change their mind
  - We can comply with financial / fraud investigation requests
  - Backups taken before deletion are eventually rotated out

## Cookie & tracking

  - We do not use third-party analytics
  - We do not set advertising cookies
  - Session cookies are `HttpOnly`, `Secure` (in production), `SameSite=Lax`
  - JWT auth is also supported for API clients that cannot use cookies

## Data Processing Agreement (DPA)

For B2B customers (tenants), a DPA is required under GDPR Art. 28.
This is a contract between Rizz and the tenant, not a code change.

## International transfers

If you host in a region other than the EU, EU user data is being
transferred outside the EEA. To comply with GDPR Chapter V:

  - Use EU-based hosting (Hetzner, OVH, Scaleway, AWS eu-central-1)
  - OR use Standard Contractual Clauses (SCCs)
  - OR rely on Privacy Shield (no longer valid post-2020)
  - Document the transfer mechanism in your privacy policy

## Breach notification (Art. 33)

In the event of a personal data breach, we notify the supervisory
authority within 72 hours. Our incident response is in
`docs/DR_RUNBOOK.md`.

## Children's data (GDPR Art. 8)

We do not knowingly collect data from users under 16 (or under 13 in
the US per COPPA). The signup form requires age confirmation. Any
identified child account is deleted within 7 days of discovery.

## Records of processing activities (Art. 30)

| Processing activity | Purpose | Legal basis | Categories of data | Recipients | Retention |
|---------------------|---------|-------------|---------------------|------------|-----------|
| Account creation | service delivery | consent | email, username, password hash | none | until deletion |
| Authentication | service delivery | consent | session token, IP | none | 7 days post-revoke |
| Content publishing | service delivery | consent | posts, comments | public | until deletion |
| Security audit | legitimate interest | security | IP, user agent, action | none | 1 year |

## Implementation status

| Control | Status | Notes |
|---------|--------|-------|
| Data export endpoint | Specified (see above) | Add to routes/me.py |
| Erasure endpoint | Specified (see above) | Add to routes/me.py; needs 30-day grace cron |
| Cookie consent banner | TODO | For web portfolio |
| Privacy policy linked from signup | TODO | Required for GDPR |
| DPA template | TODO | For B2B customers |
| Audit log anonymization on erasure | TODO | Run on `DELETE /me` |
| Backup rotation policy | TODO | Ensure deleted user data ages out |

## How to test

You can verify compliance behavior with curl:

```bash
# Login
TOKEN=$(curl -sS -X POST http://localhost:5000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"alice","password":"GoodPass99"}' | jq -r .token)

# Request data export
curl -sS http://localhost:5000/api/v1/me/data-export \
    -H "Authorization: Bearer $TOKEN" | jq .

# Request erasure
curl -sS -X DELETE http://localhost:5000/api/v1/me \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"confirmation": "delete-my-account"}'
```
