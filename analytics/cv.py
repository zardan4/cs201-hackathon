"""DA0 stub for CV text parsing backed by real skill extraction."""

from __future__ import annotations

import re

from analytics.skills import all_positions, extract_skills

_EXP_RE = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?|р\.|рок(?:ів|и))", re.IGNORECASE)
_ENGLISH_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("fluent", re.compile(r"\b(?:fluent|c2|native)\b", re.IGNORECASE)),
    ("upper", re.compile(r"\b(?:upper[\s-]?intermediate|b2|c1)\b", re.IGNORECASE)),
    ("intermediate", re.compile(r"\b(?:intermediate|b1)\b", re.IGNORECASE)),
    ("pre", re.compile(r"\b(?:pre[\s-]?intermediate|a2)\b", re.IGNORECASE)),
    ("basic", re.compile(r"\b(?:basic|elementary|a1|beginner)\b", re.IGNORECASE)),
]


def parse_cv(text: str) -> dict:
    """Extract skills, rough experience, and English level from CV text (DA0/DA7)."""
    raw = text or ""
    skills = extract_skills(raw)

    detected_position: str | None = None
    low_raw = raw.lower()
    for pos in all_positions():
        if pos.lower() in low_raw:
            detected_position = pos
            break

    exp_years: float | None = None
    if exp_match := _EXP_RE.search(raw):
        exp_years = float(exp_match.group(1))

    english_level: str | None = None
    for level, pat in _ENGLISH_PATTERNS:
        if pat.search(raw):
            english_level = level
            break

    warnings: list[str] = []
    if not skills:
        warnings.append("Не вдалося автоматично розпізнати навички — оберіть вручну.")

    return {
        "raw_text": raw,
        "detected_position": detected_position,
        "detected_skills": skills,
        "detected_experience_years": exp_years,
        "detected_english_level": english_level,
        "warnings": warnings,
    }
