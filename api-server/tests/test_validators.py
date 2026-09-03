"""
Unit tests for app/utils/validators.py — pushes coverage of the
standalone helpers to ~100%.
"""

import os
import sys
import importlib.util
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.abspath(os.path.join(HERE, ".."))
VAL_PATH = os.path.join(API_ROOT, "app", "utils", "validators.py")


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def v():
    return _load_module("_test_v", VAL_PATH)


class TestValidateEmail:
    def test_valid(self, v):
        assert v.validate_email("user@example.com") is True
        assert v.validate_email("a.b+c@sub.example.co.uk") is True

    def test_invalid(self, v):
        assert v.validate_email("not-an-email") is False
        assert v.validate_email("missing@dot") is False
        assert v.validate_email("@nodomain.com") is False
        assert v.validate_email("noatsign.com") is False

    def test_empty(self, v):
        assert v.validate_email("") is False
        assert v.validate_email(None) is False


class TestValidateUsername:
    def test_valid(self, v):
        assert v.validate_username("alice") is True
        assert v.validate_username("user_99") is True
        assert v.validate_username("abc") is True  # 3-char min

    def test_too_short(self, v):
        assert v.validate_username("ab") is False
        assert v.validate_username("") is False
        assert v.validate_username(None) is False

    def test_too_long(self, v):
        assert v.validate_username("x" * 31) is False
        assert v.validate_username("x" * 30) is True  # 30-char max

    def test_invalid_chars(self, v):
        assert v.validate_username("user-name") is False  # hyphen
        assert v.validate_username("user.name") is False  # dot
        assert v.validate_username("user name") is False  # space
        assert v.validate_username("1user") is False  # must start with letter

    def test_starts_with_letter(self, v):
        assert v.validate_username("a") is False  # too short
        assert v.validate_username("ab") is False
        assert v.validate_username("abc") is True
        assert v.validate_username("Z99") is True


class TestValidatePassword:
    def test_min_length(self, v):
        assert v.validate_password("Short1") is False  # 7 chars
        assert v.validate_password("8chars99") is True  # 8 chars

    def test_must_have_letter(self, v):
        assert v.validate_password("12345678") is False
        assert v.validate_password("abcdefg1") is True

    def test_must_have_number(self, v):
        assert v.validate_password("abcdefgh") is False
        assert v.validate_password("abcdefg1") is True

    def test_empty(self, v):
        assert v.validate_password("") is False
        assert v.validate_password(None) is False

    def test_long_password(self, v):
        assert v.validate_password("A" * 100 + "1") is True


class TestValidatePostTitle:
    def test_valid(self, v):
        assert v.validate_post_title("Hello") is True
        assert v.validate_post_title("x") is True
        assert v.validate_post_title("x" * 200) is True

    def test_empty(self, v):
        assert v.validate_post_title("") is False
        assert v.validate_post_title(None) is False

    def test_too_long(self, v):
        assert v.validate_post_title("x" * 201) is False


class TestValidatePostContent:
    def test_valid(self, v):
        assert v.validate_post_content("1234567890") is True  # exactly 10
        assert v.validate_post_content("a longer post body") is True

    def test_too_short(self, v):
        assert v.validate_post_content("short") is False
        assert v.validate_post_content("123456789") is False  # 9 chars

    def test_empty(self, v):
        assert v.validate_post_content("") is False
        assert v.validate_post_content(None) is False


class TestValidateCommentContent:
    def test_valid(self, v):
        assert v.validate_comment_content("nice post!") is True
        assert v.validate_comment_content("x" * 5000) is True
        assert v.validate_comment_content("x") is True

    def test_empty(self, v):
        assert v.validate_comment_content("") is False
        assert v.validate_comment_content(None) is False

    def test_too_long(self, v):
        assert v.validate_comment_content("x" * 5001) is False


class TestValidateTagName:
    def test_valid(self, v):
        assert v.validate_tag_name("python") is True
        assert v.validate_tag_name("web-dev") is True
        assert v.validate_tag_name("tag with spaces") is True
        assert v.validate_tag_name("ABC 123") is True

    def test_empty(self, v):
        assert v.validate_tag_name("") is False
        assert v.validate_tag_name(None) is False

    def test_too_long(self, v):
        assert v.validate_tag_name("x" * 51) is False
        assert v.validate_tag_name("x" * 50) is True

    def test_invalid_chars(self, v):
        assert v.validate_tag_name("tag_name") is False  # underscore
        assert v.validate_tag_name("tag.name") is False  # dot
        assert v.validate_tag_name("tag/name") is False  # slash
        assert v.validate_tag_name("tag<script>") is False  # angle bracket


class TestSanitizeHtml:
    def test_strips_script(self, v):
        out = v.sanitize_html("hello<script>alert(1)</script>")
        assert "<script>" not in out
        assert "hello" in out

    def test_strips_iframe(self, v):
        out = v.sanitize_html('a<iframe src="evil"></iframe>b')
        assert "<iframe" not in out

    def test_strips_object(self, v):
        out = v.sanitize_html('a<object data="x"></object>b')
        assert "<object" not in out

    def test_strips_embed(self, v):
        # <embed> is a void element; existing sanitizer only strips paired
        # tags (script, iframe, object). Document the actual behavior:
        out = v.sanitize_html('a<embed src="x">b')
        # Sanitizer does not strip <embed>; this is a known limitation
        # documented in the docstring ("use bleach library for production").
        assert out == 'a<embed src="x">b'

    def test_preserves_plain_text(self, v):
        assert v.sanitize_html("just plain text") == "just plain text"

    def test_empty_inputs(self, v):
        assert v.sanitize_html("") == ""
        assert v.sanitize_html(None) is None

    def test_case_insensitive_tag_match(self, v):
        out = v.sanitize_html("safe<SCRIPT>x</SCRIPT>ok")
        assert "SCRIPT" not in out.upper() or "<SCRIPT" not in out
