"""Tests for field validators."""

from src.app.validators import (
    validate_email, validate_password, validate_full_name,
    validate_phone_au, validate_abn, validate_org_name,
    validate_industry, validate_enum, validate_positive_integer,
    validate_pia_status_transition, validate_required_string,
    strip_and_clean,
)


class TestEmail:
    def test_valid(self):
        assert validate_email("test@example.com") == (True, None)

    def test_invalid(self):
        ok, err = validate_email("notanemail")
        assert not ok

    def test_empty(self):
        ok, err = validate_email("")
        assert not ok

    def test_none(self):
        ok, err = validate_email(None)
        assert not ok


class TestPassword:
    def test_valid(self):
        assert validate_password("securepass123") == (True, None)

    def test_too_short(self):
        ok, _ = validate_password("short")
        assert not ok

    def test_too_long(self):
        ok, _ = validate_password("a" * 73)
        assert not ok

    def test_empty(self):
        ok, _ = validate_password("")
        assert not ok


class TestFullName:
    def test_valid(self):
        assert validate_full_name("John Smith") == (True, None)

    def test_hyphenated(self):
        assert validate_full_name("Mary-Jane O'Brien") == (True, None)

    def test_too_short(self):
        ok, _ = validate_full_name("A")
        assert not ok

    def test_special_chars(self):
        ok, _ = validate_full_name("Test123!")
        assert not ok

    def test_empty(self):
        ok, _ = validate_full_name("")
        assert not ok


class TestPhoneAU:
    def test_mobile_plus61(self):
        assert validate_phone_au("+61412345678") == (True, None)

    def test_mobile_zero(self):
        assert validate_phone_au("0412345678") == (True, None)

    def test_landline(self):
        assert validate_phone_au("0893001234") == (True, None)

    def test_with_spaces(self):
        assert validate_phone_au("+61 412 345 678") == (True, None)

    def test_with_dashes(self):
        assert validate_phone_au("0412-345-678") == (True, None)

    def test_empty_optional(self):
        assert validate_phone_au("") == (True, None)

    def test_none_optional(self):
        assert validate_phone_au(None) == (True, None)

    def test_invalid_garbage(self):
        ok, err = validate_phone_au("aaaaaaa")
        assert not ok
        assert "Australian format" in err

    def test_invalid_too_short(self):
        ok, _ = validate_phone_au("04123")
        assert not ok

    def test_invalid_us_number(self):
        ok, _ = validate_phone_au("+15551234567")
        assert not ok


class TestABN:
    def test_valid_abn(self):
        # 51 824 753 556 is a known valid ABN
        assert validate_abn("51824753556") == (True, None)

    def test_valid_with_spaces(self):
        assert validate_abn("51 824 753 556") == (True, None)

    def test_invalid_check_digit(self):
        ok, err = validate_abn("12345678901")
        assert not ok
        assert "check digit" in err

    def test_too_short(self):
        ok, _ = validate_abn("1234")
        assert not ok

    def test_not_digits(self):
        ok, _ = validate_abn("abcdefghijk")
        assert not ok

    def test_empty_optional(self):
        assert validate_abn("") == (True, None)

    def test_none_optional(self):
        assert validate_abn(None) == (True, None)


class TestEnum:
    def test_valid(self):
        assert validate_enum("low", "Severity", ["low", "medium", "high"]) == (True, None)

    def test_invalid(self):
        ok, err = validate_enum("extreme", "Severity", ["low", "medium", "high"])
        assert not ok

    def test_empty(self):
        ok, _ = validate_enum("", "Severity", ["low", "medium", "high"])
        assert not ok


class TestPositiveInteger:
    def test_valid(self):
        assert validate_positive_integer(5, "Count") == (True, None)

    def test_zero_allowed(self):
        assert validate_positive_integer(0, "Count", allow_zero=True) == (True, None)

    def test_zero_not_allowed(self):
        ok, _ = validate_positive_integer(0, "Count", allow_zero=False)
        assert not ok

    def test_negative(self):
        ok, _ = validate_positive_integer(-1, "Count")
        assert not ok

    def test_string_number(self):
        assert validate_positive_integer("10", "Count") == (True, None)

    def test_not_a_number(self):
        ok, _ = validate_positive_integer("abc", "Count")
        assert not ok

    def test_empty_optional(self):
        assert validate_positive_integer(None, "Count") == (True, None)


class TestPIATransition:
    def test_draft_to_review(self):
        assert validate_pia_status_transition("draft", "in_review") == (True, None)

    def test_review_to_approved(self):
        assert validate_pia_status_transition("in_review", "approved") == (True, None)

    def test_review_to_rejected(self):
        assert validate_pia_status_transition("in_review", "rejected") == (True, None)

    def test_rejected_to_draft(self):
        assert validate_pia_status_transition("rejected", "draft") == (True, None)

    def test_invalid_draft_to_approved(self):
        ok, _ = validate_pia_status_transition("draft", "approved")
        assert not ok

    def test_invalid_approved_to_anything(self):
        ok, _ = validate_pia_status_transition("approved", "draft")
        assert not ok


class TestRequiredString:
    def test_valid(self):
        assert validate_required_string("hello", "Field") == (True, None)

    def test_empty(self):
        ok, _ = validate_required_string("", "Field")
        assert not ok

    def test_too_short(self):
        ok, _ = validate_required_string("a", "Field", min_len=3)
        assert not ok

    def test_too_long(self):
        ok, _ = validate_required_string("a" * 501, "Field", max_len=500)
        assert not ok


class TestStripAndClean:
    def test_strips_whitespace(self):
        assert strip_and_clean("  hello  ") == "hello"

    def test_collapses_spaces(self):
        assert strip_and_clean("hello   world") == "hello world"

    def test_none(self):
        assert strip_and_clean(None) == ""
