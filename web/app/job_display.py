"""Display helpers for job cards: an icon per vacancy category and a seniority level from the title."""

import re

# DOU category -> icon name from templates/swipe/_icons.html (first matching category wins).
CATEGORY_ICONS = {
    "AI/ML": "ai", "Data Science": "ai",
    "Big Data": "data", "Data Engineer": "data", "DBA": "data", "Analyst": "data",
    "DevOps": "cloud",
    "Security": "shield",
    "Android": "phone", "Flutter": "phone", "React Native": "phone",
    "Embedded": "chip", "Hardware": "chip",
    "Unity": "game", "Unreal Engine": "game",
    "QA": "qa",
    "SysAdmin": "wrench", "Support": "wrench",
    "Product Manager": "users", "Project Manager": "users", "Scrum Master": "users",
    "Engineering Manager": "users", "C-level": "users",
    "Design": "palette",
    "Technical Writer": "doc",
    "Blockchain": "cube",
    ".NET": "code", "C++": "code", "Java": "code", "Golang": "code", "Node.js": "code", "PHP": "code",
    "Python": "code", "Ruby": "code", "Rust": "code", "Scala": "code", "Front End": "code",
    "Architect": "code", "No-code": "code",
}

# Level name -> pattern; the level that appears first in the title wins ("Junior/Middle" -> Junior).
_LEVELS = [
    ("Intern", r"\b(?:intern|internship|trainee)\b|стажер|стажист"),
    ("Junior", r"\b(?:junior|jun)\b|джуніор|молодший"),
    ("Middle", r"\b(?:middle|mid|mid-level)\b|мідл"),
    ("Senior", r"\b(?:senior|sr)\b|сеньйор|сеньор|старший"),
    ("Lead", r"\b(?:lead|head|principal|staff)\b|тімлід|тімлід"),
]
_LEVEL_RES = [(name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _LEVELS]


def category_icon(categories) -> str:
    """Icon name for the first known category; 'briefcase' when none matches."""
    for category in categories or []:
        if category in CATEGORY_ICONS:
            return CATEGORY_ICONS[category]
    return "briefcase"


def job_level(title: str) -> str | None:
    """Seniority read from a vacancy title, or None when the title does not say."""
    best = None
    for name, pattern in _LEVEL_RES:
        match = pattern.search(title or "")
        if match and (best is None or match.start() < best[0]):
            best = (match.start(), name)
    return best[1] if best else None
