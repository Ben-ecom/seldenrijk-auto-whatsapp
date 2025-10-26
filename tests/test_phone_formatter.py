"""
Unit tests for phone number format conversion utilities.
"""
import pytest
from app.utils.phone_formatter import (
    format_phone_for_twilio,
    format_phone_from_twilio,
    format_phone_to_waha,
    validate_phone_number,
    normalize_phone_to_e164
)


def test_format_phone_for_twilio_waha():
    """Test WAHA format conversion"""
    assert format_phone_for_twilio("31612345678@c.us") == "whatsapp:+31612345678"


def test_format_phone_for_twilio_e164():
    """Test E.164 format conversion"""
    assert format_phone_for_twilio("+31612345678") == "whatsapp:+31612345678"


def test_format_phone_for_twilio_no_plus():
    """Test number without + prefix"""
    assert format_phone_for_twilio("31612345678") == "whatsapp:+31612345678"


def test_format_phone_for_twilio_with_spaces():
    """Test number with spaces"""
    assert format_phone_for_twilio("+31 6 12 34 56 78") == "whatsapp:+31612345678"


def test_format_phone_for_twilio_with_hyphens():
    """Test number with hyphens"""
    assert format_phone_for_twilio("+31-6-12-34-56-78") == "whatsapp:+31612345678"


def test_format_phone_for_twilio_invalid_empty():
    """Test empty phone number"""
    with pytest.raises(ValueError, match="cannot be empty"):
        format_phone_for_twilio("")


def test_format_phone_for_twilio_invalid_format():
    """Test invalid phone format"""
    with pytest.raises(ValueError, match="Invalid phone number format"):
        format_phone_for_twilio("invalid")


def test_format_phone_for_twilio_too_short():
    """Test phone number too short"""
    with pytest.raises(ValueError, match="Invalid phone number format"):
        format_phone_for_twilio("+31612")


def test_format_phone_from_twilio():
    """Test Twilio to E.164 conversion"""
    assert format_phone_from_twilio("whatsapp:+31612345678") == "+31612345678"


def test_format_phone_from_twilio_already_e164():
    """Test already E.164 format"""
    assert format_phone_from_twilio("+31612345678") == "+31612345678"


def test_format_phone_to_waha():
    """Test E.164 to WAHA conversion"""
    assert format_phone_to_waha("+31612345678") == "31612345678@c.us"


def test_format_phone_to_waha_no_plus():
    """Test WAHA conversion without + prefix"""
    assert format_phone_to_waha("31612345678") == "31612345678@c.us"


def test_validate_phone_number_valid():
    """Test valid phone number"""
    is_valid, result = validate_phone_number("+31612345678")
    assert is_valid is True
    assert result == "whatsapp:+31612345678"


def test_validate_phone_number_valid_waha():
    """Test valid WAHA format"""
    is_valid, result = validate_phone_number("31612345678@c.us")
    assert is_valid is True
    assert result == "whatsapp:+31612345678"


def test_validate_phone_number_invalid():
    """Test invalid phone number"""
    is_valid, result = validate_phone_number("invalid")
    assert is_valid is False
    assert "Invalid" in result


def test_validate_phone_number_empty():
    """Test empty phone number"""
    is_valid, result = validate_phone_number("")
    assert is_valid is False
    assert "cannot be empty" in result


def test_normalize_phone_to_e164_twilio():
    """Test Twilio format normalization"""
    assert normalize_phone_to_e164("whatsapp:+31612345678") == "+31612345678"


def test_normalize_phone_to_e164_waha():
    """Test WAHA format normalization"""
    assert normalize_phone_to_e164("31612345678@c.us") == "+31612345678"


def test_normalize_phone_to_e164_plain():
    """Test plain number normalization"""
    assert normalize_phone_to_e164("31612345678") == "+31612345678"


def test_normalize_phone_to_e164_with_spaces():
    """Test normalization with spaces"""
    assert normalize_phone_to_e164("+31 6 12 34 56 78") == "+31612345678"


def test_normalize_phone_to_e164_with_hyphens():
    """Test normalization with hyphens"""
    assert normalize_phone_to_e164("+31-6-12-34-56-78") == "+31612345678"


def test_international_numbers():
    """Test various international number formats"""
    # US number
    assert format_phone_for_twilio("+14155551234") == "whatsapp:+14155551234"

    # UK number
    assert format_phone_for_twilio("+447911123456") == "whatsapp:+447911123456"

    # German number
    assert format_phone_for_twilio("+4915123456789") == "whatsapp:+4915123456789"
