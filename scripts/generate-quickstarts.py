#!/usr/bin/env python3
"""
Quickstart generator.

For each top-level module under the project root, generate a
QUICKSTART.md based on the artifacts found in that module:
  - package.json          -> JS/Node module
  - requirements.txt      -> Python module
  - Dockerfile            -> Container module
  - README.md             -> existing docs (referenced, not overwritten)

Run from the project root:
    python3 scripts/generate-quickstarts.py [--force]

Use --force to overwrite existing QUICKSTART.md files.
"""

import os
import sys
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "htmlcov", "scripts"}


def detect_kind(module_dir: Path):
    """Return a tuple (kind, meta) describing the module."""
    if (module_dir / "package.json").is_file():
        try:
            pkg = json.loads((module_dir / "package.json").read_text())
        except Exception:
            pkg = {}
        scripts = pkg.get("scripts", {})
        return "node", {
            "name": pkg.get("name", module_dir.name),
            "version": pkg.get("version", "?"),
            "main": pkg.get("main", "index.js"),
            "scripts": scripts,
        }
    if (module_dir / "requirements.txt").is_file():
        reqs = [
            line.strip()
            for line in (module_dir / "requirements.txt").read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        return "python", {
            "name": module_dir.name,
            "reqs": reqs,
        }
    if (module_dir / "Dockerfile").is_file():
        return "docker", {"name": module_dir.name}
    if any(module_dir.glob("*.py")):
        return "python", {"name": module_dir.name, "reqs": []}
    if any(module_dir.glob("*.js")):
        return "node", {"name": module_dir.name, "scripts": {}, "main": "index.js"}
    if (module_dir / "Chart.yaml").is_file():
        return "helm", {"name": module_dir.name}
    if list(module_dir.glob("*.yaml")) or list(module_dir.glob("*.yml")):
        return "k8s", {"name": module_dir.name}
    return "unknown", {"name": module_dir.name}


def quickstart_for(name: str, kind: str, meta: dict) -> str:
    if kind == "node":
        scripts = meta.get("scripts") or {}
        start = scripts.get("start") or scripts.get("dev") or "node " + meta.get("main", "index.js")
        test = scripts.get("test", "npm test")
        install = "npm install"
        if "pnpm-lock.yaml" in os.listdir(name):
            install = "pnpm install"
        elif "yarn.lock" in os.listdir(name):
            install = "yarn install"
        return f"""# Quickstart: {name}

Node.js / JavaScript module.

## Install

```bash
cd {name}
{install}
```

## Run

```bash
{start}
```

## Test

```bash
{test}
```

## Configuration

- Environment variables: see any `.env.example` in this directory.
- Entry point: `{meta.get('main', 'index.js')}`.
- Version: `{meta.get('version', '?')}`.

## Common commands

```bash
# Format
npx prettier --write .

# Lint
npm run lint   # if defined
```
"""

    if kind == "python":
        reqs = meta.get("reqs") or []
        req_block = chr(10).join(f"  - `{r}`" for r in reqs[:5])
        if len(reqs) > 5:
            req_block += f"{chr(10)}  - ... and {len(reqs) - 5} more (see requirements.txt)"
        return f"""# Quickstart: {name}

Python module.

## Setup

```bash
cd {name}
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Key dependencies

{req_block or "  - (none listed)"}

## Run

```bash
# Adjust entry point as needed
python3 -m {name}          # if __main__.py exists
# or
python3 app.py             # legacy entry
```

## Test

```bash
pytest                     # if tests/ exists
```

## Notes

- See `Dockerfile` (if present) for container-based run.
- See `migrations/` (if present) for schema setup.
"""

    if kind == "docker":
        return f"""# Quickstart: {name}

Containerized service.

## Build

```bash
cd {name}
docker build -t {name}:dev .
```

## Run

```bash
docker run --rm -p 5000:5000 --env-file ../.env {name}:dev
```

## Test

This module is exercised by integration tests in `api-server/tests/`
or by `docker compose up` from the project root.
"""

    if kind == "helm":
        return f"""# Quickstart: {name}

Helm chart for Kubernetes.

## Install

```bash
helm install {name} ./{name}
```

## Upgrade

```bash
helm upgrade {name} ./{name}
```

## Uninstall

```bash
helm uninstall {name}
```

## Render templates locally

```bash
helm template {name} ./{name}
```
"""

    if kind == "k8s":
        return f"""# Quickstart: {name}

Kubernetes manifests.

## Apply

```bash
kubectl apply -f {name}/
```

## Verify

```bash
kubectl get all -l app={name}
```

## Remove

```bash
kubectl delete -f {name}/
```

> These manifests are for learning. See [../DEPLOYMENT.md](../DEPLOYMENT.md)
> for production hardening guidance.
"""

    # unknown
    return f"""# Quickstart: {name}

This module did not have an obvious entry point (no package.json,
requirements.txt, or Dockerfile detected). Browse the directory
contents directly or check the project root
[../SETUP.md](../SETUP.md) for general setup steps.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing QUICKSTART.md")
    ap.add_argument("--root", default=str(PROJECT_ROOT),
                    help="project root (default: this script's parent)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    written = []
    skipped = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name in SKIP_DIRS or entry.name.startswith("."):
            continue
        target = entry / "QUICKSTART.md"
        if target.exists() and not args.force:
            skipped.append(str(target.relative_to(root)))
            continue
        kind, meta = detect_kind(entry)
        content = quickstart_for(entry.name, kind, meta)
        target.write_text(content)
        written.append(str(target.relative_to(root)))

    print(f"Wrote {len(written)} QUICKSTART.md files:")
    for w in written:
        print(f"  + {w}")
    if skipped:
        print(f"\nSkipped {len(skipped)} (already exist; use --force to overwrite):")
        for s in skipped[:5]:
            print(f"  - {s}")
        if len(skipped) > 5:
            print(f"  ... and {len(skipped) - 5} more")


if __name__ == "__main__":
    main()
