from typing import Optional

def normalize_url(url: Optional[str]) -> Optional[str]:
    """
    Normalizes URLs to ensure they start with http:// or https://.
    Preserves existing schemes if present.
    """
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if url.lower().startswith(("http://", "https://")):
        return url
    return f"https://{url}"
