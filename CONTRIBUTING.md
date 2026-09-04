# Contributing to Rizz Platform

Thank you for your interest in contributing! This document provides guidelines for contributing.

> **Before you start, please read**:
> - [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community standards
> - [SECURITY_POLICY.md](SECURITY_POLICY.md) — how to report vulnerabilities
> - [RELEASING.md](RELEASING.md) — versioning & release process
> - [CHANGELOG.md](CHANGELOG.md) — what changed in each release
> - [IMPROVEMENT_ROADMAP.md](IMPROVEMENT_ROADMAP.md) — what's planned

## 🎯 Code of Conduct

This project adheres to the [Contributor Covenant](CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code. Report
unacceptable behavior to conduct@rizz.dev.

## 📋 How to Contribute

### 1. Report Bugs

Before creating a bug report:
- [ ] Check existing issues
- [ ] Verify it's reproducible
- [ ] Collect information about the bug

**Bug Report Template:**
```markdown
**Description**: Clear description of the bug

**Reproduction Steps**:
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior**: What should happen

**Actual Behavior**: What actually happened

**Environment**:
- OS: [e.g. Ubuntu 22.04]
- Python: [e.g. 3.11.5]
- Node.js: [e.g. 18.17.0]

**Additional Context**: Any other information
```

### 2. Suggest Features

**Feature Request Template:**
```markdown
**Problem**: What problem does this solve?

**Proposed Solution**: How should it work?

**Alternatives Consider**: Other solutions you've thought about

**Additional Context**: Any other information
```

### 3. Submit Code

#### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (optional)
- Git

#### Development Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/Rizz.git
cd Rizz-Project

# Create branch
git checkout -b feature/your-feature-name

# Install dependencies
cd api-server && pip install -r requirements.txt
```

#### Code Standards

**Python:**
- Follow PEP 8
- Use type hints
- Write docstrings
- Write tests
- Run linting: `ruff check --fix .`
- Type check: `mypy .`

**JavaScript/TypeScript:**
- Use ES6+ features
- Add JSDoc comments
- Handle errors properly

#### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Check coverage (must be 80%+)
coverage report --fail-under=80
```

#### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add user authentication
fix: resolve login timeout issue
docs: update API documentation
test: add integration tests for auth
refactor: improve database connection handling
```

#### Pull Request Process

1. **Before Submitting:**
   - [ ] Tests pass
   - [ ] Code is formatted (`ruff check --fix`)
   - [ ] Documentation updated (`README.md`, `CONTRIBUTING.md`)
   - [ ] Changelog updated (if applicable)

2. **PR Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] Test coverage maintained/improved

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] No new warnings
- [ ] Documentation updated
```

3. **Review Process:**
   - Maintainer reviews code
   - Automated checks run (lint, type-check, tests)
   - Changes requested (if any)
   - Approval and merge

## 📏 Code Review Guidelines

### Reviewers Should:
- Be constructive and respectful
- Explain reasoning for suggestions
- Acknowledge good code
- Focus on important issues

### Authors Should:
- Respond to all feedback
- Explain design decisions
- Make requested changes
- Thank reviewers

## 🔒 Security

- Never commit secrets or credentials
- Use `.gitignore` properly
- Report vulnerabilities privately (see SECURITY.md)
- Follow security best practices
  - JWT tokens include JTI for revocation
  - Email verification and password reset flows are tested
  - Audit logs are structured JSON
  - Swagger UI is generated from OpenAPI spec

## 📚 Resources

- [Python Style Guide](https://peps.python.org/pep-0008/)
- [JavaScript Style Guide](https://github.com/airbnb/javascript)
- [Git Best Practices](https://github.com/git-guides)
- [Testing Best Practices](https://docs.pytest.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

## ❓ Questions?

- Check existing documentation
- Search existing issues
- Ask in GitHub Discussions
- Contact maintainers

---

**Thank you for contributing!** 🎉

---

## 🛠 Development workflow

### Local setup (one command)

```bash
./scripts/dev.sh           # full Docker stack
./scripts/dev.sh --api-only   # Python-only, no Docker
./scripts/dev.sh --test       # run pytest
./scripts/dev.sh --logs       # tail service logs
./scripts/dev.sh --stop       # tear down
./scripts/dev.sh --reset      # nuke volumes and restart
```

See [`scripts/dev.sh`](scripts/dev.sh) for details. The script
generates secrets automatically on first run.

### Before submitting a pull request

Run the local checks in this order. They mirror what CI runs:

```bash
# 1. Lint and syntax
cd api-server
python3 -m pytest tests/ -v                # all tests must pass

# 2. Coverage
python3 -m coverage run --source=app/utils,app/config --omit='*/__init__.py' \
    --rcfile=/dev/null -m pytest tests/
python3 -m coverage report --rcfile=/dev/null -m

# 3. Type hints
python3 -m pytest tests/test_type_hints.py

# 4. Security
cd ..
python3 scripts/check-links-local.py       # broken markdown links
python3 scripts/check-security.py          # OpenAPI spec coverage

# 5. YAML validation
python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"
```

### Commit message style

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`chore`, `security`, `ops`.

Examples:
- `feat(api): add /api/v1/me/data-export endpoint`
- `fix(cache): fix double-count when value is None`
- `docs(readme): clarify docker compose usage`
- `security(totp): constant-time compare for verification`
- `ops(monitoring): add Prometheus alert for disk space`

### Pull request process

1. Fork & branch from `master`:
   ```bash
   git checkout -b feat/my-feature
   ```
2. Make focused commits (one logical change per commit)
3. Run the local checks above
4. Push & open PR against `master`
5. Wait for CI to pass (lint, tests, security scan)
6. Address review feedback
7. Squash-merge after approval

### Code style

  - **Python**: PEP 8 + Black formatting + type hints on public API
  - **JavaScript**: ESLint (config in `.eslintrc.json`)
  - **Markdown**: wrap at 100 cols, sentence case headers
  - **Commit messages**: imperative mood, 72-char subject, wrap body at 72

### What to work on

  - Good first issues: look for `good-first-issue` label
  - Roadmap: [`IMPROVEMENT_ROADMAP.md`](IMPROVEMENT_ROADMAP.md) has the
    full plan
  - Security: see [`SECURITY_AUDIT_REQUEST.md`](SECURITY_AUDIT_REQUEST.md)
    for areas needing review
  - Documentation: small improvements are always welcome

### Getting help

  - Discord: `#rizz-dev` (see `discord-bot/` for the bot)
  - Issues: GitHub issue tracker with the `question` label
  - Email: dev@rizz.dev (no SLA, but we read everything)

