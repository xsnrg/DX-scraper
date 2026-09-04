import re

BAND_RANGES = {
    "160m": (1.800, 2.000),
    "80m": (3.500, 4.000),
    "40m": (7.000, 7.300),
    "30m": (10.100, 10.150),
    "20m": (14.000, 14.350),
    "17m": (18.068, 18.168),
    "15m": (21.000, 21.450),
    "12m": (24.890, 24.990),
    "10m": (28.000, 29.700),
    "6m": (50.000, 54.000),
    "2m": (144.000, 148.000),
    "70cm": (420.000, 450.000),
}

# Longer tokens first so FT8/PSK31 win over FT/PSK.
_KNOWN_MODES = (
    "PSK31", "MSK144", "JT65", "JT9", "FT8", "FT4", "JS8",
    "RTTY", "DIGI", "OLIVIA", "WSPR", "Q65",
    "USB", "LSB", "SSB", "CW", "AM", "FM", "PSK",
)
_MODE_RE = re.compile(
    r"\b(" + "|".join(_KNOWN_MODES) + r")\b",
    re.IGNORECASE,
)


def frequency_to_band(freq_mhz: float) -> str | None:
    for band, (low, high) in BAND_RANGES.items():
        if low <= freq_mhz <= high:
            return band
    return None


def band_to_range(band: str) -> tuple[float, float] | None:
    return BAND_RANGES.get(canonical_band(band) or band)


def canonical_band(band: str) -> str:
    """Normalize band labels so HamQTH `20M` matches DX Summit `20m`."""
    b = (band or "").strip().replace(" ", "")
    if not b:
        return ""
    lower = b.lower()
    if lower.endswith("cm"):
        return b[:-2] + "cm"
    if lower.endswith("m"):
        return b[:-1] + "m"
    return b


def mode_from_text(text: str) -> str:
    match = _MODE_RE.search(text or "")
    return match.group(1).upper() if match else ""
