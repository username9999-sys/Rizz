"""
Tests for app/utils/session.py — JWT session manager.
"""

import os
import sys
import time
import pytest
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.abspath(os.path.join(HERE, ".."))
SES_PATH = os.path.join(API_ROOT, "app", "utils", "session.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def smod():
    return _load("_test_s", SES_PATH)


@pytest.fixture
def sm(smod):
    """Session manager with deterministic clock and short TTLs for fast tests."""
    return smod.SessionManager(
        secret=os.urandom(32),
        access_ttl=10,
        refresh_ttl=60,
        clock=lambda: 1000.0,
    )


# ==================== Secret & init ====================

class TestInit:
    def test_secret_must_be_bytes(self, smod):
        with pytest.raises(ValueError):
            smod.SessionManager(secret="short", access_ttl=10, refresh_ttl=60)

    def test_secret_too_short_rejected(self, smod):
        with pytest.raises(ValueError, match="16 random bytes"):
            smod.SessionManager(secret=b"short", access_ttl=10, refresh_ttl=60)

    def test_valid_init(self, smod):
        sm = smod.SessionManager(secret=os.urandom(32), access_ttl=10, refresh_ttl=60)
        assert sm.access_ttl == 10
        assert sm.refresh_ttl == 60


class TestNewSecret:
    def test_returns_bytes(self, smod):
        s = smod.new_secret()
        assert isinstance(s, bytes)
        assert len(s) >= 32

    def test_secrets_unique(self, smod):
        secrets = {smod.new_secret() for _ in range(20)}
        assert len(secrets) == 20


# ==================== Issue pair ====================

class TestIssuePair:
    def test_returns_access_and_refresh(self, sm):
        pair = sm.issue_pair(user_id=42, username="alice")
        assert "access_token" in pair
        assert "refresh_token" in pair
        assert "jti" in pair
        assert "access_exp" in pair
        assert "refresh_exp" in pair

    def test_access_and_refresh_differ(self, sm):
        pair = sm.issue_pair(user_id=42, username="alice")
        assert pair["access_token"] != pair["refresh_token"]

    def test_access_exp_equals_clock_plus_access_ttl(self, sm):
        pair = sm.issue_pair(user_id=42, username="alice")
        assert pair["access_exp"] == 1000 + 10

    def test_refresh_exp_equals_clock_plus_refresh_ttl(self, sm):
        pair = sm.issue_pair(user_id=42, username="alice")
        assert pair["refresh_exp"] == 1000 + 60

    def test_extra_claims_in_access(self, sm):
        pair = sm.issue_pair(user_id=42, username="alice",
                             extra_claims={"role": "admin", "mfa": True})
        claims = sm.verify_access(pair["access_token"])
        assert claims["role"] == "admin"
        assert claims["mfa"] is True


# ==================== Access verify ====================

class TestAccessVerify:
    def test_valid_access_verifies(self, sm):
        pair = sm.issue_pair(user_id=42, username="alice")
        claims = sm.verify_access(pair["access_token"])
        assert claims["sub"] == "42"
        assert claims["usr"] == "alice"
        assert claims["type"] == "access"

    def test_refresh_rejected_as_access(self, sm, smod):
        pair = sm.issue_pair(user_id=42, username="alice")
        with pytest.raises(smod.TokenInvalid, match="not an access token"):
            sm.verify_access(pair["refresh_token"])

    def test_tampered_signature_rejected(self, sm, smod):
        pair = sm.issue_pair(user_id=42, username="alice")
        h, p, s = pair["access_token"].split(".")
        tampered = f"{h}.{p}.aaaa"
        with pytest.raises(smod.TokenInvalid):
            sm.verify_access(tampered)

    def test_expired_access_rejected(self, sm, smod):
        pair = sm.issue_pair(user_id=42, username="alice")
        # advance clock past TTL
        sm._clock = lambda: 2000.0
        with pytest.raises(smod.TokenExpired):
            sm.verify_access(pair["access_token"])

    def test_malformed_token_rejected(self, sm, smod):
        with pytest.raises(smod.TokenInvalid):
            sm.verify_access("not-a-jwt")
        with pytest.raises(smod.TokenInvalid):
            sm.verify_access("a.b")
        with pytest.raises(smod.TokenInvalid):
            sm.verify_access("")


# ==================== Refresh rotation ====================

class TestRefreshRotation:
    def test_first_use_succeeds(self, sm):
        pair = sm.issue_pair(user_id=42, username="alice")
        new = sm.rotate_refresh(pair["refresh_token"])
        assert "access_token" in new
        assert "refresh_token" in new
        assert new["refresh_token"] != pair["refresh_token"]

    def test_second_use_of_same_token_revokes_family(self, sm, smod):
        """Replay protection: re-using a rotated token revokes all sessions."""
        pair = sm.issue_pair(user_id=42, username="alice")
        new = sm.rotate_refresh(pair["refresh_token"])
        # Now try to use the ORIGINAL refresh again
        with pytest.raises(smod.TokenRevoked, match="reuse detected"):
            sm.rotate_refresh(pair["refresh_token"])

    def test_after_replay_all_user_sessions_revoked(self, sm, smod):
        """Reusing a rotated refresh token revokes the entire session family.

        After rotating pair1, attempting to use pair1's refresh again
        (the replay attack) must trigger family-wide revocation.
        """
        pair1 = sm.issue_pair(user_id=42, username="alice")
        pair2 = sm.issue_pair(user_id=42, username="alice")
        # Rotate pair1 normally
        sm.rotate_refresh(pair1["refresh_token"])
        # Replay pair1's original refresh — must raise and revoke family
        with pytest.raises(smod.TokenRevoked, match="reuse detected"):
            sm.rotate_refresh(pair1["refresh_token"])
        # After replay detection, both pair1's NEW refresh and pair2 are revoked
        with pytest.raises(smod.TokenRevoked):
            sm.rotate_refresh(pair2["refresh_token"])

    def test_rotated_token_chain_works(self, sm):
        """Each rotation produces a valid next refresh token."""
        pair = sm.issue_pair(user_id=42, username="alice")
        for _ in range(5):
            pair = sm.rotate_refresh(pair["refresh_token"])
            assert pair["refresh_token"]

    def test_revoked_refresh_cannot_rotate(self, sm, smod):
        pair = sm.issue_pair(user_id=42, username="alice")
        sm.revoke_refresh(pair["refresh_token"])
        with pytest.raises(smod.TokenRevoked):
            sm.rotate_refresh(pair["refresh_token"])

    def test_user_revoke_blocks_all(self, sm, smod):
        pair1 = sm.issue_pair(user_id=42, username="alice")
        pair2 = sm.issue_pair(user_id=42, username="alice")
        n = sm.revoke_user(42)
        assert n == 2
        with pytest.raises(smod.TokenRevoked):
            sm.rotate_refresh(pair1["refresh_token"])
        with pytest.raises(smod.TokenRevoked):
            sm.rotate_refresh(pair2["refresh_token"])

    def test_other_user_unaffected_by_revoke(self, sm):
        pair1 = sm.issue_pair(user_id=42, username="alice")
        pair2 = sm.issue_pair(user_id=99, username="bob")
        sm.revoke_user(42)
        # bob's token still works
        new = sm.rotate_refresh(pair2["refresh_token"])
        assert "access_token" in new

    def test_expired_refresh_rejected(self, sm, smod):
        pair = sm.issue_pair(user_id=42, username="alice")
        # advance past refresh_ttl (60s)
        sm._clock = lambda: 2000.0
        with pytest.raises(smod.TokenExpired):
            sm.rotate_refresh(pair["refresh_token"])


# ==================== Concurrency ====================

class TestConcurrency:
    def test_concurrent_rotation_only_one_succeeds(self, smod):
        """Two threads racing to rotate the same refresh: only one wins."""
        import threading
        sm = smod.SessionManager(secret=os.urandom(32), access_ttl=10, refresh_ttl=60)
        pair = sm.issue_pair(user_id=42, username="alice")
        results = {"success": 0, "error": 0}
        lock = threading.Lock()
        def rotate():
            try:
                sm.rotate_refresh(pair["refresh_token"])
                with lock:
                    results["success"] += 1
            except Exception:
                with lock:
                    results["error"] += 1
        threads = [threading.Thread(target=rotate) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert results["success"] == 1, f"expected 1 success, got {results}"
        assert results["error"] == 9


# ==================== Revocation store ====================

class TestCustomStore:
    def test_uses_provided_store(self, smod):
        store = {}
        sm = smod.SessionManager(secret=os.urandom(32),
                                 access_ttl=10, refresh_ttl=60,
                                 store=store)
        sm.issue_pair(42, "alice")
        assert any(k for k in store if k != "_test")  # at least one entry
