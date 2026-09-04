# CDN Setup

This document covers serving static assets through a Content Delivery
Network (CDN) in front of the Rizz platform. We support Cloudflare
(recommended for most teams) and AWS CloudFront.

## What to cache

| Asset type | Cache? | TTL | Notes |
|------------|--------|-----|-------|
| `/static/*` (JS, CSS, fonts, images) | YES | 1 year (immutable) | Hash filenames for cache busting |
| `/favicon.ico` | YES | 1 day | |
| `/api/*` | NO | 0 | Always hit origin |
| `/api/health`, `/api/metrics` | NO | 0 | Origin only |
| `/api/posts/*` (public GET) | YES (stale) | 60s edge, 5m browser | See below |
| Authenticated `/api/posts` (POST/PUT/DELETE) | NO | 0 | Never cache mutating |
| HTML pages with user data | NO | 0 | Always fresh |
| Login/register pages | NO | 0 | CSRF tokens are per-request |

The rule: **cache only what is shared and immutable**. Anything
user-specific or authenticated is not safe to cache.

## Cloudflare Setup

### 1. Add site to Cloudflare

  1. Create account at https://dash.cloudflare.com
  2. Add your domain (e.g. `rizz.dev`)
  3. Cloudflare will scan existing DNS records; confirm them
  4. Update nameservers at your registrar to the Cloudflare ones

### 2. SSL/TLS

  - **SSL/TLS > Overview > Full (Strict)**
  - **Edge Certificates > Always Use HTTPS: ON**
  - **Edge Certificates > Minimum TLS Version: TLS 1.2**
  - **Edge Certificates > Automatic HTTPS Rewrites: ON**
  - Cloudflare issues a free origin cert; install on the origin nginx

### 3. Page Rules (Cache Rules in newer UI)

```
# Static assets — long cache
URL: rizz.dev/static/*
Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 year
  - Browser Cache TTL: 1 year
  - Origin Cache Control: On

# API GETs — short edge cache
URL: rizz.dev/api/posts*
Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 60 seconds
  - Browser Cache TTL: 5 minutes
  - Cache by Device Type: Off
  - Bypass Cache on Cookie: api_session

# Admin and authenticated endpoints — bypass
URL: rizz.dev/api/auth/*
Settings:
  - Cache Level: Bypass
  - Security Level: High

# Login page — bypass
URL: rizz.dev/login
Settings:
  - Cache Level: Bypass
```

### 4. Firewall rules

  - **Security > WAF > Managed Rules: ON** (Cloudflare free tier)
  - **Security > Bots > Bot Fight Mode: ON**
  - **Security > Settings > Browser Integrity Check: ON**

### 5. Rate limiting (free tier: 1 rule)

```
Expression: (http.request.uri.path eq "/api/auth/login")
Rate: 5 requests per 10 seconds per IP
Action: Challenge (CAPTCHA) for 1 hour
```

For production, add paid rules for stricter thresholds.

### 6. Caching dynamic API responses

For the public `/api/posts` GET endpoint, set cache headers at the
origin (Flask):

```python
@app.route("/api/posts")
@cache.cached(ttl=60, key="posts:list:{0}", namespace="rizz:public")
def list_posts():
    response = jsonify({"posts": ...})
    response.cache_control.public = True
    response.cache_control.max_age = 60      # browser
    response.cache_control.s_maxage = 300   # CDN
    return response, 200
```

`s_maxage` is the CDN edge TTL, separate from `max_age` (browser).

## AWS CloudFront Setup

If you prefer CloudFront over Cloudflare:

```yaml
# cloudfront-distribution.yaml (CloudFormation)
AWSTemplateFormatVersion: "2010-09-09"
Resources:
  RizzCDN:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Enabled: true
        PriceClass: PriceClass_100
        Origins:
          - Id: rizz-origin
            DomainName: api.rizz.dev
            CustomOriginConfig:
              OriginProtocolPolicy: https-only
              OriginSSLProtocols: [TLSv1.2]
        DefaultCacheBehavior:
          TargetOriginId: rizz-origin
          ViewerProtocolPolicy: redirect-to-https
          AllowedMethods: [GET, HEAD, OPTIONS]
          CachedMethods: [GET, HEAD]
          CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6  # CachingOptimized
          Compress: true
        CacheBehaviors:
          - PathPattern: "/static/*"
            TargetOriginId: rizz-origin
            ViewerProtocolPolicy: redirect-to-https
            CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6
            MinTTL: 31536000
            DefaultTTL: 31536000
            MaxTTL: 31536000
          - PathPattern: "/api/posts*"
            TargetOriginId: rizz-origin
            ViewerProtocolPolicy: redirect-to-https
            CachePolicyId: 4135ea2d-6df8-44a3-9df3-4b5a84be39ad  # CachingDisabled
            MinTTL: 0
            DefaultTTL: 60
            MaxTTL: 300
```

## Origin configuration

Your origin (nginx) should:

  1. Honor the `X-Forwarded-Proto` header from the CDN
  2. Set `Vary: Accept-Encoding, Authorization` on dynamic responses
  3. Set `Cache-Control: s-maxage=N` for CDN-aware caching
  4. Return `404` (not `200`) for missing resources so the CDN
     can cache the miss briefly

## Purge / Invalidation

When you deploy new code, purge the CDN cache:

```bash
# Cloudflare
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"files": ["https://rizz.dev/static/rizz-app.bundle.js"]}'

# Or purge everything (use carefully):
# -d '{"purge_everything": true}'

# CloudFront
aws cloudfront create-invalidation \
    --distribution-id $CF_DIST_ID \
    --paths "/static/*" "/index.html"
```

Add to your deploy script (e.g. `scripts/deploy.sh`).

## Cache hit ratio

Monitor in Cloudflare Analytics or via the `X-Cache` header. Target:
  - Static assets: >99% hit rate
  - Public API: >70% hit rate

If hit rate is low, review:
  - `Vary` header — too granular values fragment the cache
  - Query strings — they create cache variants
  - Cookies — Cloudflare bypasses on most cookies by default
