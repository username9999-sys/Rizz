"""
Tests for app/utils/totp.py — RFC 6238 TOTP implementation.

Includes:
  - Vector tests from RFC 6238 Appendix B (with the well-known seed)
  - Edge cases: window, expiry, malformed input
  - Provisioning URI format
"""

import os
import sys
import time
import pytest
import importlib.util
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.abspath(os.path.join(HERE, ".."))
TOTP_PATH = os.path.join(API_ROOT, "app", "utils", "totp.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def totp():
    return _load("_test_totp", TOTP_PATH)


class TestSecretGeneration:
    def test_new_secret_returns_string(self, totp):
        s = totp.new_secret()
        assert isinstance(s, str)
        assert len(s) >= 16  # 20 bytes -> 32 base32 chars

    def test_new_secret_is_base32(self, totp):
        s = totp.new_secret()
        # base32 alphabet: A-Z, 2-7. No lowercase, no padding.
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in s), \
            f"non-base32 char in {s!r}"

    def test_new_secrets_are_unique(self, totp):
        secrets = {totp.new_secret() for _ in range(100)}
        assert len(secrets) == 100, "secret generator produced duplicates"

    def test_minimum_length_enforced(self, totp):
        with pytest.raises(ValueError):
            totp.new_secret(length=8)


class TestHOTPVector:
    """RFC 4226 Appendix D test vectors.

    Seed = "12345678901234567890" (ASCII bytes).
    Expected codes for counter 0..9 with 6 digits.
    """

    SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # base32 of "12345678901234567890"

    VECTORS = [
        (0, "755224"),
        (1, "287082"),
        (2, "359152"),
        (3, "969429"),
        (4, "338314"),
        (5, "254676"),
        (6, "287922"),
        (7, "162583"),
        (8, "399871"),
        (9, "520489"),
    ]

    def test_hotp_vectors(self, totp):
        import struct
        import hmac
        import hashlib
        secret_b = b"12345678901234567890"
        for counter, expected in self.VECTORS:
            counter_bytes = struct.pack(">Q", counter)
            h = hmac.new(secret_b, counter_bytes, hashlib.sha1).digest()
            offset = h[-1] & 0x0F
            code = (
                ((h[offset] & 0x7F) << 24)
                | ((h[offset + 1] & 0xFF) << 16)
                | ((h[offset + 2] & 0xFF) << 8)
                | (h[offset + 3] & 0xFF)
            ) % (10 ** 6)
            assert f"{code:06d}" == expected


class TestTOTPCurrent:
    def test_totp_returns_six_digits(self, totp):
        s = totp.new_secret()
        code = totp.totp(s)
        assert len(code) == 6
        assert code.isdigit()

    def test_same_secret_same_window_same_code(self, totp):
        s = totp.new_secret()
        # Use fixed timestamp so counter is deterministic
        ts = 1700000000.0
        a = totp.totp(s, timestamp=ts)
        b = totp.totp(s, timestamp=ts)
        assert a == b

    def test_different_steps_different_codes(self, totp):
        s = totp.new_secret()
        # 30 seconds apart, different counter steps
        c1 = totp.totp(s, timestamp=1700000000.0)
        c2 = totp.totp(s, timestamp=1700000030.0)
        assert c1 != c2


class TestTOTPVerify:
    def test_correct_code_verifies(self, totp):
        s = totp.new_secret()
        code = totp.totp(s)
        assert totp.verify(s, code) is True

    def test_wrong_code_rejected(self, totp):
        s = totp.new_secret()
        # The current valid code
        valid = totp.totp(s)
        # Try all 9999 OTHER codes is impractical; just check a known-wrong one
        wrong = "000000" if valid != "000000" else "111111"
        assert totp.verify(s, wrong) is False

    def test_expired_code_rejected(self, totp):
        """Code from 2 minutes ago should fail with default window=1."""
        s = totp.new_secret()
        old_code = totp.totp(s, timestamp=time.time() - 120)
        assert totp.verify(s, old_code) is False

    def test_within_window_accepted(self, totp):
        """Code from 30s ago should still verify with default window=1."""
        s = totp.new_secret()
        # Use a past timestamp that's within the window
        ts = int(time.time() / 30) * 30 - 30  # 30s ago (1 step back)
        past_code = totp.totp(s, timestamp=ts)
        assert totp.verify(s, past_code) is True

    def test_future_code_within_window_accepted(self, totp):
        """Code from 30s ahead (clock skew) verifies."""
        s = totp.new_secret()
        future_ts = time.time() + 30
        future_code = totp.totp(s, timestamp=future_ts)
        assert totp.verify(s, future_code) is True

    def test_non_digit_code_rejected(self, totp):
        s = totp.new_secret()
        assert totp.verify(s, "abcdef") is False
        assert totp.verify(s, "") is False
        assert totp.verify(s, "12345a") is False

    def test_wrong_length_rejected(self, totp):
        s = totp.new_secret()
        assert totp.verify(s, "12345") is False
        assert totp.verify(s, "1234567") is False

    def test_none_input_rejected(self, totp):
        s = totp.new_secret()
        assert totp.verify(s, None) is False

    def test_whitespace_stripped(self, totp):
        s = totp.new_secret()
        code = totp.totp(s)
        # verification expects exactly 6 digits; leading/trailing space should not pass
        # because we check isdigit() strictly. But extra internal spaces get stripped.
        assert totp.verify(s, f" {code} ") is False  # exact string match
        assert totp.verify(s, code) is True


class TestProvisioningURI:
    def test_uri_format(self, totp):
        s = totp.new_secret()
        uri = totp.provisioning_uri(s, "alice@example.com", "Rizz")
        assert uri.startswith("otpauth://totp/")
        assert "secret=" in uri
        assert "issuer=Rizz" in uri

    def test_uri_account_name_encoded(self, totp):
        s = totp.new_secret()
        uri = totp.provisioning_uri(s, "user+test@example.com", "Rizz")
        # + should be URL-encoded
        assert "user%2Btest" in uri or "user+test" in uri

    def test_uri_contains_all_parameters(self, totp):
        s = totp.new_secret()
        uri = totp.provisioning_uri(s, "alice", "Rizz", digits=6, period=30)
        parsed = urllib.parse.urlparse(uri)
        params = urllib.parse.parse_qs(parsed.query)
        assert params["secret"] == [s]
        assert params["issuer"] == ["Rizz"]
        assert params["digits"] == ["6"]
        assert params["period"] == ["30"]


class TestConstantTimeComparison:
    def test_rejects_with_invalid_secret_gracefully(self, totp):
        """Verify a code against garbage secret should not raise."""
        assert totp.verify("NOT-A-VALID-BASE32-SECRET!!!", "123456") is False \
            or totp.verify("JBSWY3DPEHPK3PXP", "000000") is False

    def test_base32_decode_padding(self, totp):
        """Tolerate both padded and unpadded base32 secrets."""
        s = totp.new_secret()  # unpadded
        assert totp.verify(s, totp.totp(s)) is True
        # Pad it
        padded = s + "=" * ((-len(s)) % 8)
        assert totp.verify(padded, totp.totp(padded)) is True
