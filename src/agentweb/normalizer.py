"""Canonicalize common extracted fields without discarding unparseable values."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation


@dataclass
class NormalizedField:
    value: object
    expected_type: str
    normalized: bool
    raw: object
    currency: str | None = None
    confidence: float = 0.0


_CURRENCY_MARKERS = (
    ("INR", "INR"),
    ("USD", "USD"),
    ("EUR", "EUR"),
    ("GBP", "GBP"),
    ("Rs", "INR"),
    ("₹", "INR"),
    ("$", "USD"),
    ("€", "EUR"),
    ("£", "GBP"),
)
_MONTH_NAMES = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}


def _currency(text: str) -> str | None:
    for marker, code in _CURRENCY_MARKERS:
        if marker.isalpha():
            if re.search(rf"(?i)(?<![A-Za-z]){re.escape(marker)}(?![A-Za-z])", text):
                return code
        elif marker in text:
            return code
    return None


def _numeric_price(text: str) -> str:
    """Convert common grouping/decimal separator conventions to Decimal syntax."""
    text = re.sub(r"(?i)\b(?:INR|USD|EUR|GBP|Rs)\b", "", text)
    text = re.sub(r"[$€£₹]", "", text)
    text = text.replace("\u00a0", " ").replace("\u202f", " ")
    text = re.sub(r"[\s']+", "", text)
    text = re.sub(r"[^0-9,.+-]", "", text)
    if text.count("+") + text.count("-") > 1 or ("+" in text[1:] or "-" in text[1:]):
        raise InvalidOperation
    if "," in text and "." in text:
        decimal_separator = "," if text.rfind(",") > text.rfind(".") else "."
        grouping_separator = "." if decimal_separator == "," else ","
        text = text.replace(grouping_separator, "").replace(decimal_separator, ".")
    elif "," in text:
        before, after = text.rsplit(",", 1)
        text = f"{before}.{after}" if len(after) in {1, 2} else text.replace(",", "")
    elif "." in text and text.count(".") == 1:
        before, after = text.split(".", 1)
        if len(after) == 3 and before:
            text = before + after
    else:
        text = text.replace(".", "")
    return text


def _price(raw: object) -> NormalizedField:
    text = str(raw).strip()
    currency = _currency(text)
    negative_parentheses = text.startswith("(") and text.endswith(")")
    if negative_parentheses:
        text = text[1:-1]
    cleaned = _numeric_price(text)
    if negative_parentheses:
        cleaned = "-" + cleaned
    try:
        number = Decimal(cleaned)
        value: int | float = int(number) if number == number.to_integral_value() else float(number)
        return NormalizedField(value=value, expected_type="price", normalized=True, raw=raw, currency=currency, confidence=0.95)
    except (InvalidOperation, ValueError):
        return NormalizedField(value=raw, expected_type="price", normalized=False, raw=raw, currency=currency, confidence=0.20)


def _month_number(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    for name, month in sorted(_MONTH_NAMES.items(), key=lambda item: len(item[0]), reverse=True):
        plain_name = unicodedata.normalize("NFKD", name)
        plain_name = "".join(char for char in plain_name if not unicodedata.combining(char))
        if re.search(rf"(?i)\b{re.escape(plain_name)}\b", normalized):
            normalized = re.sub(rf"(?i)\b{re.escape(plain_name)}\b", str(month), normalized)
    return normalized


def _date(raw: object, expected_type: str = "date") -> NormalizedField:
    text = str(raw).strip()
    candidates = [text, text.replace("Z", "+00:00")]
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            return NormalizedField(
                value=(parsed.isoformat().replace("+00:00", "Z") if expected_type == "datetime" else parsed.date().isoformat()),
                expected_type=expected_type,
                normalized=True,
                raw=raw,
                confidence=0.95,
            )
        except ValueError:
            continue
    normalized_text = _month_number(text)
    formats = (
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y",
        "%d-%m-%Y", "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
        "%d %m %Y", "%d. %m %Y", "%d/%m %Y", "%d-%m %Y",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(normalized_text, fmt)
            return NormalizedField(
                value=(parsed.isoformat() if expected_type == "datetime" else parsed.date().isoformat()), expected_type=expected_type, normalized=True, raw=raw, confidence=0.90
            )
        except ValueError:
            continue
    return NormalizedField(value=raw, expected_type=expected_type, normalized=False, raw=raw, confidence=0.20)


def _entity(raw: object) -> NormalizedField:
    text = re.sub(r"\s+", " ", str(raw).strip())
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return NormalizedField(value=text, expected_type="entity", normalized=bool(text), raw=raw, confidence=0.85 if text else 0.0)


def normalize(raw: object, expected_type: str) -> NormalizedField:
    """Normalize a field; unsupported types remain raw and receive low confidence."""
    kind = expected_type.strip().lower()
    if kind == "price":
        return _price(raw)
    if kind in {"date", "datetime"}:
        return _date(raw, kind)
    if kind in {"entity", "entity_name", "string"}:
        return _entity(raw)
    return NormalizedField(value=raw, expected_type=kind, normalized=False, raw=raw, confidence=0.20 if raw not in (None, "") else 0.0)
