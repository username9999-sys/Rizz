"""
Debug preset for the Rizz API.

Import in your development environment:

    from app.config.debug import apply_debug
    apply_debug(app)

The preset is safe to import in any environment — `apply_debug` checks
the FLASK_ENV / PRODUCTION flag before applying anything that would
leak information in production.
"""

import logging
import os
import sys


def is_dev() -> bool:
    """True if the runtime looks like a dev environment."""
    env = os.environ.get("FLASK_ENV", "production").lower()
    if env in ("development", "dev", "test"):
        return True
    debug_flag = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    return debug_flag


def apply_debug(app) -> None:
    """Apply debug-friendly settings to a Flask app.

    Effects:
      - Set Flask debug mode on
      - Verbose log format with timestamp, level, module, message
      - Log level DEBUG when in dev
      - Add SQLAlchemy echo for query inspection (if SQLAlchemy is used)
      - Enable Flask's interactive debugger
    """
    if not is_dev():
        # Be paranoid: do nothing in production even if called by mistake
        return

    app.config["DEBUG"] = True
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    # Set up console logging at DEBUG level
    level = logging.DEBUG
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    # Quieter noisy libraries
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("werkzeug").setLevel(logging.INFO)

    # SQLAlchemy query echo (only if the extension is present)
    try:
        from flask_sqlalchemy import get_debug_queries
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
        app.config["SQLALCHEMY_ECHO"] = os.environ.get("SQL_ECHO", "0") == "1"
    except ImportError:
        pass

    # Werkzeug request log (helpful for development)
    logging.getLogger("werkzeug").setLevel(logging.INFO)

    app.logger.info("Debug mode enabled (FLASK_ENV=%s)", os.environ.get("FLASK_ENV"))


def quiet_loggers():
    """Silence chatty loggers in dev too. Call before apply_debug if needed."""
    for name in ("boto3", "botocore", "s3transfer", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)
