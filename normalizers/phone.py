import phonenumbers
from typing import Optional

def normalize_phone(phone_str: Optional[str], default_region: str = "US") -> Optional[str]:
    """
    Normalizes phone numbers to E.164 format.
    If phone is invalid or parsing fails, returns the original input.
    """
    if not phone_str:
        return None
        
    try:
        # Parse phone number (e.g. "+1-555-555-5555" or "(555) 555-5555")
        parsed_number = phonenumbers.parse(phone_str, default_region)
        if phonenumbers.is_possible_number(parsed_number):
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        # Fall back to returning clean original string
        pass
        
    # Strip basic noise if parsing fails but keep the characters
    cleaned = "".join(c for c in phone_str if c.isalnum() or c in "+-()")
    return cleaned if cleaned else None
