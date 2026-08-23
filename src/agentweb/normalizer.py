"""Canonicalize common extracted fields without discarding unparseable values."""

from __future__ import annotations

import re
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


def _price(raw: object) -> NormalizedField:
    text = str(raw).strip()
    currency = None
    for marker, code in (("₹", "INR"), ("$", "USD"), ("€", "EUR"), ("£", "GBP")):
        if marker in text:
            currency = code
            break
    cleaned = re.sub(r"[^0-9,.-]", "", text).replace(",", "")
    try:
        number = Decimal(cleaned)
        value: int | float = int(number) if number == number.to_integral_value() else float(number)
        return NormalizedField(value=value, expected_type="price", normalized=True, raw=raw, currency=currency, confidence=0.95)
    except (InvalidOperation, ValueError):
        return NormalizedField(value=raw, expected_type="price", normalized=False, raw=raw, currency=currency, confidence=0.20)


def _date(raw: object) -> NormalizedField:
    text = str(raw).strip()
    candidates = [text, text.replace("Z", "+00:00")]
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            return NormalizedField(
                value=parsed.isoformat().replace("+00:00", "Z"),
                expected_type="date",
                normalized=True,
                raw=raw,
                confidence=0.95,
            )
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return NormalizedField(
                value=parsed.date().isoformat(), expected_type="date", normalized=True, raw=raw, confidence=0.90
            )
        except ValueError:
            continue
    return NormalizedField(value=raw, expected_type="date", normalized=False, raw=raw, confidence=0.20)


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
        return _date(raw)
    if kind in {"entity", "entity_name", "string"}:
        return _entity(raw)
    return NormalizedField(value=raw, expected_type=kind, normalized=False, raw=raw, confidence=0.20 if raw not in (None, "") else 0.0)
