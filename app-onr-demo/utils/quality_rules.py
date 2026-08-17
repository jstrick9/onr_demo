"""Shared DQ gates — keep in sync with notebooks/02_silver_quality.py."""

from __future__ import annotations

KNOWN_PROGRAM_AREAS = frozenset(
    {
        "AI/ML",
        "Autonomy",
        "Biotech",
        "Cyber",
        "Directed Energy",
        "Materials",
        "Quantum",
        "Undersea",
    }
)

LARGE_AMOUNT_USD = 5_000_000

QUARANTINE_CODES = {
    "empty": "Empty grant_no",
    "dup": "Duplicate grant_no",
    "amt": "Amount not positive",
}

WARN_CODES = {
    "missing_abstract": "Missing abstract",
    "unknown_program_area": "Unknown program area",
    "large_amount": "Amount over $5M",
}


def is_empty_grant_no(raw) -> bool:
    try:
        import math

        if raw is None or (isinstance(raw, float) and math.isnan(raw)):
            return True
    except Exception:
        pass
    gn = str(raw).strip()
    return (not gn) or gn.lower() in {"nan", "none", "null"}


def parse_amount(raw):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def quarantine_reason(rec: dict, exists_in_bronze: bool) -> tuple[str, str] | None:
    if is_empty_grant_no(rec.get("grant_no")):
        return "empty", QUARANTINE_CODES["empty"]
    amount = parse_amount(rec.get("amount_usd"))
    if amount is None:
        return "amt", "Amount not numeric"
    if amount <= 0:
        return "amt", QUARANTINE_CODES["amt"]
    if exists_in_bronze:
        return "dup", QUARANTINE_CODES["dup"]
    return None


def warn_findings(rec: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    abstract = str(rec.get("abstract") or "").strip()
    if not abstract:
        out.append(("missing_abstract", WARN_CODES["missing_abstract"]))
    area = str(rec.get("program_area") or "").strip()
    if area and area not in KNOWN_PROGRAM_AREAS:
        out.append(("unknown_program_area", f"{WARN_CODES['unknown_program_area']}: {area}"))
    if not area:
        out.append(("unknown_program_area", WARN_CODES["unknown_program_area"]))
    amount = parse_amount(rec.get("amount_usd"))
    if amount is not None and amount > LARGE_AMOUNT_USD:
        out.append(("large_amount", f"{WARN_CODES['large_amount']} (${amount:,.0f})"))
    return out
