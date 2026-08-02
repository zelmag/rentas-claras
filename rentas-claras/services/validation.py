"""
Input Validation Services
==========================

Centralized validation for API inputs to prevent security issues.
"""

import logging
import re
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Valid ranges for date fields
MIN_VALID_YEAR = 2020
MAX_VALID_YEAR = 2100
MIN_VALID_MONTH = 1
MAX_VALID_MONTH = 12

# Phone number regex (Mexican format with optional country code)
PHONE_REGEX = re.compile(r"^\+?[0-9\s\-]{10,15}$")

# Tenant ID format (e.g., MAT-A, HUI-B2)
TENANT_ID_REGEX = re.compile(r"^[A-Z]{2,5}-[A-Za-z0-9]{1,5}$")

# Safe column names for dynamic SQL (whitelist)
TENANT_SAFE_COLUMNS = frozenset(
    {
        "name",
        "phone",
        "property_name",
        "unit",
        "rent",
        "emergency_contact",
        "emergency_phone",
        "contract_start",
        "contract_end",
        "bank",
        "active",
        "renewal_status",
        "contract_delivered",
        "contract_picked_up",
        "leaving_date",
        "replacement_name",
        "replacement_phone",
        "replacement_contract_start",
        "replacement_contract_end",
        "replacement_aval_name",
        "replacement_aval_phone",
        "aval_name",
        "aval_phone",
        "prorated_first_month",
        "prorated_amount",
        "prorated_month",
        "prorated_year",
        "deposit_amount",
        "deposit_paid",
        "deposit_paid_date",
        "deposit_returned",
        "deposit_returned_date",
        "deposit_returned_notes",
        "updated_at",
    }
)

