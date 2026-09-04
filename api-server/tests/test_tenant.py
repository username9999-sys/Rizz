"""
Tests for app/utils/tenant.py — multi-tenant support.
"""

import os
import sys
import importlib.util
import pytest
from flask import Flask, g, jsonify

HERE = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.abspath(os.path.join(HERE, ".."))
T_PATH = os.path.join(API_ROOT, "app", "utils", "tenant.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def ten():
    return _load("_test_ten", T_PATH)


@pytest.fixture
def app_with_tenants(ten):
    """Flask app with two tenants installed."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    reg = ten.TenantRegistry()
    reg.add(ten.Tenant(id="t_acme", name="ACME Inc", slug="acme", plan="pro"))
    reg.add(ten.Tenant(id="t_globex", name="Globex", slug="globex", plan="free"))
    ten.install_tenant_middleware(app, registry=reg, require_tenant=True,
                                 exempt_paths=("/health", "/metrics"))
    return app


@pytest.fixture
def client(app_with_tenants):
    return app_with_tenants.test_client()


# ==================== Tenant model ====================

class TestTenant:
    def test_to_dict(self, ten):
        t = ten.Tenant(id="t1", name="Acme", slug="acme", plan="pro")
        d = t.to_dict()
        assert d["id"] == "t1"
        assert d["name"] == "Acme"
        assert d["slug"] == "acme"
        assert d["plan"] == "pro"
        assert d["active"] is True
        assert isinstance(d["created_at"], float)


class TestTenantRegistry:
    def test_add_and_get(self, ten):
        reg = ten.TenantRegistry()
        t = ten.Tenant(id="t1", name="Acme", slug="acme")
        reg.add(t)
        assert reg.get_by_id("t1") is t
        assert reg.get_by_slug("acme") is t

    def test_remove(self, ten):
        reg = ten.TenantRegistry()
        t = ten.Tenant(id="t1", name="Acme", slug="acme")
        reg.add(t)
        reg.remove("t1")
        assert reg.get_by_id("t1") is None
        assert reg.get_by_slug("acme") is None

    def test_all(self, ten):
        reg = ten.TenantRegistry()
        reg.add(ten.Tenant(id="t1", name="A", slug="a"))
        reg.add(ten.Tenant(id="t2", name="B", slug="b"))
        assert len(reg.all()) == 2


# ==================== Tenant creation ====================

class TestCreateTenant:
    def test_create_with_valid_slug(self, ten):
        reg = ten.TenantRegistry()
        t = ten.create_tenant("Acme Inc", "acme", registry=reg)
        assert t.id.startswith("ten_")
        assert t.slug == "acme"
        assert t.plan == "free"
        assert reg.get_by_id(t.id) is t

    def test_create_duplicate_slug_raises(self, ten):
        reg = ten.TenantRegistry()
        ten.create_tenant("First", "acme", registry=reg)
        with pytest.raises(ValueError, match="already exists"):
            ten.create_tenant("Second", "acme", registry=reg)

    def test_invalid_slug_raises(self, ten):
        for bad in ("", "A", "a" * 50, "with space", "-leading", "trailing-",
                    "under_score", "UPPER"):
            with pytest.raises(ValueError, match="slug must be"):
                ten.create_tenant("X", bad)


# ==================== Middleware ====================

class TestMiddleware:
    def test_valid_tenant_header_sets_g(self, app_with_tenants, client):
        @app_with_tenants.route("/whoami")
        def whoami():
            from flask import g
            return jsonify({"tenant_id": g.tenant_id, "name": g.tenant.name})

        r = client.get("/whoami", headers={"X-Tenant-ID": "t_acme"})
        assert r.status_code == 200
        assert r.get_json()["tenant_id"] == "t_acme"
        assert r.get_json()["name"] == "ACME Inc"

    def test_tenant_slug_also_works(self, app_with_tenants, client):
        @app_with_tenants.route("/whoami")
        def whoami():
            from flask import g
            return jsonify({"tenant_id": g.tenant_id})

        r = client.get("/whoami", headers={"X-Tenant-ID": "globex"})
        assert r.status_code == 200
        assert r.get_json()["tenant_id"] == "t_globex"

    def test_missing_tenant_returns_400(self, app_with_tenants, client):
        r = client.get("/whoami")
        assert r.status_code == 400
        assert "Tenant" in r.get_json()["error"]

    def test_unknown_tenant_returns_404(self, app_with_tenants, client):
        r = client.get("/whoami", headers={"X-Tenant-ID": "t_ghost"})
        assert r.status_code == 404

    def test_inactive_tenant_returns_403(self, ten):
        app = Flask(__name__)
        reg = ten.TenantRegistry()
        reg.add(ten.Tenant(id="t_off", name="Off Co", slug="off", active=False))
        ten.install_tenant_middleware(app, registry=reg, require_tenant=True,
                                     exempt_paths=("/health",))

        @app.route("/whoami")
        def whoami():
            from flask import g
            return jsonify({"tenant_id": g.tenant_id})

        c = app.test_client()
        r = c.get("/whoami", headers={"X-Tenant-ID": "t_off"})
        assert r.status_code == 403

    def test_exempt_path_skips_tenant(self, app_with_tenants, client):
        r = client.get("/health")
        assert r.status_code == 404   # route not defined, but middleware did not 400

    def test_response_echoes_tenant_header(self, app_with_tenants, client):
        @app_with_tenants.route("/ping")
        def ping():
            return "pong"

        r = client.get("/ping", headers={"X-Tenant-ID": "t_acme"})
        assert r.headers.get("X-Tenant-ID") == "t_acme"

    def test_subdomain_detection(self, ten):
        app = Flask(__name__)
        reg = ten.TenantRegistry()
        reg.add(ten.Tenant(id="t_acme", name="Acme", slug="acme"))
        ten.install_tenant_middleware(app, registry=reg, require_tenant=True,
                                     exempt_paths=("/health",))

        @app.route("/whoami")
        def whoami():
            from flask import g
            return jsonify({"tenant_id": g.tenant_id})

        c = app.test_client()
        r = c.get("/whoami", headers={"Host": "acme.rizz.dev"})
        assert r.status_code == 200
        assert r.get_json()["tenant_id"] == "t_acme"

    def test_non_tenant_subdomain_returns_404(self, ten):
        """A subdomain that looks like a tenant but doesn't exist -> 404."""
        app = Flask(__name__)
        reg = ten.TenantRegistry()
        ten.install_tenant_middleware(app, registry=reg, require_tenant=True,
                                     exempt_paths=("/health",))
        @app.route("/whoami")
        def whoami():
            return "x"
        c = app.test_client()
        r = c.get("/whoami", headers={"Host": "random.rizz.dev"})
        assert r.status_code == 404  # unknown tenant slug


# ==================== require_tenant decorator ====================

class TestRequireTenantDecorator:
    def test_view_without_tenant_returns_400(self, ten):
        app = Flask(__name__)
        reg = ten.TenantRegistry()
        ten.install_tenant_middleware(app, registry=reg, require_tenant=False,
                                     exempt_paths=("/health",))
        @app.route("/protected")
        @ten.require_tenant
        def protected():
            from flask import g
            return jsonify({"tenant_id": g.tenant_id})

        c = app.test_client()
        r = c.get("/protected")
        assert r.status_code == 400

    def test_view_with_tenant_succeeds(self, ten):
        app = Flask(__name__)
        reg = ten.TenantRegistry()
        reg.add(ten.Tenant(id="t1", name="X", slug="x"))
        ten.install_tenant_middleware(app, registry=reg, require_tenant=True,
                                     exempt_paths=("/health",))
        @app.route("/protected")
        @ten.require_tenant
        def protected():
            from flask import g
            return jsonify({"tenant_id": g.tenant_id})

        c = app.test_client()
        r = c.get("/protected", headers={"X-Tenant-ID": "t1"})
        assert r.status_code == 200
        assert r.get_json()["tenant_id"] == "t1"


# ==================== tenant_filter ====================

class TestTenantFilter:
    def test_filter_without_tenant_asserts(self, ten):
        app = Flask(__name__)
        with app.test_request_context("/"):
            # No tenant attached
            with pytest.raises(AssertionError, match="tenant_filter"):
                ten.tenant_filter(None)

    def test_filter_with_tenant_uses_g_tenant_id(self, ten):
        app = Flask(__name__)
        with app.test_request_context("/"):
            g.tenant_id = "t_xyz"
            captured = {}

            class FakeQuery:
                def filter_by(self, **kwargs):
                    captured.update(kwargs)
                    return "FILTERED"

            result = ten.tenant_filter(FakeQuery())
            assert result == "FILTERED"
            assert captured == {"tenant_id": "t_xyz"}


# ==================== Thread safety ====================

class TestThreadSafety:
    def test_concurrent_adds(self, ten):
        import threading
        reg = ten.TenantRegistry()
        def add(i):
            reg.add(ten.Tenant(id=f"t{i}", name=f"T{i}", slug=f"s{i}"))
        threads = [threading.Thread(target=add, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert len(reg.all()) == 50
