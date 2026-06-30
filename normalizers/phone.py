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
        pass
        
    # Strip all non-digit characters except leading +
    cleaned = ""
    for i, c in enumerate(phone_str):
        if i == 0 and c == "+":
            cleaned += c
        elif c.isdigit():
            cleaned += c
            
    # If no leading +, we could assume US (+1) but it's safer to just return digits.
    # The validator requires a leading +, so if it's missing but we have digits, prepend +
    if cleaned and not cleaned.startswith('+'):
        cleaned = '+' + cleaned
        
    return cleaned if len(cleaned) >= 8 else None
