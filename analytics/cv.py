"""Extract position, canonical skills, experience, and English level from CV text (DA7)."""

from __future__ import annotations

import datetime
import re

from analytics.skills import extract_skills

_EXP_EXPLICIT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*\+?\s*(?:years?|yrs?|р\.|рок(?:ів|и))",
    re.IGNORECASE,
)
_YEAR_RANGE_RE = re.compile(
    r"\b(20[0-2]\d)\s*[–\-—]\s*(20[0-2]\d|present|now|current|дотепер|зараз|н\.?\s*ч\.?)\b",
    re.IGNORECASE,
)

_ENGLISH_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("fluent", re.compile(r"\b(?:fluent|c2|native|proficiency)\b|вільн[аией]\w*", re.IGNORECASE)),
    ("upper", re.compile(r"\b(?:upper[\s-]?intermediate|b2|c1|advanced)\b|вище\s+середнього", re.IGNORECASE)),
    ("intermediate", re.compile(r"\b(?:intermediate|b1)\b|(?<!вище\s)середн[ійяє]\w*", re.IGNORECASE)),
    ("pre", re.compile(r"\b(?:pre[\s-]?intermediate|a2)\b", re.IGNORECASE)),
    ("basic", re.compile(r"\b(?:basic|elementary|a1|beginner)\b|початков\w*", re.IGNORECASE)),
]

# Ordered position patterns checked against CV headline first, then full text.
_POSITION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AI/ML", re.compile(r"\b(?:ai/ml|ml\s+engineer|ai\s+engineer|machine\s+learning|computer\s+vision|nlp\s+engineer)\b", re.IGNORECASE)),
    ("Data Science", re.compile(r"\bdata\s+scien(?:tist|ce)\b", re.IGNORECASE)),
    ("Data Engineer", re.compile(r"\bdata\s+engineer\b", re.IGNORECASE)),
    ("DevOps", re.compile(r"\b(?:devops|devsecops|site\s+reliability|sre)\b", re.IGNORECASE)),
    ("QA", re.compile(r"\b(?:qa|aqa|sdet|quality\s+assurance|test\s+engineer|automation\s+qa)\b|тестувальни\w*", re.IGNORECASE)),
    ("Analyst", re.compile(r"\b(?:data\s+analyst|business\s+analyst|product\s+analyst|bi\s+analyst|system\s+analyst)\b|(?:бізнес|дата|системн\w*)[-\s]*аналітик\w*", re.IGNORECASE)),
    ("Product Manager", re.compile(r"\b(?:product\s+manager|product\s+owner)\b", re.IGNORECASE)),
    ("Project Manager", re.compile(r"\b(?:project\s+manager|delivery\s+manager)\b", re.IGNORECASE)),
    ("Scrum Master", re.compile(r"\bscrum\s+master\b", re.IGNORECASE)),
    ("Design", re.compile(r"\b(?:ui/ux|ux/ui|product\s+designer|ui\s+designer|ux\s+designer|motion\s+designer|graphic\s+designer)\b", re.IGNORECASE)),
    ("Security", re.compile(r"\b(?:cybersecurity|security\s+engineer|infosec|pentest\w*|soc\s+analyst)\b|кібербезпек\w*", re.IGNORECASE)),
    ("Embedded", re.compile(r"\b(?:embedded|firmware)\b", re.IGNORECASE)),
    ("Hardware", re.compile(r"\b(?:hardware\s+engineer|pcb\s+design\w*|fpga)\b|інженер-конструктор", re.IGNORECASE)),
    ("SysAdmin", re.compile(r"\b(?:sysadmin|system\s+administrator)\b|системн\w*\s+адміністратор\w*", re.IGNORECASE)),
    ("Support", re.compile(r"\b(?:technical\s+support|customer\s+support|helpdesk)\b|технічної\s+підтримки", re.IGNORECASE)),
    ("Technical Writer", re.compile(r"\btechnical\s+writer\b", re.IGNORECASE)),
    ("Architect", re.compile(r"\b(?:solution[s]?\s+architect|system\s+architect|software\s+architect|data\s+architect)\b", re.IGNORECASE)),
    ("Engineering Manager", re.compile(r"\bengineering\s+manager\b", re.IGNORECASE)),
    ("Front End", re.compile(r"\b(?:front[\s-]?end|frontend|react\s+developer|angular\s+developer|vue\s+developer)\b", re.IGNORECASE)),
    ("Node.js", re.compile(r"\b(?:node\.?js|nestjs)\s*(?:developer|engineer)?\b", re.IGNORECASE)),
    ("Python", re.compile(r"\bpython\b", re.IGNORECASE)),
    (".NET", re.compile(r"(?:^|\s)(?:\.net|c#|asp\.net)\b", re.IGNORECASE)),
    ("Java", re.compile(r"\bjava(?!script)\b", re.IGNORECASE)),
    ("Golang", re.compile(r"\b(?:golang|go\s+developer|go\s+engineer)\b", re.IGNORECASE)),
    ("C++", re.compile(r"(?:^|\s)c\+\+", re.IGNORECASE)),
    ("PHP", re.compile(r"\bphp\b", re.IGNORECASE)),
    ("Android", re.compile(r"\bandroid\b", re.IGNORECASE)),
    ("Flutter", re.compile(r"\bflutter\b", re.IGNORECASE)),
    ("Rust", re.compile(r"\brust\b", re.IGNORECASE)),
    ("Ruby", re.compile(r"\bruby\b", re.IGNORECASE)),
    ("Scala", re.compile(r"\bscala\b", re.IGNORECASE)),
    ("DBA", re.compile(r"\b(?:dba|database\s+administrator)\b", re.IGNORECASE)),
    ("Salesforce", re.compile(r"\bsalesforce\b", re.IGNORECASE)),
    ("SAP", re.compile(r"\bsap\b", re.IGNORECASE)),
]

