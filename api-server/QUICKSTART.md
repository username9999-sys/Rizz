# Quickstart: api-server

Python module.

## Setup

```bash
cd api-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Key dependencies

  - `Flask==3.0.0`
  - `Flask-CORS==4.0.0`
  - `Flask-Limiter==3.5.0`
  - `Flask-Migrate==4.0.5`
  - `Flask-SQLAlchemy==3.1.1`
  - ... and 47 more (see requirements.txt)

## Run

```bash
# Adjust entry point as needed
python3 -m api-server          # if __main__.py exists
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
