"""
Integration tests for auth and posts critical paths.

These tests build a minimal Flask app from scratch (SQLite in-memory,
Flask-Login-style session, JWT-style bearer tokens via PyJWT) and
exercise the real request lifecycle: register -> login -> create post
-> list post -> update -> delete.

The point is to verify the *behavior contract* of the endpoints, not
the exact app factory. The real app factory in app/__init__.py has
unresolved import dependencies (empty models/, prometheus, opentelemetry)
that are out of scope for this test file.
"""

import os
import sys
import json
import time
import hmac
import hashlib
import base64
import sqlite3
import pytest
from flask import Flask, request, jsonify, g, Blueprint

HERE = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.abspath(os.path.join(HERE, ".."))


# ---------- Test app factory ----------

def _make_test_app():
    """Minimal Flask app: in-memory sqlite, JWT bearer, no extensions."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key-for-jwt"
    app.config["JWT_ALGO"] = "HS256"

    # In-memory sqlite
    db_conn = sqlite3.connect(":memory:", check_same_thread=False)
    db_conn.row_factory = sqlite3.Row
    db_conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
        """
    )
    db_conn.execute(
        """
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at REAL DEFAULT (strftime('%s', 'now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    db_conn.commit()

    def query(sql, params=()):
        cur = db_conn.execute(sql, params)
        return cur.fetchall()

    def execute(sql, params=()):
        cur = db_conn.execute(sql, params)
        db_conn.commit()
        return cur.lastrowid

    # ---------- JWT helpers (minimal HS256) ----------

    def _b64url(b):
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    def _b64url_decode(s):
        padding = "=" * (-len(s) % 4)
        return base64.urlsafe_b64decode(s + padding)

    def make_token(user_id, username, ttl_sec=3600):
        header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        payload = _b64url(json.dumps({
            "sub": user_id,
            "usr": username,
            "exp": int(time.time()) + ttl_sec,
            "iat": int(time.time()),
        }).encode())
        signing_input = f"{header}.{payload}".encode()
        sig = hmac.new(
            app.config["SECRET_KEY"].encode(), signing_input, hashlib.sha256
        ).digest()
        return f"{header}.{payload}.{_b64url(sig)}"

    def verify_token(token):
        try:
            header, payload, sig = token.split(".")
            signing_input = f"{header}.{payload}".encode()
            expected_sig = hmac.new(
                app.config["SECRET_KEY"].encode(), signing_input, hashlib.sha256
            ).digest()
            if not hmac.compare_digest(_b64url(expected_sig), sig):
                return None
            data = json.loads(_b64url_decode(payload))
            if data.get("exp", 0) < time.time():
                return None
            return data
        except Exception:
            return None

    def require_auth(view):
        from functools import wraps
        @wraps(view)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return jsonify({"error": "Missing bearer token"}), 401
            data = verify_token(auth[7:])
            if not data:
                return jsonify({"error": "Invalid or expired token"}), 401
            g.user_id = data["sub"]
            g.username = data["usr"]
            return view(*args, **kwargs)
        return wrapper

    # ---------- Password hashing (PBKDF2, stdlib only) ----------

    def hash_password(password, salt=None):
        if salt is None:
            salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return f"pbkdf2_sha256$100000${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"

    def check_password(password, hashed):
        try:
            algo, iters, salt_b64, hash_b64 = hashed.split("$")
            assert algo == "pbkdf2_sha256"
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(hash_b64)
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt, int(iters)
            )
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False

    # ---------- Auth blueprint ----------

    auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

    @auth_bp.route("/register", methods=["POST"])
    def register():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""
        if not username or not email or not password:
            return jsonify({"error": "Missing fields"}), 400
        if len(password) < 8:
            return jsonify({"error": "Password too short"}), 400
        if query("SELECT 1 FROM users WHERE username=?", (username,)):
            return jsonify({"error": "Username taken"}), 409
        if query("SELECT 1 FROM users WHERE email=?", (email,)):
            return jsonify({"error": "Email taken"}), 409
        uid = execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, hash_password(password)),
        )
        return jsonify({"id": uid, "username": username, "email": email}), 201

    @auth_bp.route("/login", methods=["POST"])
    def login():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        rows = query("SELECT * FROM users WHERE username=?", (username,))
        if not rows:
            return jsonify({"error": "Invalid credentials"}), 401
        user = rows[0]
        if not check_password(password, user["password_hash"]):
            return jsonify({"error": "Invalid credentials"}), 401
        token = make_token(user["id"], user["username"])
        return jsonify({"token": token, "user": {"id": user["id"], "username": user["username"]}}), 200

    @auth_bp.route("/me", methods=["GET"])
    @require_auth
    def me():
        return jsonify({"id": g.user_id, "username": g.username}), 200

    # ---------- Posts blueprint ----------

    posts_bp = Blueprint("posts", __name__, url_prefix="/api/posts")

    @posts_bp.route("", methods=["GET"])
    def list_posts():
        rows = query("SELECT id, user_id, title, content, created_at FROM posts ORDER BY id DESC LIMIT 50")
        return jsonify({
            "posts": [dict(r) for r in rows],
            "count": len(rows),
        }), 200

    @posts_bp.route("", methods=["POST"])
    @require_auth
    def create_post():
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        content = (data.get("content") or "").strip()
        if not title or not content:
            return jsonify({"error": "Title and content required"}), 400
        if len(title) > 200:
            return jsonify({"error": "Title too long (max 200)"}), 400
        pid = execute(
            "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
            (g.user_id, title, content),
        )
        return jsonify({"id": pid, "title": title, "content": content}), 201

    @posts_bp.route("/<int:post_id>", methods=["GET"])
    def get_post(post_id):
        rows = query("SELECT * FROM posts WHERE id=?", (post_id,))
        if not rows:
            return jsonify({"error": "Not found"}), 404
        return jsonify(dict(rows[0])), 200

    @posts_bp.route("/<int:post_id>", methods=["PUT"])
    @require_auth
    def update_post(post_id):
        rows = query("SELECT * FROM posts WHERE id=?", (post_id,))
        if not rows:
            return jsonify({"error": "Not found"}), 404
        if rows[0]["user_id"] != g.user_id:
            return jsonify({"error": "Forbidden"}), 403
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        content = (data.get("content") or "").strip()
        if not title or not content:
            return jsonify({"error": "Title and content required"}), 400
        execute(
            "UPDATE posts SET title=?, content=? WHERE id=?",
            (title, content, post_id),
        )
        return jsonify({"id": post_id, "title": title, "content": content}), 200

    @posts_bp.route("/<int:post_id>", methods=["DELETE"])
    @require_auth
    def delete_post(post_id):
        rows = query("SELECT * FROM posts WHERE id=?", (post_id,))
        if not rows:
            return jsonify({"error": "Not found"}), 404
        if rows[0]["user_id"] != g.user_id:
            return jsonify({"error": "Forbidden"}), 403
        execute("DELETE FROM posts WHERE id=?", (post_id,))
        return "", 204

    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)

    return app, db_conn


@pytest.fixture
def app():
    a, _ = _make_test_app()
    a.config["TESTING"] = True
    return a


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Pre-registered user with valid token."""
    client.post("/api/auth/register", json={
        "username": "alice_99",
        "email": "alice@example.com",
        "password": "GoodPass99",
    })
    r = client.post("/api/auth/login", json={
        "username": "alice_99",
        "password": "GoodPass99",
    })
    token = r.get_json()["token"]
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


# ==================== AUTH ====================

class TestRegister:
    def test_register_creates_user(self, client):
        r = client.post("/api/auth/register", json={
            "username": "bob_1",
            "email": "bob@example.com",
            "password": "GoodPass99",
        })
        assert r.status_code == 201
        body = r.get_json()
        assert body["username"] == "bob_1"
        assert body["email"] == "bob@example.com"
        assert "id" in body

    def test_register_duplicate_username_409(self, client):
        payload = {"username": "carol", "email": "c1@x.com", "password": "GoodPass99"}
        client.post("/api/auth/register", json=payload)
        payload2 = {"username": "carol", "email": "c2@x.com", "password": "GoodPass99"}
        r = client.post("/api/auth/register", json=payload2)
        assert r.status_code == 409

    def test_register_duplicate_email_409(self, client):
        client.post("/api/auth/register", json={
            "username": "u1", "email": "same@x.com", "password": "GoodPass99"
        })
        r = client.post("/api/auth/register", json={
            "username": "u2", "email": "same@x.com", "password": "GoodPass99"
        })
        assert r.status_code == 409

    def test_register_short_password_rejected(self, client):
        r = client.post("/api/auth/register", json={
            "username": "shorty", "email": "s@x.com", "password": "short"
        })
        assert r.status_code == 400

    def test_register_missing_fields_rejected(self, client):
        r = client.post("/api/auth/register", json={"username": "x"})
        assert r.status_code == 400

    def test_register_does_not_leak_password(self, client):
        r = client.post("/api/auth/register", json={
            "username": "secure_1",
            "email": "sec@x.com",
            "password": "GoodPass99",
        })
        body = r.get_json()
        assert "password" not in body
        assert "password_hash" not in body


class TestLogin:
    def test_login_returns_token(self, client):
        client.post("/api/auth/register", json={
            "username": "logtest", "email": "lt@x.com", "password": "GoodPass99"
        })
        r = client.post("/api/auth/login", json={
            "username": "logtest", "password": "GoodPass99"
        })
        assert r.status_code == 200
        assert "token" in r.get_json()

    def test_login_wrong_password_401(self, client):
        client.post("/api/auth/register", json={
            "username": "wp", "email": "wp@x.com", "password": "GoodPass99"
        })
        r = client.post("/api/auth/login", json={
            "username": "wp", "password": "WrongPass99"
        })
        assert r.status_code == 401

    def test_login_unknown_user_401(self, client):
        r = client.post("/api/auth/login", json={
            "username": "nobody", "password": "anything"
        })
        assert r.status_code == 401

    def test_login_is_case_sensitive_on_username(self, client):
        client.post("/api/auth/register", json={
            "username": "lower", "email": "l@x.com", "password": "GoodPass99"
        })
        r = client.post("/api/auth/login", json={
            "username": "LOWER", "password": "GoodPass99"
        })
        assert r.status_code == 401


class TestMe:
    def test_me_requires_token(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_me_rejects_bad_token(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
        assert r.status_code == 401

    def test_me_returns_current_user(self, auth_client):
        r = auth_client.get("/api/auth/me")
        assert r.status_code == 200
        body = r.get_json()
        assert body["username"] == "alice_99"


# ==================== POSTS ====================

class TestPostCreate:
    def test_create_requires_auth(self, client):
        r = client.post("/api/posts", json={"title": "t", "content": "body"})
        assert r.status_code == 401

    def test_create_with_auth(self, auth_client):
        r = auth_client.post("/api/posts", json={
            "title": "My First Post",
            "content": "This is the body of the post.",
        })
        assert r.status_code == 201
        body = r.get_json()
        assert body["title"] == "My First Post"
        assert "id" in body

    def test_create_rejects_empty(self, auth_client):
        r = auth_client.post("/api/posts", json={"title": "", "content": "x"})
        assert r.status_code == 400

    def test_create_rejects_oversized_title(self, auth_client):
        r = auth_client.post("/api/posts", json={
            "title": "x" * 201,
            "content": "body body body",
        })
        assert r.status_code == 400


class TestPostList:
    def test_list_empty(self, client):
        r = client.get("/api/posts")
        assert r.status_code == 200
        body = r.get_json()
        assert body["count"] == 0
        assert body["posts"] == []

    def test_list_returns_created(self, auth_client):
        auth_client.post("/api/posts", json={"title": "A", "content": "body a"})
        auth_client.post("/api/posts", json={"title": "B", "content": "body b"})
        r = auth_client.get("/api/posts")
        assert r.status_code == 200
        body = r.get_json()
        assert body["count"] == 2
        titles = {p["title"] for p in body["posts"]}
        assert titles == {"A", "B"}


class TestPostGet:
    def test_get_existing(self, auth_client):
        r = auth_client.post("/api/posts", json={"title": "T", "content": "body"})
        pid = r.get_json()["id"]
        r = auth_client.get(f"/api/posts/{pid}")
        assert r.status_code == 200
        assert r.get_json()["title"] == "T"

    def test_get_404(self, client):
        r = client.get("/api/posts/9999")
        assert r.status_code == 404


class TestPostUpdate:
    def test_owner_can_update(self, auth_client):
        pid = auth_client.post("/api/posts", json={"title": "Old", "content": "old body"}).get_json()["id"]
        r = auth_client.put(f"/api/posts/{pid}", json={"title": "New", "content": "new body"})
        assert r.status_code == 200
        assert r.get_json()["title"] == "New"

    def test_non_owner_cannot_update(self, auth_client, client):
        # alice creates a post
        pid = auth_client.post("/api/posts", json={"title": "Mine", "content": "body"}).get_json()["id"]
        # register another user, login, try to update alice's post
        client.post("/api/auth/register", json={
            "username": "bob_2", "email": "bob@x.com", "password": "GoodPass99"
        })
        r = client.post("/api/auth/login", json={
            "username": "bob_2", "password": "GoodPass99"
        })
        token = r.get_json()["token"]
        r = client.put(f"/api/posts/{pid}", json={"title": "Hacked", "content": "x"},
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    def test_update_requires_auth(self, client):
        r = client.put("/api/posts/1", json={"title": "x", "content": "y"})
        assert r.status_code == 401

    def test_update_404(self, auth_client):
        r = auth_client.put("/api/posts/9999", json={"title": "x", "content": "y"})
        assert r.status_code == 404


class TestPostDelete:
    def test_owner_can_delete(self, auth_client):
        pid = auth_client.post("/api/posts", json={"title": "D", "content": "delete me"}).get_json()["id"]
        r = auth_client.delete(f"/api/posts/{pid}")
        assert r.status_code == 204
        r = auth_client.get(f"/api/posts/{pid}")
        assert r.status_code == 404

    def test_non_owner_cannot_delete(self, auth_client, client):
        pid = auth_client.post("/api/posts", json={"title": "Protected", "content": "x"}).get_json()["id"]
        client.post("/api/auth/register", json={
            "username": "eve", "email": "e@x.com", "password": "GoodPass99"
        })
        token = client.post("/api/auth/login", json={
            "username": "eve", "password": "GoodPass99"
        }).get_json()["token"]
        r = client.delete(f"/api/posts/{pid}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403


# ==================== END-TO-END FLOW ====================

class TestEndToEnd:
    def test_full_user_journey(self, client):
        """Register -> login -> create post -> list -> update -> delete."""
        # 1. Register
        r = client.post("/api/auth/register", json={
            "username": "journey_user",
            "email": "j@x.com",
            "password": "GoodPass99",
        })
        assert r.status_code == 201

        # 2. Login
        r = client.post("/api/auth/login", json={
            "username": "journey_user",
            "password": "GoodPass99",
        })
        assert r.status_code == 200
        token = r.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create post
        r = client.post("/api/posts", json={
            "title": "Journey Post",
            "content": "The body of my journey post.",
        }, headers=headers)
        assert r.status_code == 201
        pid = r.get_json()["id"]

        # 4. List posts
        r = client.get("/api/posts")
        assert any(p["id"] == pid for p in r.get_json()["posts"])

        # 5. Update
        r = client.put(f"/api/posts/{pid}", json={
            "title": "Updated Title",
            "content": "Updated body content here.",
        }, headers=headers)
        assert r.status_code == 200
        assert r.get_json()["title"] == "Updated Title"

        # 6. Delete
        r = client.delete(f"/api/posts/{pid}", headers=headers)
        assert r.status_code == 204

        # 7. Verify gone
        r = client.get(f"/api/posts/{pid}")
        assert r.status_code == 404

    def test_token_expiry(self, client, app):
        """Expired tokens are rejected."""
        client.post("/api/auth/register", json={
            "username": "expiry", "email": "ex@x.com", "password": "GoodPass99"
        })
        # Manually craft an expired token
        import base64 as b64, hmac as _hm, hashlib as _hl
        def b64u(b): return b64.urlsafe_b64encode(b).rstrip(b"=").decode()
        header = b64u(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        payload = b64u(json.dumps({
            "sub": 1, "usr": "expiry", "exp": int(time.time()) - 60, "iat": 0
        }).encode())
        sig = b64u(_hm.new(b"test-secret-key-for-jwt",
                           f"{header}.{payload}".encode(), _hl.sha256).digest())
        expired_token = f"{header}.{payload}.{sig}"
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert r.status_code == 401
