"""Skill, position, and secondary tag extraction backed by skills_catalog.json."""

from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from pathlib import Path

ANALYTICS_DIR = Path(__file__).resolve().parent
ROOT_DIR = ANALYTICS_DIR.parent
CATALOG_PATH = ANALYTICS_DIR / "skills_catalog.json"
DEFAULT_CSV_PATH = ROOT_DIR / "data" / "dou_active_vacancies.csv"

_WORD_CHAR = r"A-Za-zА-Яа-яІіЇїЄєҐґ0-9_"
_LEFT_BOUNDARY = rf"(?<![{_WORD_CHAR}])"
_RIGHT_BOUNDARY = rf"(?![{_WORD_CHAR}])"

# Aliases that collide with common English words or other skill names unless constrained.
_CUSTOM_PATTERNS: dict[str, tuple[str, int]] = {
    "c": (r"(?<![A-Za-z0-9_.+#/-])C(?![+#A-Za-z0-9_/-])", 0),
    "go": (
        r"(?<![A-Za-z0-9_.+#/-])Go"
        r"(?=(?:\s+(?:developer|engineer|backend|programmer|lang|microservices|service|code|team)|[/,)\s]|$))"
        r"(?!-to-market|\s+live|\s+beyond|\s+ahead)",
        0,
    ),
    "java": (rf"{_LEFT_BOUNDARY}java(?!script){_RIGHT_BOUNDARY}", re.IGNORECASE),
    "react": (rf"{_LEFT_BOUNDARY}react(?!\s+native){_RIGHT_BOUNDARY}", re.IGNORECASE),
    "ai": (rf"{_LEFT_BOUNDARY}AI{_RIGHT_BOUNDARY}", 0),
    "ts": (rf"(?<![{_WORD_CHAR}.])TS{_RIGHT_BOUNDARY}", 0),
    "js": (rf"(?<![{_WORD_CHAR}.])(?:JS|js){_RIGHT_BOUNDARY}", 0),
    "ros": (rf"{_LEFT_BOUNDARY}ROS2?{_RIGHT_BOUNDARY}", 0),
    "l1": (rf"{_LEFT_BOUNDARY}L1{_RIGHT_BOUNDARY}", 0),
    "l2": (rf"{_LEFT_BOUNDARY}L2{_RIGHT_BOUNDARY}", 0),
}

# Unambiguous mapping from DOU vacancy categories to canonical skills.
_CATEGORY_TO_SKILLS: dict[str, tuple[str, ...]] = {
    ".NET": ("c#/.net",),
    "AI/ML": ("ai/ml",),
    "Android": ("android",),
    "Architect": ("architecture",),
    "Big Data": ("big data",),
    "Blockchain": ("blockchain",),
    "C++": ("c++",),
    "DBA": ("dba", "sql"),
    "Data Engineer": ("data engineering",),
    "Data Science": ("data science",),
    "DevOps": ("devops",),
    "Embedded": ("embedded",),
    "Engineering Manager": ("engineering management",),
    "ERP/CRM": ("crm/erp",),
    "Flutter": ("flutter",),
    "Front End": ("frontend",),
    "Golang": ("go",),
    "Hardware": ("hardware",),
    "Java": ("java",),
    "Node.js": ("node.js",),
    "PHP": ("php",),
    "Product Manager": ("product management",),
    "Project Manager": ("project management",),
    "Python": ("python",),
    "QA": ("qa",),
    "React Native": ("react native",),
    "Ruby": ("ruby",),
    "Rust": ("rust",),
    "SAP": ("sap",),
    "Salesforce": ("salesforce",),
    "Scala": ("scala",),
    "Scrum Master": ("scrum/agile",),
    "Security": ("cybersecurity",),
    "Support": ("technical support",),
    "SysAdmin": ("sysadmin",),
    "Technical Writer": ("technical writing",),
    "Unity": ("unity",),
    "Unreal Engine": ("unreal engine",),
}

