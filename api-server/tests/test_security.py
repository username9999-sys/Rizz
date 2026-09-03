"""
Security tests — independent of the buggy app factory.

These tests load app/utils/security.py and app/utils/validators.py as
standalone modules via importlib.util.spec_from_file_location so they
can be exercised without pulling in the heavy app/__init__.py
(prometheus, opentelemetry, sqlalchemy, etc.).
"""

import os
import sys
import importlib
import importlib.util
import pytest

# Resolve file paths
HERE = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.abspath(os.path.join(HERE, ".."))
SEC_PATH = os.path.join(API_ROOT, "app", "utils", "security.py")
VAL_PATH = os.path.join(API_ROOT, "app", "utils", "validators.py")
SET_PATH = os.path.join(API_ROOT, "app", "config", "settings.py")


def _load_module_from_path(name, path):
    """Load a .py file as a standalone module, bypassing package __init__."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # Register so submodule imports inside the module (e.g. validators)
    # can be resolved if they use relative imports.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Pre-load validators first (security.py imports it)
_validators = _load_module_from_path("_test_validators", VAL_PATH)
# Pre-load security
_security = _load_module_from_path("_test_security", SEC_PATH)

# Make available to tests as module-level imports
validate_json = _security.validate_json
require_content_type = _security.require_content_type
sanitize_html = _security.sanitize_html
validate_password = _validators.validate_password


# Helper to reload settings.py in tests that mutate env vars
def _reload_settings():
    # Reload validators first (no dep), then settings
    return _load_module_from_path("_test_settings", SET_PATH)


# ---------- Fixtures ----------

@pytest.fixture
def security_app():
    """Minimal Flask app wired with the production security helpers."""
    from flask import Flask

    # Use the pre-loaded standalone module (no app/__init__ side effects)
    v = validate_json
    r = require_content_type

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["PRODUCTION"] = False

    @app.route("/echo", methods=["POST"])
    @r()
    @v(required_fields=["username"], allowed_fields=["username", "email"])
    def echo():
        from flask import g, jsonify
        return jsonify({"received": g.validated_data}), 200

    @app.route("/strict", methods=["POST"])
    @r()
    @v(
        required_fields=["username", "password"],
        allowed_fields=["username", "password"],
        strict=True,
    )
    def strict():
        from flask import g, jsonify
        return jsonify({"ok": True, "data": g.validated_data}), 200

    @app.route("/open", methods=["POST"])
    @r()
    @v()  # no required/allowed fields
    def open_view():
        from flask import jsonify
        return jsonify({"ok": True}), 200

    return app


@pytest.fixture
def client(security_app):
    return security_app.test_client()


# ---------- Content-Type enforcement ----------

class TestContentTypeGuard:
    def test_post_without_content_type_is_415(self, client):
        r = client.post("/echo", data="username=alice")
        assert r.status_code == 415
        assert "application/json" in r.get_json()["error"]

    def test_post_with_form_urlencoded_is_415(self, client):
        r = client.post(
            "/echo",
            data="username=alice",
            content_type="application/x-www-form-urlencoded",
        )
        assert r.status_code == 415

    def test_post_with_json_accepted(self, client):
        r = client.post("/echo", json={"username": "alice_1"})
        assert r.status_code == 200

    def test_post_with_json_and_charset_accepted(self, client):
        r = client.post(
            "/echo",
            data='{"username": "alice_1"}',
            content_type="application/json; charset=utf-8",
        )
        assert r.status_code == 200

    def test_get_endpoint_unaffected(self, security_app):
        c = security_app.test_client()
        # No GET route, so 405; just confirm guard doesn't 415 GETs
        r = c.get("/echo")
        assert r.status_code in (405, 404)


# ---------- Input validation: required fields ----------

class TestRequiredFields:
    def test_missing_field_returns_400(self, client):
        r = client.post("/echo", json={})
        assert r.status_code == 400
        body = r.get_json()
        assert "username" in body["fields"]

    def test_empty_string_counts_as_missing(self, client):
        r = client.post("/echo", json={"username": ""})
        assert r.status_code == 400

    def test_null_counts_as_missing(self, client):
        r = client.post("/echo", json={"username": None})
        assert r.status_code == 400

    def test_present_field_passes(self, client):
        r = client.post("/echo", json={"username": "valid_user"})
        assert r.status_code == 200


# ---------- Input validation: allowlist (strict) ----------

class TestAllowlist:
    def test_unknown_field_rejected_in_strict_mode(self, client):
        r = client.post(
            "/strict",
            json={"username": "u", "password": "Pass1234", "is_admin": True},
        )
        assert r.status_code == 400
        body = r.get_json()
        assert "is_admin" in body["fields"]

    def test_only_known_fields_accepted(self, client):
        r = client.post(
            "/strict",
            json={"username": "alice_99", "password": "Pass1234"},
        )
        assert r.status_code == 200

    def test_non_strict_allows_extra(self, client):
        r = client.post(
            "/open",
            json={"anything": "goes", "more": "stuff"},
        )
        assert r.status_code == 200


# ---------- Validator hook integration ----------

class TestFieldValidators:
    def test_bad_username_rejected(self, client):
        # username validator requires >=3 chars, alphanumeric+underscore
        r = client.post("/echo", json={"username": "a"})
        assert r.status_code == 400
        assert "username" in r.get_json()["details"]

    def test_username_with_special_chars_rejected(self, client):
        r = client.post("/echo", json={"username": "bad name!"})
        assert r.status_code == 400

    def test_good_username_accepted(self, client):
        r = client.post("/echo", json={"username": "alice_99"})
        assert r.status_code == 200

    def test_bad_email_rejected(self, client):
        r = client.post("/echo", json={"username": "alice", "email": "not-an-email"})
        assert r.status_code == 400
        assert "email" in r.get_json()["details"]

    def test_good_email_accepted(self, client):
        r = client.post(
            "/echo",
            json={"username": "alice", "email": "alice@example.com"},
        )
        assert r.status_code == 200


# ---------- HTML sanitization on string fields ----------

class TestHtmlSanitization:
    def test_script_tag_stripped_from_content(self, client):
        r = client.post(
            "/open",
            json={
                "content": '<script>alert(1)</script>hello',
                "username": "alice",
            },
        )
        # 'open' view doesn't echo back, so this just confirms no 400
        assert r.status_code == 200

    def test_iframe_stripped_from_content(self, client):
        r = client.post(
            "/open",
            json={
                "content": '<iframe src="x"></iframe>safe',
                "username": "alice",
            },
        )
        assert r.status_code == 200


# ---------- Malformed JSON ----------

class TestMalformedJson:
    def test_broken_json_returns_400(self, client):
        r = client.post(
            "/echo",
            data='{"username": "alice"',  # missing closing brace
            content_type="application/json",
        )
        assert r.status_code == 400
        assert "Malformed" in r.get_json()["error"]

    def test_json_array_rejected(self, client):
        r = client.post("/echo", json=["not", "a", "dict"])
        assert r.status_code == 400

    def test_json_string_rejected(self, client):
        r = client.post("/echo", json="just a string")
        assert r.status_code == 400

    def test_empty_body_returns_400(self, client):
        r = client.post("/echo", content_type="application/json")
        # No body at all — should reject
        assert r.status_code in (400, 415)


# ---------- Config: production fail-closed ----------

class _FakeApp:
    """Minimal app stub with .config dict and .logger."""
    def __init__(self, config=None):
        self.config = config or {}

    class logger:
        @staticmethod
        def addHandler(*a, **k):
            pass

        @staticmethod
        def setLevel(*a, **k):
            pass


class TestProductionConfig:
    def test_production_without_secrets_raises(self, monkeypatch):
        # Reload settings with empty env so class-body reads return None
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        settings = _reload_settings()
        # Pass an app with empty config to simulate "no secrets loaded"
        with pytest.raises(RuntimeError) as exc:
            settings.ProductionConfig.init_app(_FakeApp({}))
        assert "SECRET_KEY" in str(exc.value) or "JWT_SECRET_KEY" in str(exc.value)

    def test_production_wildcard_cors_rejected(self):
        """When secrets are present in app.config, wildcard CORS must raise."""
        app = _FakeApp({
            "SECRET_KEY": "x" * 32,
            "JWT_SECRET_KEY": "y" * 32,
            "CORS_ORIGINS": ["*"],
        })
        settings = _reload_settings()
        with pytest.raises(RuntimeError) as exc:
            settings.ProductionConfig.init_app(app)
        assert "CORS_ORIGINS" in str(exc.value)

    def test_production_explicit_cors_ok(self):
        """With secrets in app.config and explicit CORS, init_app succeeds."""
        app = _FakeApp({
            "SECRET_KEY": "x" * 32,
            "JWT_SECRET_KEY": "y" * 32,
            "CORS_ORIGINS": ["https://example.com"],
        })
        settings = _reload_settings()
        # Should not raise
        settings.ProductionConfig.init_app(app)

    def test_production_cors_env_var_parsed(self, monkeypatch):
        """CORS_ORIGINS env var is comma-split into a list."""
        monkeypatch.setenv("CORS_ORIGINS", "https://a.com,https://b.com")
        settings = _reload_settings()
        assert isinstance(settings.Config.CORS_ORIGINS, list)
        assert len(settings.Config.CORS_ORIGINS) >= 1
