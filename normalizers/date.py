import re
from typing import Optional

MONTHS = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12"
}

def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Standardize varied human date inputs (e.g. "June 2021", "2021/06", "2021") to YYYY-MM.
    Preserves "Present" / "Current" for active roles.
    """
    if not date_str:
        return None
        
    cleaned = date_str.strip()
    cleaned_lower = cleaned.lower()
    
    if cleaned_lower in ["present", "current", "now", "ongoing"]:
        return "Present"
        
    # Pattern: YYYY-MM or YYYY/MM
    match_ym = re.search(r'\b(\d{4})[-/](\d{1,2})\b', cleaned_lower)
    if match_ym:
        year, month = match_ym.groups()
        return f"{year}-{int(month):02d}"
        
    # Pattern: MM-YYYY or MM/YYYY
    match_my = re.search(r'\b(\d{1,2})[-/](\d{4})\b', cleaned_lower)
    if match_my:
        month, year = match_my.groups()
        return f"{year}-{int(month):02d}"
        
    # Pattern: Month Name + Year (e.g. "June 2021" or "2021 June")
    match_year = re.search(r'\b(\d{4})\b', cleaned_lower)
    if match_year:
        year = match_year.group(1)
        for m_name, m_num in MONTHS.items():
            if m_name in cleaned_lower:
                return f"{year}-{m_num}"
        # If year only, default to Jan
        return f"{year}-01"
        
    # If just a 4-digit number
    if cleaned_lower.isdigit() and len(cleaned_lower) == 4:
        return f"{cleaned_lower}-01"
        
    return cleaned  # Fallback to returning trimmed input
