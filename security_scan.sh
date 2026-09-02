#!/usr/bin/env bash
# Security scan script for the Rizz API Server
# Uses Bandit (Python security linter) to scan the codebase.
# Exits with non-zero status if any HIGH severity findings are present.

set -euo pipefail

# Ensure bandit is installed (it is listed in requirements.txt)
if ! command -v bandit >/dev/null 2>&1; then
  echo "Bandit not found – installing via pip..."
  pip install --quiet bandit
fi

# Run bandit on the Python source directory (excluding tests)
BANDIT_OUTPUT=$(bandit -r . -x "*/tests/*" -f json)

# Parse JSON to count findings by severity
HIGH_COUNT=$(echo "$BANDIT_OUTPUT" | python - <<'PY'
import sys, json
data = json.load(sys.stdin)
print(sum(1 for issue in data.get('results', []) if issue.get('issue_severity') == 'HIGH'))
PY
)

echo "Bandit scan completed. HIGH severity findings: $HIGH_COUNT"
if [ "$HIGH_COUNT" -gt 0 ]; then
  echo "Security issues detected! Review the above findings."
  exit 1
fi

echo "No high severity issues found."
exit 0
