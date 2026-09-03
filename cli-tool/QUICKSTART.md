# Quickstart: cli-tool

Python module.

## Setup

```bash
cd cli-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Key dependencies

  - `click>=8.0.0`

## Run

```bash
# Adjust entry point as needed
python3 -m cli-tool          # if __main__.py exists
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
