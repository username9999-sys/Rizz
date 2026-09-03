# Quickstart: automation

Python module.

## Setup

```bash
cd automation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Key dependencies

  - (none listed)

## Run

```bash
# Adjust entry point as needed
python3 -m automation          # if __main__.py exists
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
