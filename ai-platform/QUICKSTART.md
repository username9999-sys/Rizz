# Quickstart: ai-platform

Python module.

## Setup

```bash
cd ai-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Key dependencies

  - `{`
  - `"name": "rizz-ai-platform",`
  - `"version": "1.0.0",`
  - `"description": "Enterprise AI/ML Platform with Model Serving",`
  - `"main": "src/api/index.py",`
  - ... and 31 more (see requirements.txt)

## Run

```bash
# Adjust entry point as needed
python3 -m ai-platform          # if __main__.py exists
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
