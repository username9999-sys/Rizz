# Release Process

This document describes how to cut a release of the Rizz platform.

We follow [Semantic Versioning](https://semver.org/) and tag each
release in git. Releases are published to GitHub via the
[Releases](https://github.com/username9999-sys/Rizz/releases) page
and a Docker image is pushed to GitHub Container Registry (ghcr.io).

## Versioning

Given a version number `MAJOR.MINOR.PATCH`:

  - **MAJOR** bump when you make incompatible API changes
  - **MINOR** bump when you add functionality in a backward-compatible way
  - **PATCH** bump when you make backward-compatible bug fixes

Pre-release tags: `-alpha.N`, `-beta.N`, `-rc.N` (in that order).

## Release cadence

  - **Ad-hoc** during `0.x` development (no fixed schedule)
  - **Monthly** once we hit `1.0` (GA)
  - **Patch releases** as needed for security fixes

## Pre-release checklist

Run through these BEFORE cutting a tag:

  - [ ] All tests pass: `cd api-server && pytest`
  - [ ] Coverage is >= target (currently 70%, see `IMPROVEMENT_ROADMAP.md`)
  - [ ] `python3 scripts/check-links-local.py` reports no broken links
  - [ ] `python3 scripts/check-security.py` passes
  - [ ] `CHANGELOG.md` "Unreleased" section is fully populated
  - [ ] All open security advisories are closed or accepted as known
  - [ ] Migration scripts in `migrations/versions/` are tested
  - [ ] Docker images build: `docker build -t rizz:test api-server/`
  - [ ] `.env.example` is up to date with all required env vars
  - [ ] `BACKUP_VERIFICATION.md` and `SCALING.md` reflect current behavior

## Cutting a release

### 1. Update version references

```bash
# In api-server/app/__init__.py (or wherever the version lives)
__version__ = "0.9.0"
```

### 2. Move CHANGELOG entries from `[Unreleased]` to a dated version

```markdown
## [0.9.0] - 2026-09-15
... all the items that were in [Unreleased] ...
```

### 3. Commit and tag

```bash
git add CHANGELOG.md api-server/app/__init__.py
git commit -m "release: 0.9.0"
git tag -a v0.9.0 -m "0.9.0"
git push origin master --tags
```

### 4. Build and push the Docker image

```bash
docker build -t ghcr.io/username9999-sys/rizz-api:0.9.0 -t ghcr.io/username9999-sys/rizz-api:latest api-server/
docker push ghcr.io/username9999-sys/rizz-api:0.9.0
docker push ghcr.io/username9999-sys/rizz-api:latest
```

### 5. Create the GitHub Release

  1. Go to `https://github.com/username9999-sys/Rizz/releases/new`
  2. Choose tag `v0.9.0`
  3. Title: `Rizz 0.9.0`
  4. Body: copy the `## [0.9.0]` section from CHANGELOG.md
  5. Mark as "Latest release" if appropriate
  6. Publish

### 6. Announce

  - Slack: `#rizz-releases`
  - Email: `announce@rizz.dev` (mailing list)
  - Twitter/Mastodon: `@rizz_dev` (if account exists)
  - Update the `README.md` "What's new" section

## Post-release

  - [ ] Monitor error rates for 24 hours (Prometheus alert: `ApiHighErrorRate`)
  - [ ] Verify smoke tests pass in production
  - [ ] Close the milestone on GitHub
  - [ ] Update `IMPROVEMENT_ROADMAP.md` with the released version
  - [ ] Begin planning the next milestone

## Hotfix procedure

For a security patch or critical bug:

```bash
# 1. Branch from the latest release tag
git checkout -b hotfix/v0.9.1 v0.9.0

# 2. Make the minimal fix
# ... code, tests, CHANGELOG ...

# 3. Tag and release
git commit -am "hotfix: 0.9.1 — <description>"
git tag -a v0.9.1 -m "0.9.1"
git push origin hotfix/v0.9.1 --tags

# 4. Cherry-pick or merge back to master
git checkout master
git merge --no-ff hotfix/v0.9.1
git push origin master
```

## Deprecation policy

  - Features marked deprecated in `MINOR.X` are removed in `MAJOR.0`
  - Announce deprecations in CHANGELOG with at least one MINOR release
    of warning (e.g. "deprecated in 0.9.0, removal planned for 1.0.0")
  - Use Python `@deprecated` decorator or runtime warnings to flag at runtime

## See also

  - `CHANGELOG.md` — full change history
  - `IMPROVEMENT_ROADMAP.md` — what's planned
  - `SECURITY_POLICY.md` — how to report vulnerabilities
  - `CODE_OF_CONDUCT.md` — community standards