# Secondary non-skill keywords (seniority, work mode, industry domain).
_TAG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("trainee", re.compile(rf"{_LEFT_BOUNDARY}(?:trainee|intern|стажер){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("junior", re.compile(rf"{_LEFT_BOUNDARY}(?:junior|jun){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("middle", re.compile(rf"{_LEFT_BOUNDARY}(?:middle|mid){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("senior", re.compile(rf"{_LEFT_BOUNDARY}(?:senior|sr){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("lead", re.compile(rf"{_LEFT_BOUNDARY}(?:team\s+lead|tech\s+lead|lead|head\s+of|principal){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("c-level", re.compile(rf"{_LEFT_BOUNDARY}(?:cto|ceo|coo|cfo|ciso|cio|vp\s+of){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("part-time", re.compile(rf"{_LEFT_BOUNDARY}part[\s-]?time{_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("hybrid", re.compile(rf"{_LEFT_BOUNDARY}(?:hybrid|гібрид){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("miltech", re.compile(rf"{_LEFT_BOUNDARY}(?:miltech|deftech|defense|оборон\w*|бпла|fpv|drone|drones|дрон\w*|військов\w*){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("fintech", re.compile(rf"{_LEFT_BOUNDARY}(?:fintech|banking|payment|payments|фінтех){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("igaming", re.compile(rf"{_LEFT_BOUNDARY}(?:igaming|gambling|casino|betting|slots){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("gamedev", re.compile(rf"{_LEFT_BOUNDARY}(?:gamedev|game\s+dev|game\s+engine|game\s+designer|games){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("saas", re.compile(rf"{_LEFT_BOUNDARY}saas{_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("b2b", re.compile(rf"{_LEFT_BOUNDARY}b2b{_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("edtech", re.compile(rf"{_LEFT_BOUNDARY}edtech{_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("ecommerce", re.compile(rf"{_LEFT_BOUNDARY}(?:e-?commerce|retail|marketplace|ритейл){_RIGHT_BOUNDARY}", re.IGNORECASE)),
    ("healthcare", re.compile(rf"{_LEFT_BOUNDARY}(?:healthcare|healthtech|medtech){_RIGHT_BOUNDARY}", re.IGNORECASE)),
]


@lru_cache(maxsize=1)
def all_skills() -> list[dict]:
    """Return the canonical skill catalog entries from analytics/skills_catalog.json."""
    with CATALOG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def _compiled_skill_patterns() -> list[tuple[str, re.Pattern[str]]]:
    """Compile boundary-safe regex matchers for each canonical skill."""
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for entry in all_skills():
        name = entry["name"]
        aliases = entry.get("aliases", [name])
        subpatterns: list[str] = []
        # Split aliases into custom-constrained vs standard boundary-safe patterns.
        case_sensitive_subs: list[str] = []
        case_insensitive_subs: list[str] = []
        for alias in aliases:
            key = alias.lower()
            if key in _CUSTOM_PATTERNS:
                pat, flags = _CUSTOM_PATTERNS[key]
                if flags == 0:
                    case_sensitive_subs.append(pat)
                else:
                    case_insensitive_subs.append(pat)
            else:
                escaped = re.escape(alias).replace(r"\ ", r"\s+")
                case_insensitive_subs.append(rf"{_LEFT_BOUNDARY}{escaped}{_RIGHT_BOUNDARY}")

        if case_insensitive_subs:
            combined_ci = "|".join(case_insensitive_subs)
            compiled.append((name, re.compile(combined_ci, re.IGNORECASE | re.UNICODE)))
        if case_sensitive_subs:
            combined_cs = "|".join(case_sensitive_subs)
            compiled.append((name, re.compile(combined_cs, re.UNICODE)))
    return compiled


def extract_skills(text: str) -> list[str]:
    """Extract deduplicated canonical lowercase skills from arbitrary text."""
    if not text:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for skill_name, pattern in _compiled_skill_patterns():
        if skill_name in seen:
            continue
        if pattern.search(text):
            seen.add(skill_name)
            found.append(skill_name)
    return found


def extract_job_skills(title: str, snippet: str, categories: list[str]) -> list[str]:
    """Extract canonical skills from job title, snippet, and DOU categories."""
    combined_text = f"{title or ''}\n{snippet or ''}"
    skills = extract_skills(combined_text)
    seen = set(skills)

    def _add(skill: str) -> None:
        if skill not in seen:
            seen.add(skill)
            skills.append(skill)

    for category in categories:
        for mapped in _CATEGORY_TO_SKILLS.get(category, ()):
            _add(mapped)

    cat_set = set(categories)
    if "Analyst" in cat_set and not (seen & {"data analysis", "business analysis", "data science", "data engineering"}):
        _add("data analysis")
    if "Design" in cat_set and not (cat_set & {"Hardware", "Embedded"}) and not (seen & {"ui/ux", "motion design", "graphic/game design", "hardware", "fpga"}):
        _add("ui/ux")

    # Also check category text through catalog extractors if not explicitly mapped.
    if categories:
        for extra in extract_skills(" ".join(categories)):
            _add(extra)
    return skills


def extract_tags(title: str, snippet: str = "", location_text: str = "") -> list[str]:
    """Extract seniority, work-format, and industry domain tags from job text."""
    combined = f"{title or ''}\n{snippet or ''}\n{location_text or ''}"
    tags: list[str] = []
    for tag_name, pattern in _TAG_PATTERNS:
        if pattern.search(combined):
            tags.append(tag_name)
    return tags


@lru_cache(maxsize=1)
def all_positions() -> list[str]:
    """Return sorted canonical DOU category/position names from the vacancies dataset."""
    if not DEFAULT_CSV_PATH.exists():
        return sorted(_CATEGORY_TO_SKILLS.keys())
    positions: set[str] = set()
    with DEFAULT_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            raw = row.get("categories") or ""
            sep = ";" if ";" in raw else ","
            for part in raw.split(sep):
                cleaned = part.strip()
                if cleaned:
                    positions.add(cleaned)
    return sorted(positions)