MONTHLY_RECORD_SAFE_COLUMNS = frozenset(
    {
        "paid",
        "payment_method",
        "amount_paid",
        "notes",
        "payment_date",
        "visits",
        "visit_charge",
        "updated_at",
    }
)


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_tenant_id(tenant_id: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate tenant ID format.

    Args:
        tenant_id: The tenant ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if tenant_id is None:
        return False, "tenant_id is required"

    if not isinstance(tenant_id, str):
        return False, "tenant_id must be a string"

    tenant_id = tenant_id.strip()
    if not tenant_id:
        return False, "tenant_id cannot be empty"

    if len(tenant_id) > 20:
        return False, "tenant_id is too long (max 20 characters)"

    # Allow flexible format since IDs are system-generated from property
    # name/unit, which may include accented letters (e.g. "Álamos") or
    # spaces (e.g. unit "Local 1"). \w is Unicode-aware in Python 3, so
    # this already covers accented letters.
    if not re.match(r"^[\w\s-]+$", tenant_id, re.UNICODE):
        return False, "tenant_id contains invalid characters"

    return True, None


def validate_year(year: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate year is within acceptable range.

    Args:
        year: The year to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if year is None:
        return False, "year is required"

    if not isinstance(year, int):
        try:
            year = int(year)
        except (ValueError, TypeError):
            return False, "year must be an integer"

    if year < MIN_VALID_YEAR or year > MAX_VALID_YEAR:
        return False, f"year must be between {MIN_VALID_YEAR} and {MAX_VALID_YEAR}"

    return True, None


def validate_month(month: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate month is 1-12.

    Args:
        month: The month to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if month is None:
        return False, "month is required"

    if not isinstance(month, int):
        try:
            month = int(month)
        except (ValueError, TypeError):
            return False, "month must be an integer"

    if month < MIN_VALID_MONTH or month > MAX_VALID_MONTH:
        return False, f"month must be between {MIN_VALID_MONTH} and {MAX_VALID_MONTH}"

    return True, None


def validate_phone(phone: Any, required: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validate phone number format.

    Args:
        phone: The phone number to validate
        required: Whether the phone is required

    Returns:
        Tuple of (is_valid, error_message)
    """
    if phone is None or phone == "":
        if required:
            return False, "phone is required"
        return True, None

    if not isinstance(phone, str):
        return False, "phone must be a string"

    # Clean the phone for validation
    cleaned = phone.replace(" ", "").replace("-", "")

    # Check length (10-15 digits)
    digits_only = re.sub(r"\D", "", cleaned)
    if len(digits_only) < 10 or len(digits_only) > 15:
        return False, "phone must have 10-15 digits"

    return True, None


def validate_rent(rent: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate rent amount.

    Args:
        rent: The rent amount to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if rent is None:
        return False, "rent is required"

    try:
        rent_float = float(rent)
    except (ValueError, TypeError):
        return False, "rent must be a number"

    if rent_float < 0:
        return False, "rent cannot be negative"

    if rent_float > 1000000:
        return False, "rent value seems too high (max 1,000,000)"

    return True, None


def validate_payment_method(method: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate payment method.

    Args:
        method: The payment method to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if method is None:
        return True, None  # Optional field

    if not isinstance(method, str):
        return False, "payment_method must be a string"

    if len(method) > 100:
        return False, "payment_method is too long (max 100 characters)"

    return True, None


def validate_renewal_status(status: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate renewal status value.

    Args:
        status: The renewal status to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if status is None:
        return True, None  # Optional field

    valid_statuses = {"renovará", "no_renovará", "pendiente"}

    if not isinstance(status, str):
        return False, "renewal_status must be a string"

    if status not in valid_statuses:
        return False, f"renewal_status must be one of: {', '.join(valid_statuses)}"

    return True, None


def validate_date_string(
    date_str: Any, field_name: str = "date"
) -> Tuple[bool, Optional[str]]:
    """
    Validate date string format (YYYY-MM-DD or DD/MM/YYYY).

    Args:
        date_str: The date string to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if date_str is None or date_str == "":
        return True, None  # Optional field

    if not isinstance(date_str, str):
        return False, f"{field_name} must be a string"

    # Try ISO format (YYYY-MM-DD)
    iso_pattern = r"^\d{4}-\d{2}-\d{2}$"
    # Try European format (DD/MM/YYYY)
    euro_pattern = r"^\d{2}/\d{2}/\d{4}$"

    if not (re.match(iso_pattern, date_str) or re.match(euro_pattern, date_str)):
        return False, f"{field_name} must be in YYYY-MM-DD or DD/MM/YYYY format"

    return True, None


def validate_boolean(
    value: Any, field_name: str = "value"
) -> Tuple[bool, Optional[str]]:
    """
    Validate and convert boolean value.

    Args:
        value: The value to validate as boolean
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return True, None

    if isinstance(value, bool):
        return True, None

    if isinstance(value, (int, float)):
        if value in (0, 1, 0.0, 1.0):
            return True, None

    if isinstance(value, str):
        if value.lower() in ("true", "false", "1", "0", "yes", "no"):
            return True, None

    return False, f"{field_name} must be a boolean value"


def validate_column_name(
    column: str, allowed_columns: frozenset
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a column name is in the whitelist (SQL injection prevention).

    Args:
        column: The column name to validate
        allowed_columns: Set of allowed column names

    Returns:
        Tuple of (is_valid, error_message)
    """
    if column not in allowed_columns:
        logger.warning(f"Attempted to use invalid column name: {column}")
        return False, f"Invalid column name: {column}"

    return True, None


def sanitize_string(value: Any, max_length: int = 500) -> Optional[str]:
    """
    Sanitize a string value.

    Args:
        value: The value to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string or None
    """
    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    # Strip whitespace
    value = value.strip()

    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]

    return value if value else None


# =============================================================================
# COMPOSITE VALIDATORS (for API endpoints)
# =============================================================================


def validate_payment_update(data: dict) -> Tuple[bool, Optional[str], dict]:
    """
    Validate payment update request data.

    Args:
        data: Request JSON data

    Returns:
        Tuple of (is_valid, error_message, validated_data)
    """
    errors = []
    validated = {}

    # Required: tenant_id
    is_valid, error = validate_tenant_id(data.get("tenant_id"))
    if not is_valid:
        errors.append(error)
    else:
        validated["tenant_id"] = data.get("tenant_id").strip()

    # Optional: year (default to current)
    from datetime import datetime

    year = data.get("year", datetime.now().year)
    is_valid, error = validate_year(year)
    if not is_valid:
        errors.append(error)
    else:
        validated["year"] = int(year)

    # Optional: month (default to current)
    month = data.get("month", datetime.now().month)
    is_valid, error = validate_month(month)
    if not is_valid:
        errors.append(error)
    else:
        validated["month"] = int(month)

    # Optional: paid (boolean)
    is_valid, error = validate_boolean(data.get("paid"), "paid")
    if not is_valid:
        errors.append(error)
    else:
        validated["paid"] = bool(data.get("paid", False))

    # Optional: payment_method
    is_valid, error = validate_payment_method(data.get("payment_method"))
    if not is_valid:
        errors.append(error)
    else:
        validated["payment_method"] = sanitize_string(data.get("payment_method"))

    # Optional: visits (integer >= 0)
    visits = data.get("visits", 0)
    if visits is not None:
        try:
            visits = int(visits)
            if visits < 0 or visits > 100:
                errors.append("visits must be between 0 and 100")
            else:
                validated["visits"] = visits
        except (ValueError, TypeError):
            errors.append("visits must be an integer")
    else:
        validated["visits"] = 0

    # Optional: visit_charge (float >= 0)
    visit_charge = data.get("visit_charge", 0.0)
    if visit_charge is not None:
        try:
            visit_charge = float(visit_charge)
            if visit_charge < 0 or visit_charge > 100000:
                errors.append("visit_charge must be between 0 and 100000")
            else:
                validated["visit_charge"] = visit_charge
        except (ValueError, TypeError):
            errors.append("visit_charge must be a number")
    else:
        validated["visit_charge"] = 0.0

    if errors:
        return False, "; ".join(errors), {}

    return True, None, validated


def validate_tenant_create(data: dict) -> Tuple[bool, Optional[str], dict]:
    """
    Validate tenant creation request data.

    Args:
        data: Request JSON data

    Returns:
        Tuple of (is_valid, error_message, validated_data)
    """
    errors = []
    validated = {}

    # Required: name
    name = data.get("name", "").strip() if data.get("name") else ""
    if not name:
        errors.append("name is required")
    elif len(name) > 200:
        errors.append("name is too long (max 200 characters)")
    else:
        validated["name"] = name

    # Required: property_name
    property_name = (
        data.get("property_name", "").strip() if data.get("property_name") else ""
    )
    if not property_name:
        errors.append("property_name is required")
    elif len(property_name) > 100:
        errors.append("property_name is too long (max 100 characters)")
    else:
        validated["property_name"] = property_name

    # Required: unit
    unit = data.get("unit", "").strip() if data.get("unit") else ""
    if not unit:
        errors.append("unit is required")
    elif len(unit) > 20:
        errors.append("unit is too long (max 20 characters)")
    else:
        validated["unit"] = unit

    # Required: rent
    is_valid, error = validate_rent(data.get("rent"))
    if not is_valid:
        errors.append(error)
    else:
        validated["rent"] = float(data.get("rent"))

    # Optional: phone
    is_valid, error = validate_phone(data.get("phone"))
    if not is_valid:
        errors.append(error)
    else:
        validated["phone"] = sanitize_string(data.get("phone", ""))

    # Optional: contract dates
    is_valid, error = validate_date_string(data.get("contract_start"), "contract_start")
    if not is_valid:
        errors.append(error)
    else:
        validated["contract_start"] = data.get("contract_start")

    is_valid, error = validate_date_string(data.get("contract_end"), "contract_end")
    if not is_valid:
        errors.append(error)
    else:
        validated["contract_end"] = data.get("contract_end")

    # Optional: other fields
    validated["emergency_contact"] = sanitize_string(data.get("emergency_contact"))
    validated["emergency_phone"] = sanitize_string(data.get("emergency_phone"))
    validated["bank"] = sanitize_string(data.get("bank"), max_length=50)
    validated["aval_name"] = sanitize_string(data.get("aval_name"))
    validated["aval_phone"] = sanitize_string(data.get("aval_phone"))

    # Proration fields
    validated["prorated_first_month"] = bool(data.get("prorated_first_month", False))
    if data.get("prorated_amount") is not None:
        try:
            validated["prorated_amount"] = float(data.get("prorated_amount"))
        except (ValueError, TypeError):
            errors.append("prorated_amount must be a number")
    else:
        validated["prorated_amount"] = None

    if data.get("prorated_month") is not None:
        is_valid, error = validate_month(data.get("prorated_month"))
        if not is_valid:
            errors.append(f"prorated_month: {error}")
        else:
            validated["prorated_month"] = int(data.get("prorated_month"))
    else:
        validated["prorated_month"] = None

    if data.get("prorated_year") is not None:
        is_valid, error = validate_year(data.get("prorated_year"))
        if not is_valid:
            errors.append(f"prorated_year: {error}")
        else:
            validated["prorated_year"] = int(data.get("prorated_year"))
    else:
        validated["prorated_year"] = None

    if errors:
        return False, "; ".join(errors), {}

    return True, None, validated


def validate_deposit_update(data: dict) -> Tuple[bool, Optional[str], dict]:
    """
    Validate deposit update request data.

    Args:
        data: Request JSON data

    Returns:
        Tuple of (is_valid, error_message, validated_data)
    """
    errors = []
    validated = {}

    # Required: tenant_id
    is_valid, error = validate_tenant_id(data.get("tenant_id"))
    if not is_valid:
        errors.append(error)
    else:
        validated["tenant_id"] = data.get("tenant_id").strip()

    # Optional: deposit_amount
    if data.get("deposit_amount") is not None:
        try:
            amount = float(data.get("deposit_amount"))
            if amount < 0 or amount > 1000000:
                errors.append("deposit_amount must be between 0 and 1,000,000")
            else:
                validated["deposit_amount"] = amount
        except (ValueError, TypeError):
            errors.append("deposit_amount must be a number")
    else:
        validated["deposit_amount"] = None

    # Optional: deposit_paid (boolean)
    is_valid, error = validate_boolean(data.get("deposit_paid"), "deposit_paid")
    if not is_valid:
        errors.append(error)
    else:
        validated["deposit_paid"] = data.get("deposit_paid")

    # Optional: deposit_paid_date
    is_valid, error = validate_date_string(
        data.get("deposit_paid_date"), "deposit_paid_date"
    )
    if not is_valid:
        errors.append(error)
    else:
        validated["deposit_paid_date"] = data.get("deposit_paid_date")

    # Optional: deposit_returned (boolean)
    is_valid, error = validate_boolean(data.get("deposit_returned"), "deposit_returned")
    if not is_valid:
        errors.append(error)
    else:
        validated["deposit_returned"] = data.get("deposit_returned")

    # Optional: deposit_returned_date
    is_valid, error = validate_date_string(
        data.get("deposit_returned_date"), "deposit_returned_date"
    )
    if not is_valid:
        errors.append(error)
    else:
        validated["deposit_returned_date"] = data.get("deposit_returned_date")

    # Optional: deposit_returned_notes
    validated["deposit_returned_notes"] = sanitize_string(
        data.get("deposit_returned_notes"), max_length=500
    )

    if errors:
        return False, "; ".join(errors), {}

    return True, None, validated


def validate_renewal_update(data: dict) -> Tuple[bool, Optional[str], dict]:
    """
    Validate renewal status update request data.

    Args:
        data: Request JSON data

    Returns:
        Tuple of (is_valid, error_message, validated_data)
    """
    errors = []
    validated = {}

    # Required: tenant_id
    is_valid, error = validate_tenant_id(data.get("tenant_id"))
    if not is_valid:
        errors.append(error)
    else:
        validated["tenant_id"] = data.get("tenant_id").strip()

    # Optional: renewal_status
    is_valid, error = validate_renewal_status(data.get("renewal_status"))
    if not is_valid:
        errors.append(error)
    else:
        validated["renewal_status"] = data.get("renewal_status")

    # Optional: contract_delivered (boolean)
    is_valid, error = validate_boolean(
        data.get("contract_delivered"), "contract_delivered"
    )
    if not is_valid:
        errors.append(error)
    else:
        validated["contract_delivered"] = data.get("contract_delivered")

    # Optional: contract_picked_up (boolean)
    is_valid, error = validate_boolean(
        data.get("contract_picked_up"), "contract_picked_up"
    )
    if not is_valid:
        errors.append(error)
    else:
        validated["contract_picked_up"] = data.get("contract_picked_up")

    # Optional: dates
    for date_field in [
        "leaving_date",
        "replacement_contract_start",
        "replacement_contract_end",
    ]:
        is_valid, error = validate_date_string(data.get(date_field), date_field)
        if not is_valid:
            errors.append(error)
        else:
            validated[date_field] = data.get(date_field)

    # Optional: replacement info
    validated["replacement_name"] = sanitize_string(data.get("replacement_name"))
    validated["replacement_phone"] = sanitize_string(data.get("replacement_phone"))
    validated["replacement_aval_name"] = sanitize_string(
        data.get("replacement_aval_name")
    )
    validated["replacement_aval_phone"] = sanitize_string(
        data.get("replacement_aval_phone")
    )

    if errors:
        return False, "; ".join(errors), {}

    return True, None, validated
