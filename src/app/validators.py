"""Reusable validation functions for all form fields."""

from __future__ import annotations

import re


def strip_and_clean(value: str | None) -> str:
    """Strip whitespace and normalize."""
    if value is None:
        return ""
    return " ".join(value.strip().split())


def validate_required_string(
    value: str | None, field_name: str, min_len: int = 1, max_len: int = 500
) -> tuple[bool, str | None]:
    """Validate a required string field with min/max length."""
    cleaned = strip_and_clean(value)
    if not cleaned:
        return False, f"{field_name} is required"
    if len(cleaned) < min_len:
        return False, f"{field_name} must be at least {min_len} characters"
    if len(cleaned) > max_len:
        return False, f"{field_name} must be at most {max_len} characters"
    return True, None


def validate_email(value: str | None) -> tuple[bool, str | None]:
    """Validate email format."""
    if not value or not value.strip():
        return False, "Email is required"
    email = value.strip().lower()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    if len(email) > 254:
        return False, "Email must be at most 254 characters"
    return True, None


def validate_password(value: str | None) -> tuple[bool, str | None]:
    """Validate password: 8-72 chars (bcrypt limit)."""
    if not value:
        return False, "Password is required"
    if len(value) < 8:
        return False, "Password must be at least 8 characters"
    if len(value) > 72:
        return False, "Password must be at most 72 characters"
    return True, None


def validate_full_name(value: str | None) -> tuple[bool, str | None]:
    """Validate full name: 2-100 chars, letters/spaces/hyphens/apostrophes."""
    cleaned = strip_and_clean(value)
    if not cleaned:
        return False, "Full name is required"
    if len(cleaned) < 2:
        return False, "Full name must be at least 2 characters"
    if len(cleaned) > 100:
        return False, "Full name must be at most 100 characters"
    if not re.match(r"^[a-zA-Z\s\-']+$", cleaned):
        return False, "Full name can only contain letters, spaces, hyphens, and apostrophes"
    return True, None


def validate_phone_au(value: str | None) -> tuple[bool, str | None]:
    """Validate Australian phone number: +61XXXXXXXXX or 0XXXXXXXXX."""
    if not value or not value.strip():
        return True, None  # phone is optional
    cleaned = re.sub(r'[\s\-\(\)]', '', value.strip())
    if cleaned.startswith('+61') and len(cleaned) == 12 and cleaned[3:].isdigit():
        return True, None
    if cleaned.startswith('0') and len(cleaned) == 10 and cleaned.isdigit():
        return True, None
    return False, "Phone must be Australian format: +61XXXXXXXXX or 0XXXXXXXXX"


def validate_abn(value: str | None) -> tuple[bool, str | None]:
    """Validate Australian Business Number with check digit algorithm."""
    if not value or not value.strip():
        return True, None  # ABN is optional
    cleaned = re.sub(r'[\s\-]', '', value.strip())
    if not cleaned.isdigit() or len(cleaned) != 11:
        return False, "ABN must be exactly 11 digits"
    # ABN check digit algorithm
    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    digits = [int(d) for d in cleaned]
    digits[0] -= 1  # subtract 1 from first digit
    weighted_sum = sum(d * w for d, w in zip(digits, weights))
    if weighted_sum % 89 != 0:
        return False, "Invalid ABN (check digit failed)"
    return True, None


def validate_org_name(value: str | None) -> tuple[bool, str | None]:
    """Validate organization name: 2-200 chars."""
    return validate_required_string(value, "Organization name", min_len=2, max_len=200)


def validate_industry(value: str | None) -> tuple[bool, str | None]:
    """Validate industry: 2-100 chars."""
    if not value or not value.strip():
        return True, None  # optional
    cleaned = strip_and_clean(value)
    if len(cleaned) < 2:
        return False, "Industry must be at least 2 characters"
    if len(cleaned) > 100:
        return False, "Industry must be at most 100 characters"
    return True, None


def validate_enum(value: str | None, field_name: str, valid_values: list[str]) -> tuple[bool, str | None]:
    """Validate that a value is one of the allowed enum values."""
    if not value:
        return False, f"{field_name} is required"
    if value not in valid_values:
        return False, f"{field_name} must be one of: {', '.join(valid_values)}"
    return True, None


def validate_positive_integer(
    value: str | int | None, field_name: str, allow_zero: bool = True
) -> tuple[bool, str | None]:
    """Validate a positive integer."""
    if value is None or value == "":
        return True, None  # optional
    try:
        n = int(value)
    except (ValueError, TypeError):
        return False, f"{field_name} must be a number"
    if n < 0:
        return False, f"{field_name} must be non-negative"
    if not allow_zero and n == 0:
        return False, f"{field_name} must be greater than 0"
    return True, None


def validate_pia_status_transition(current: str, new: str) -> tuple[bool, str | None]:
    """Validate PIA status transitions."""
    valid_transitions = {
        "draft": ["in_review"],
        "in_review": ["approved", "rejected"],
        "rejected": ["draft", "in_review"],
        "approved": [],
    }
    allowed = valid_transitions.get(current, [])
    if new not in allowed:
        return False, f"Cannot transition from '{current}' to '{new}'"
    return True, None
