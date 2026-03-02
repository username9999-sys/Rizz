# Contributing to Rizz Platform

Thank you for your interest in contributing! This document provides guidelines for contributing.

## 🎯 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what's best for the community

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
- Add tests

```python
def calculate_total(items: list[float], tax_rate: float) -> float:
    """
    Calculate total with tax.
    
    Args:
        items: List of item prices
        tax_rate: Tax rate as decimal
        
    Returns:
        Total amount including tax
    """
    subtotal = sum(items)
    return subtotal * (1 + tax_rate)
```

**JavaScript:**
- Use ES6+ features
- Add JSDoc comments
- Handle errors properly

```javascript
/**
 * Calculate total with tax
 * @param {number[]} items - List of item prices
 * @param {number} taxRate - Tax rate as decimal
 * @returns {number} Total amount including tax
 */
function calculateTotal(items, taxRate) {
  const subtotal = items.reduce((sum, item) => sum + item, 0);
  return subtotal * (1 + taxRate);
}
```

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
   - [ ] Code is formatted
   - [ ] Documentation updated
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
   - Automated checks run
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

## 📚 Resources

- [Python Style Guide](https://peps.python.org/pep-0008/)
- [JavaScript Style Guide](https://github.com/airbnb/javascript)
- [Git Best Practices](https://github.com/git-guides)
- [Testing Best Practices](https://docs.pytest.org/)

## ❓ Questions?

- Check existing documentation
- Search existing issues
- Ask in GitHub Discussions
- Contact maintainers

---

**Thank you for contributing!** 🎉
