"""Map country names to ISO 3166-1 alpha-2 codes."""

# Common country name variations to ISO 3166-1 alpha-2 codes
COUNTRY_NAME_TO_ISO = {
    # Major UFC countries
    "United States": "US",
    "USA": "US",
    "Brazil": "BR",
    "Brasil": "BR",
    "Canada": "CA",
    "United Kingdom": "GB",
    "UK": "GB",
    "England": "GB",
    "Ireland": "IE",
    "Russia": "RU",
    "Russian Federation": "RU",
    "Mexico": "MX",
    "Australia": "AU",
    "Poland": "PL",
    "France": "FR",
    "Netherlands": "NL",
    "Sweden": "SE",
    "Germany": "DE",
    "Spain": "ES",
    "Italy": "IT",
    "Japan": "JP",
    "South Korea": "KR",
    "Korea": "KR",
    "China": "CN",
    "New Zealand": "NZ",
    "Argentina": "AR",
    "Chile": "CL",
    "Austria": "AT",
    "Belgium": "BE",
    "Croatia": "HR",
    "Czech Republic": "CZ",
    "Denmark": "DK",
    "Finland": "FI",
    "Georgia": "GE",
    "Greece": "GR",
    "Iceland": "IS",
    "Kazakhstan": "KZ",
    "Lithuania": "LT",
    "Norway": "NO",
    "Portugal": "PT",
    "Romania": "RO",
    "Serbia": "RS",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Switzerland": "CH",
    "Turkey": "TR",
    "Ukraine": "UA",
    "South Africa": "ZA",
    "Nigeria": "NG",
    "Cameroon": "CM",
    "Egypt": "EG",
    "Morocco": "MA",
    "Tunisia": "TN",
    "Israel": "IL",
    "Philippines": "PH",
    "Thailand": "TH",
    "Indonesia": "ID",
    "Vietnam": "VN",
    "India": "IN",
    "Pakistan": "PK",
    "Afghanistan": "AF",
    "Iraq": "IQ",
    "Iran": "IR",
    "Lebanon": "LB",
    "Syria": "SY",
    "Saudi Arabia": "SA",
    "United Arab Emirates": "AE",
    "UAE": "AE",
}


def normalize_nationality(country_name: str | None) -> str | None:
    """
    Convert country name to ISO 3166-1 alpha-2 code.

    Args:
        country_name: Full country name (e.g., "United States")

    Returns:
        ISO alpha-2 code (e.g., "US") or None if not found
    """
    if not country_name:
        return None

    # Clean and normalize
    country_name = country_name.strip()

    # Try exact match first
    if country_name in COUNTRY_NAME_TO_ISO:
        return COUNTRY_NAME_TO_ISO[country_name]

    # Try case-insensitive match
    for name, code in COUNTRY_NAME_TO_ISO.items():
        if name.lower() == country_name.lower():
            return code

    # Log unmapped countries for future additions
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Unmapped country name: '{country_name}'")

    return None
