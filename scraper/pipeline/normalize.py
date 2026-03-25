from scraper.config import COMPANY_ALIASES, COMPANY_LEGAL_SUFFIXES


def normalize_company(name: str | None) -> str | None:
    """
    Normalize a company name:
    1. Check alias map first (exact match, case-sensitive)
    2. Strip legal suffixes
    3. Return None if input is None
    """
    if not name:
        return name

    name = name.strip()

    # Alias map takes priority — handles known variants exactly
    if name in COMPANY_ALIASES:
        return COMPANY_ALIASES[name]

    # Strip legal suffixes (longest first to avoid partial stripping)
    for suffix in sorted(COMPANY_LEGAL_SUFFIXES, key=len, reverse=True):
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
            break  # only strip one suffix

    return name if name else None
