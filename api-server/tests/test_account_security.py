"""
Tests for app/utils/account_security.py — password policy + account lockout.
"""

import os
import sys
import time
import pytest
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.abspath(os.path.join(HERE, ".."))
AS_PATH = os.path.join(API_ROOT, "app", "utils", "account_security.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def asec():
    return _load("_test_as", AS_PATH)


# ==================== Password complexity ====================

class TestPasswordComplexity:
    def test_valid_password_passes(self, asec):
        asec.check_password_complexity("GoodPass99")  # no raise
        asec.check_password_complexity("aB1aaaaa")  # 8 chars, all classes

    def test_too_short(self, asec):
        with pytest.raises(asec.PasswordPolicyError, match="at least 8"):
            asec.check_password_complexity("Ab1")

    def test_too_long(self, asec):
        with pytest.raises(asec.PasswordPolicyError, match="at most"):
            asec.check_password_complexity("A1" + "a" * 200)

    def test_missing_uppercase(self, asec):
        with pytest.raises(asec.PasswordPolicyError, match="uppercase"):
            asec.check_password_complexity("badpass99")

    def test_missing_lowercase(self, asec):
        with pytest.raises(asec.PasswordPolicyError, match="lowercase"):
            asec.check_password_complexity("BADPASS99")

    def test_missing_digit(self, asec):
        with pytest.raises(asec.PasswordPolicyError, match="digit"):
            asec.check_password_complexity("BadPassword")

    def test_weak_substring_rejected(self, asec):
        with pytest.raises(asec.PasswordPolicyError, match="weak substring"):
            asec.check_password_complexity("MyPassword99")
        with pytest.raises(asec.PasswordPolicyError):
            asec.check_password_complexity("QwertyABC1")
        with pytest.raises(asec.PasswordPolicyError):
            asec.check_password_complexity("LetmeinABC1")

    def test_non_string_input_rejected(self, asec):
        with pytest.raises(asec.PasswordPolicyError):
            asec.check_password_complexity(None)
        with pytest.raises(asec.PasswordPolicyError):
            asec.check_password_complexity(12345678)

    def test_custom_min_length(self, asec):
        with pytest.raises(asec.PasswordPolicyError):
            asec.check_password_complexity("Ab1aaaaa", min_length=10)
        asec.check_password_complexity("Ab1aaaaaaaa", min_length=10)

    def test_can_disable_classes(self, asec):
        # Allow weak password when all classes are off
        asec.check_password_complexity(
            "aaaaaaaa",
            require_upper=False,
            require_lower=False,
            require_digit=False,
        )

    def test_unicode_password_supported(self, asec):
        # Unicode chars count toward length
        asec.check_password_complexity("Pässw0rt!", require_upper=False)


# ==================== Account lockout ====================

class TestAccountLockout:
    def _make(self, asec, max_failures=3, lockout_sec=60):
        # Use a stub clock for deterministic time
        clock = [1000.0]
        lo = asec.AccountLockout(
            max_failures=max_failures,
            lockout_sec=lockout_sec,
            clock=lambda: clock[0],
        )
        return lo, clock

    def test_initially_not_locked(self, asec):
        lo, _ = self._make(asec)
        assert lo.is_locked("alice") is False
        assert lo.remaining_lockout_sec("alice") == 0

    def test_lockout_after_max_failures(self, asec):
        lo, _ = self._make(asec, max_failures=3, lockout_sec=60)
        for _ in range(3):
            lo.record_failure("alice")
        assert lo.is_locked("alice") is True
        assert lo.remaining_lockout_sec("alice") == 60

    def test_success_clears_state(self, asec):
        lo, _ = self._make(asec, max_failures=3)
        lo.record_failure("alice")
        lo.record_failure("alice")
        lo.record_success("alice")
        assert lo.is_locked("alice") is False
        # Can fail again without lockout immediately
        for _ in range(2):
            lo.record_failure("alice")
        assert lo.is_locked("alice") is False

    def test_lockout_expires(self, asec):
        lo, clock = self._make(asec, max_failures=2, lockout_sec=60)
        for _ in range(2):
            lo.record_failure("alice")
        assert lo.is_locked("alice")
        clock[0] += 61
        assert lo.is_locked("alice") is False

    def test_progressive_lockout_extends_duration(self, asec):
        lo, clock = self._make(asec, max_failures=2, lockout_sec=60)
        for _ in range(2):
            lo.record_failure("alice")
        assert lo.remaining_lockout_sec("alice") == 60
        # Wait for lockout to expire
        clock[0] += 61
        # Fail again
        for _ in range(2):
            lo.record_failure("alice")
        # Second lockout cycle should be longer (3600s)
        assert lo.remaining_lockout_sec("alice") == 3600

    def test_per_user_isolation(self, asec):
        lo, _ = self._make(asec, max_failures=2)
        for _ in range(2):
            lo.record_failure("alice")
        assert lo.is_locked("alice")
        assert not lo.is_locked("bob")

    def test_remaining_lockout_decreases(self, asec):
        lo, clock = self._make(asec, max_failures=2, lockout_sec=100)
        for _ in range(2):
            lo.record_failure("alice")
        assert lo.remaining_lockout_sec("alice") == 100
        clock[0] += 30
        assert lo.remaining_lockout_sec("alice") == 70

    def test_concurrent_access_thread_safe(self, asec):
        """Multiple threads incrementing failures should not corrupt state."""
        import threading
        lo = asec.AccountLockout(max_failures=100, lockout_sec=60)
        def fail():
            for _ in range(10):
                lo.record_failure("alice")
        threads = [threading.Thread(target=fail) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Should have exactly 50 failures recorded
        assert lo._store["acctlock:alice"]["failed_count"] == 50

    def test_custom_store(self, asec):
        """Verify the lockout state lives in the provided store."""
        store = {}
        lo = asec.AccountLockout(max_failures=2, store=store)
        lo.record_failure("alice")
        lo.record_failure("alice")
        assert "acctlock:alice" in store
        assert store["acctlock:alice"]["locked_until"] > 0

    def test_admin_reset(self, asec):
        lo, _ = self._make(asec, max_failures=2)
        for _ in range(2):
            lo.record_failure("alice")
        assert lo.is_locked("alice")
        lo.reset("alice")
        assert lo.is_locked("alice") is False


# ==================== Constant-time compare ====================

class TestConstantTimeCompare:
    def test_equal_strings(self, asec):
        assert asec.constant_time_compare("abc", "abc") is True

    def test_different_strings(self, asec):
        assert asec.constant_time_compare("abc", "abd") is False

    def test_different_lengths(self, asec):
        assert asec.constant_time_compare("abc", "abcd") is False

    def test_non_string_input(self, asec):
        assert asec.constant_time_compare(None, "x") is False
        assert asec.constant_time_compare("x", 123) is False
