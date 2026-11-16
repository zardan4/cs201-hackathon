"""Canonical skills from the shared JSON catalogue and DOU vacancy positions."""

import json
import re
from importlib import import_module
from pathlib import Path

from flask import current_app

# Snapshot of individual categories in dou_active_vacancies.csv, split on ';' or ','.
# DA's API replaces this snapshot; web runtime never reads the raw CSV.
_POSITIONS = [
    ".NET", "AI/ML", "Analyst", "Android", "Architect", "Big Data", "Blockchain",
    "C++", "C-level", "DBA", "Data Engineer", "Data Science", "Design", "DevOps",
    "ERP/CRM", "Embedded", "Engineering Manager", "Flutter", "Front End", "Golang",
    "Hardware", "Java", "No-code", "Node.js", "Other", "PHP", "Product Manager",
    "Project Manager", "Python", "QA", "React Native", "Ruby", "Rust", "SAP",
    "Salesforce", "Scala", "Scrum Master", "Security", "Support", "SysAdmin",
    "Technical Writer", "Unity", "Unreal Engine",
]


class CatalogUnavailable(ValueError):
    """The shared skill catalogue is missing or invalid."""


def analytics_module(name: str):
    """Only fall back for an absent module, not for errors in an existing one."""
    try:
        return import_module(name)
    except ModuleNotFoundError as error:
        if error.name in {"analytics", name}:
            return None
        raise


def _skill_entries(*, required: bool) -> list[dict]:
    path = Path(current_app.config["SKILLS_CATALOG_PATH"])
    try:
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        else:
            module = analytics_module("analytics.skills")
            raw = module.all_skills() if module is not None else []
    except (OSError, ValueError) as error:
        raise CatalogUnavailable("The skills JSON catalogue could not be read.") from error
    if not isinstance(raw, list):
        raise CatalogUnavailable("The skills JSON catalogue must contain a list.")
    entries = {}
    for item in raw:
        if isinstance(item, str):
            item = {"name": item, "aliases": []}
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise CatalogUnavailable("Each skill needs a canonical name.")
        name = item["name"].strip().casefold()
        aliases = item.get("aliases", [])
        if not name or not isinstance(aliases, list) or not all(isinstance(alias, str) for alias in aliases):
            raise CatalogUnavailable("Skill names and aliases must be nonempty strings.")
        previous = entries.get(name, {"aliases": []})
        entries[name] = {"name": name, "aliases": sorted({alias.strip().casefold()
                         for alias in [*previous["aliases"], *aliases] if alias.strip()})}
    if required and not entries:
        raise CatalogUnavailable("Add analytics/skills_catalog.json before enabling CV analysis.")
    return [entries[name] for name in sorted(entries)]


def skill_entries() -> list[dict]:
    """Return the authoritative nonempty catalogue, including aliases for Gemini."""
    return _skill_entries(required=True)


def all_skills() -> list[str]:
    return [entry["name"] for entry in _skill_entries(required=False)]


SKILL_GROUPS = [("language", "Languages"), ("framework", "Frameworks"), ("tool", "Tools"),
                ("cloud", "Cloud"), ("other", "Other")]


def skill_groups() -> list[dict]:
    """Catalogue skills grouped for the profile picker: [{"label", "skills": [...]}].

    Uses the optional ``group`` field of skills_catalog.json; anything unknown goes
    to "Other". Every name from all_skills() appears exactly once.
    """
    names = all_skills()
    grouped = {key: [] for key, _ in SKILL_GROUPS}
    try:
        raw = json.loads(Path(current_app.config["SKILLS_CATALOG_PATH"]).read_text(encoding="utf-8-sig"))
        by_name = {item["name"].strip().casefold(): item.get("group") for item in raw if isinstance(item, dict) and isinstance(item.get("name"), str)}
    except (OSError, ValueError, TypeError):
        by_name = {}
    for name in names:
        group = by_name.get(name)
        grouped[group if group in grouped else "other"].append(name)
    return [{"label": label, "skills": grouped[key]} for key, label in SKILL_GROUPS if grouped[key]]


def detected_skills(text: str) -> list[str]:
    """Find every supported CV keyword using the same extractor as vacancies."""
    entries = skill_entries()
    allowed = {entry["name"] for entry in entries}
    module = analytics_module("analytics.skills")
    if module is not None:
        return sorted(allowed.intersection(module.extract_skills(text)))
    return sorted(entry["name"] for entry in entries if any(
        re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text, re.IGNORECASE)
        for alias in {entry["name"], *entry["aliases"]}))


def all_positions() -> list[str]:
    module = analytics_module("analytics.skills")
    values = module.all_positions() if module is not None else _POSITIONS
    return sorted({position.strip() for value in values
                   for position in re.split(r"[,;]", value) if position.strip()})
