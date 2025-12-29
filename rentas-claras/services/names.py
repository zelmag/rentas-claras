"""
Name Processing Services
========================

Utilities for processing Mexican Spanish names.
Handles abbreviations, compound names, and display name extraction.

This is culturally-aware name processing for:
- Common Mexican name abbreviations (J → Juan, Ma → María, etc.)
- Compound first names (Juan Carlos, María Elena, etc.)
- Multiple tenant names (Samantha y Cecilia → Samantha)
"""

import re
from typing import Optional, Set


# =============================================================================
# CONSTANTS
# =============================================================================

# Common name abbreviations in Mexican Spanish
NAME_ABBREVIATIONS: dict[str, str] = {
    "J": "Juan",
    "Ma": "María",
    "Ma.": "María",
    "Mª": "María",
    "Fco": "Francisco",
    "Fco.": "Francisco",
    "Gpe": "Guadalupe",
    "Gpe.": "Guadalupe",
    "Jse": "José",
    "Jse.": "José",
}

# Common second parts of compound first names in Mexican culture
COMPOUND_SECOND_NAMES: Set[str] = {
    "Carlos",
    "María",
    "Luis",
    "José",
    "Antonio",
    "Francisco",
    "Elena",
    "Isabel",
    "Teresa",
    "Carmen",
    "Cristina",
    "Fernanda",
    "Alejandro",
    "Manuel",
    "Miguel",
    "Angel",
    "Guadalupe",
    "Vanessa",
}

# Well-known compound first names that should always be preserved as-is
COMPOUND_FIRST_NAMES: Set[str] = {
    "Juan Carlos",
    "José Luis",
    "María Elena",
    "Ana María",
    "María José",
    "Luis Miguel",
    "María Fernanda",
    "María Guadalupe",
    "José Antonio",
    "María Isabel",
    "Juan Manuel",
    "José María",
    "Ana Sofía",
    "Guadalupe Vanessa",
}


# =============================================================================
# PHONE VALIDATION (DEPRECATED - Use services/validation.py instead)
# =============================================================================
# NOTE: These functions are kept for backward compatibility but new code
# should use validate_phone() from services/validation.py


def validate_phone_number(phone: str) -> tuple[bool, Optional[str]]:
    """
    Validate a phone number for WhatsApp messaging.
    
    DEPRECATED: Use validate_phone() from services/validation.py instead.
    This function is kept for backward compatibility.

    Args:
        phone: Phone number string

    Returns:
        Tuple of (is_valid, error_message)
    """
    from services.validation import validate_phone
    return validate_phone(phone, required=True)


# =============================================================================
# FUNCTIONS
# =============================================================================


def expand_abbreviated_name(name: str) -> str:
    """
    Expand common Mexican name abbreviations.

    Examples:
        "J Carlos" -> "Juan Carlos"
        "Ma Elena" -> "María Elena"
        "Gpe Vanessa" -> "Guadalupe Vanessa"

    Args:
        name: Name string that may contain abbreviations

    Returns:
        Expanded name string
    """
    parts = name.split()
    if not parts:
        return name

    first_part = parts[0]

    # Check if first part is an abbreviation
    if first_part in NAME_ABBREVIATIONS:
        expanded = NAME_ABBREVIATIONS[first_part]
        if len(parts) > 1:
            return f"{expanded} {parts[1]}"
        return expanded

    # If first part is a single letter followed by more name parts
    if len(first_part) == 1 and len(parts) > 1:
        if first_part.upper() in NAME_ABBREVIATIONS:
            return f"{NAME_ABBREVIATIONS[first_part.upper()]} {parts[1]}"

    # Check if the full name is a well-known compound first name
    if len(parts) >= 2:
        potential_compound = f"{parts[0]} {parts[1]}"
        if potential_compound in COMPOUND_FIRST_NAMES:
            return potential_compound

    # Check if we have a compound first name
    if len(parts) == 2 and parts[1] in COMPOUND_SECOND_NAMES:
        return f"{parts[0]} {parts[1]}"

    return parts[0]


def extract_display_name(full_name: str) -> str:
    """
    Extract the display name for greeting a tenant.

    Handles:
    - Simple names: "María González" -> "María"
    - Abbreviated names: "J Carlos y Raul" -> "Juan Carlos"
    - Compound names: "Gpe Vanessa" -> "Guadalupe Vanessa"
    - Multiple tenants: "Samantha Y Cecilia" -> "Samantha"

    Args:
        full_name: Full tenant name from database

    Returns:
        Display name suitable for greeting (e.g., "Buenos días {name}")
    """
    if not full_name:
        return "Inquilino"

    name_lower = full_name.lower()

    # Handle multiple tenants (separated by " y " or " Y ")
    if " y " in name_lower:
        # Split and get first person's name
        first_person = full_name.split(" y ")[0].split(" Y ")[0].strip()
        return expand_abbreviated_name(first_person)

    return expand_abbreviated_name(full_name)
