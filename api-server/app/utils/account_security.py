"""
Account security helpers: lockout + password policy.

These utilities are intentionally framework-agnostic so they can be
unit-tested in isolation and plugged into any login handler. They do
NOT depend on the heavy app/__init__.py (prometheus, opentelemetry, etc).

The lockout is a small in-memory store (suitable for single-process
testing and as a reference implementation). For production, swap with
Redis-backed storage via the `store` parameter.
"""

import re
import time
import threading
from typing import Optional, Callable


# ---------- Password complexity policy ----------

class PasswordPolicyError(ValueError):
    """Raised when a password fails the policy."""


# Default policy: 8+ chars, 1 lower, 1 upper, 1 digit.
# Can be tuned per deployment via the env-driven settings.
DEFAULT_MIN_LENGTH = 8
DEFAULT_REQUIRE_UPPER = True
DEFAULT_REQUIRE_LOWER = True
DEFAULT_REQUIRE_DIGIT = True
DEFAULT_MAX_LENGTH = 128  # bcrypt truncates at 72; 128 is safe upper bound
DISALLOWED_SUBSTRINGS = ("password", "12345678", "qwerty", "letmein")


def check_password_complexity(
    password: str,
    min_length: int = DEFAULT_MIN_LENGTH,
    max_length: int = DEFAULT_MAX_LENGTH,
    require_upper: bool = DEFAULT_REQUIRE_UPPER,
    require_lower: bool = DEFAULT_REQUIRE_LOWER,
    require_digit: bool = DEFAULT_REQUIRE_DIGIT,
) -> None:
    """Validate password against policy. Raises PasswordPolicyError on failure.

    Policy:
      - length in [min_length, max_length]
      - if require_upper: at least one A-Z
      - if require_lower: at least one a-z
      - if require_digit: at least one 0-9
      - not in DISALLOWED_SUBSTRINGS (case-insensitive)
    """
    if not isinstance(password, str):
        raise PasswordPolicyError("password must be a string")
    if len(password) < min_length:
        raise PasswordPolicyError(
            f"password must be at least {min_length} characters"
        )
    if len(password) > max_length:
        raise PasswordPolicyError(
            f"password must be at most {max_length} characters"
        )
    if require_upper and not re.search(r"[A-Z]", password):
        raise PasswordPolicyError("password must contain an uppercase letter")
    if require_lower and not re.search(r"[a-z]", password):
        raise PasswordPolicyError("password must contain a lowercase letter")
    if require_digit and not re.search(r"\d", password):
        raise PasswordPolicyError("password must contain a digit")
    lower = password.lower()
    for bad in DISALLOWED_SUBSTRINGS:
        if bad in lower:
            raise PasswordPolicyError(
                "password contains a commonly-used weak substring"
            )


# ---------- Account lockout ----------

class AccountLockout:
    """In-memory account lockout with progressive delay.

    State per username:
      - failed_count: number of consecutive failures
      - locked_until: unix epoch when current lockout expires (0 = not locked)

    Threshold strategy:
      - After MAX_FAILURES failures, lock the account for LOCKOUT_DURATION_SEC
      - Each subsequent failure while locked resets the lockout window
      - A successful login clears all state

    For production: pass `store=` with a Redis-backed implementation
    that exposes the same .get/.set/.delete interface.
    """

    MAX_FAILURES = 5
    LOCKOUT_DURATION_SEC = 900       # 15 minutes initial
    LOCKOUT_DURATION_REPEAT = 3600   # 1 hour if user fails again after lockout expires
    PROGRESSIVE = True               # each lockout cycle extends the duration

    def __init__(self, max_failures: int = MAX_FAILURES,
                 lockout_sec: int = LOCKOUT_DURATION_SEC,
                 store: Optional[dict] = None,
                 clock: Callable[[], float] = time.time):
        self.max_failures = max_failures
        self.lockout_sec = lockout_sec
        self._store = store if store is not None else {}
        self._lock = threading.Lock()
        self._clock = clock

    def _key(self, username: str) -> str:
        return f"acctlock:{username}"

    def is_locked(self, username: str) -> bool:
        """True if the account is currently locked out."""
        with self._lock:
            entry = self._store.get(self._key(username))
            if not entry:
                return False
            return entry.get("locked_until", 0) > self._clock()

    def remaining_lockout_sec(self, username: str) -> int:
        """Seconds remaining in current lockout, or 0 if not locked."""
        with self._lock:
            entry = self._store.get(self._key(username))
            if not entry:
                return 0
            remaining = entry.get("locked_until", 0) - self._clock()
            return max(0, int(remaining))

    def record_failure(self, username: str) -> dict:
        """Record a failed login attempt.

        Returns a dict with the new state. If the threshold is reached,
        locks the account.
        """
        with self._lock:
            key = self._key(username)
            entry = self._store.get(key, {"failed_count": 0, "locked_until": 0, "lockouts": 0})
            entry["failed_count"] += 1

            if entry["failed_count"] >= self.max_failures:
                # Determine lockout duration
                if self.PROGRESSIVE and entry.get("lockouts", 0) > 0:
                    duration = self.LOCKOUT_DURATION_REPEAT
                else:
                    duration = self.lockout_sec
                entry["locked_until"] = self._clock() + duration
                entry["lockouts"] = entry.get("lockouts", 0) + 1
                entry["failed_count"] = 0  # reset for next round

            self._store[key] = entry
            return dict(entry)

    def record_success(self, username: str) -> None:
        """Clear all lockout state for a user on successful login."""
        with self._lock:
            self._store.pop(self._key(username), None)

    def reset(self, username: str) -> None:
        """Explicitly clear state (admin action)."""
        self.record_success(username)


# ---------- Constant-time helpers ----------

def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time."""
    import hmac
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
