"""
Phone number format conversion utilities for WhatsApp providers.
Handles conversion between WAHA, Twilio, and E.164 formats.
"""
import re
from typing import Tuple


def format_phone_for_twilio(phone: str) -> str:
    """
    Convert any phone format to Twilio WhatsApp format.

    Examples:
        "31612345678@c.us" → "whatsapp:+31612345678"
        "+31612345678" → "whatsapp:+31612345678"
        "31612345678" → "whatsapp:+31612345678"

    Args:
        phone: Phone number in any format

    Returns:
        Phone number in Twilio WhatsApp format (whatsapp:+E164)

    Raises:
        ValueError: If phone number is invalid
    """
    if not phone:
        raise ValueError("Phone number cannot be empty")

    # Remove @c.us suffix (WAHA format)
    phone = phone.replace("@c.us", "")

    # Remove existing whatsapp: prefix
    phone = phone.replace("whatsapp:", "")

    # Remove spaces and hyphens
    phone = phone.replace(" ", "").replace("-", "")

    # Ensure + prefix
    if not phone.startswith("+"):
        phone = f"+{phone}"

    # Validate E.164 format
    if not re.match(r'^\+[1-9]\d{9,14}$', phone):
        raise ValueError(f"Invalid phone number format: {phone}")

    # Add whatsapp: prefix
    return f"whatsapp:{phone}"


def format_phone_from_twilio(twilio_phone: str) -> str:
    """
    Convert Twilio format to E.164 standard for database.

    Example:
        "whatsapp:+31612345678" → "+31612345678"

    Args:
        twilio_phone: Phone number in Twilio format

    Returns:
        Phone number in E.164 format (+31612345678)
    """
    return twilio_phone.replace("whatsapp:", "")


def format_phone_to_waha(phone: str) -> str:
    """
    Convert E.164 format to WAHA format.
    (Used during migration period only - will be removed)

    Example:
        "+31612345678" → "31612345678@c.us"

    Args:
        phone: Phone number in E.164 format

    Returns:
        Phone number in WAHA format
    """
    # Remove + prefix
    phone = phone.replace("+", "")

    # Add @c.us suffix
    return f"{phone}@c.us"


def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """
    Validate phone number for WhatsApp.

    Args:
        phone: Phone number to validate

    Returns:
        Tuple of (is_valid, formatted_phone or error_message)

    Rules:
        - Must be E.164 format: +[country][number]
        - Length: 10-15 digits
        - Must start with +
        - No spaces or special chars (except + prefix)
    """
    try:
        formatted = format_phone_for_twilio(phone)
        return True, formatted
    except ValueError as e:
        return False, str(e)


def normalize_phone_to_e164(phone: str) -> str:
    """
    Normalize any phone format to E.164 for database storage.

    Examples:
        "whatsapp:+31612345678" → "+31612345678"
        "31612345678@c.us" → "+31612345678"
        "31612345678" → "+31612345678"

    Args:
        phone: Phone number in any format

    Returns:
        Phone number in E.164 format
    """
    # Remove provider prefixes
    phone = phone.replace("whatsapp:", "").replace("@c.us", "")

    # Remove spaces and hyphens
    phone = phone.replace(" ", "").replace("-", "")

    # Ensure + prefix
    if not phone.startswith("+"):
        phone = f"+{phone}"

    return phone
