from typing import Optional

COUNTRY_MAP = {
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "us": "US",
    "india": "IN",
    "ind": "IN",
    "in": "IN",
    "united kingdom": "GB",
    "great britain": "GB",
    "uk": "GB",
    "gb": "GB",
    "canada": "CA",
    "can": "CA",
    "ca": "CA",
    "germany": "DE",
    "deutschland": "DE",
    "de": "DE",
    "france": "FR",
    "fr": "FR",
    "australia": "AU",
    "aus": "AU",
    "au": "AU",
}

def normalize_country(country_str: Optional[str]) -> Optional[str]:
    """
    Normalizes a country name or short-code to an ISO-3166 Alpha-2 code.
    If country is unrecognized, returns it stripped and uppercase.
    """
    if not country_str:
        return None
        
    cleaned = country_str.strip()
    cleaned_lower = cleaned.lower()
    return COUNTRY_MAP.get(cleaned_lower, cleaned.upper())