_SKILL_TO_POSITION: tuple[tuple[str, str], ...] = (
    ("automation qa", "QA"),
    ("qa", "QA"),
    ("devops", "DevOps"),
    ("kubernetes", "DevOps"),
    ("ai/ml", "AI/ML"),
    ("data engineering", "Data Engineer"),
    ("data science", "Data Science"),
    ("data analysis", "Analyst"),
    ("business analysis", "Analyst"),
    ("python", "Python"),
    ("c#/.net", ".NET"),
    ("java", "Java"),
    ("node.js", "Node.js"),
    ("react", "Front End"),
    ("angular", "Front End"),
    ("vue", "Front End"),
    ("typescript", "Front End"),
    ("c++", "C++"),
    ("php", "PHP"),
    ("go", "Golang"),
    ("ui/ux", "Design"),
    ("figma", "Design"),
    ("cybersecurity", "Security"),
    ("embedded", "Embedded"),
)


def _detect_position(raw: str, skills: list[str]) -> str | None:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    headline = "\n".join(lines[:2])
    for zone in (headline, raw):
        matches: list[tuple[int, int, str]] = []
        for priority, (pos, pat) in enumerate(_POSITION_PATTERNS):
            if m := pat.search(zone):
                matches.append((m.start(), priority, pos))
        if matches:
            matches.sort()
            return matches[0][2]

    skill_set = set(skills)
    for skill, pos in _SKILL_TO_POSITION:
        if skill in skill_set:
            return pos
    return None


def _detect_experience(raw: str) -> float | None:
    explicit = [float(m.group(1).replace(",", ".")) for m in _EXP_EXPLICIT_RE.finditer(raw)]
    valid_explicit = [y for y in explicit if 0.0 <= y <= 40.0]
    if valid_explicit:
        return max(valid_explicit)

    current_year = datetime.date.today().year
    starts: list[int] = []
    ends: list[int] = []
    for m in _YEAR_RANGE_RE.finditer(raw):
        start_y = int(m.group(1))
        end_raw = m.group(2).lower()
        end_y = current_year if not end_raw.isdigit() else int(end_raw)
        if 2000 <= start_y <= current_year and start_y <= end_y <= current_year + 1:
            starts.append(start_y)
            ends.append(end_y)
    if starts and ends:
        span = max(0, max(ends) - min(starts))
        return float(min(span, 30))
    return None


# "English: Upper-Intermediate" up to the next separator, so "· Ukrainian: native" is not included.
_ENGLISH_FRAGMENT_RE = re.compile(r"(?:english|англ\w*)[^·•,;|\n]*", re.IGNORECASE)


def _detect_english(raw: str) -> str | None:
    """English level, preferring the text right after the word "English".

    Otherwise "Ukrainian: native" elsewhere in the CV would be read as fluent English.
    """
    english_fragments = "\n".join(_ENGLISH_FRAGMENT_RE.findall(raw))
    for text in (english_fragments, raw):
        if not text:
            continue
        for level, pattern in _ENGLISH_PATTERNS:
            if pattern.search(text):
                return level
    return None


def parse_cv(text: str) -> dict:
    """Parse CV text into CvParseResult dict (position, skills, experience, english, warnings)."""
    raw = (text or "").strip()
    if not raw:
        return {
            "raw_text": "",
            "detected_position": None,
            "detected_skills": [],
            "detected_experience_years": None,
            "detected_english_level": None,
            "warnings": ["Текст резюме порожній — заповніть профіль вручну."],
        }

    skills = extract_skills(raw)
    detected_position = _detect_position(raw, skills)
    exp_years = _detect_experience(raw)

    english_level = _detect_english(raw)

    warnings: list[str] = []
    if not skills:
        warnings.append("Не вдалося автоматично розпізнати навички — оберіть вручну.")
    if detected_position is None:
        warnings.append("Позицію не розпізнано — оберіть зі списку.")

    return {
        "raw_text": raw,
        "detected_position": detected_position,
        "detected_skills": skills,
        "detected_experience_years": exp_years,
        "detected_english_level": english_level,
        "warnings": warnings,
    }
