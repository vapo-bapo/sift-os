import re
import unicodedata
from urllib.parse import urlsplit


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    prefix = "+" if stripped.startswith("+") else ""
    digits = re.sub(r"\D", "", stripped)
    return f"{prefix}{digits}" if digits else None


def normalize_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    words = re.findall(r"[a-z0-9]+", ascii_value.casefold())
    return " ".join(words)


def normalize_domain(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip().casefold()
    if not candidate:
        return None
    parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}")
    host = (parsed.hostname or "").rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or None
