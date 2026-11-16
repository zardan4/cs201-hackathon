"""Tests for DA3 (salary_records), DA5 (salary_stats), DA6 (recommend_upgrades), DA7 (parse_cv), and DA8 (build)."""

from __future__ import annotations

import pandas as pd
import pytest

from analytics import (
    build_salary_records,
    clear_salary_cache,
    load_salary_records,
    parse_cv,
    recommend_upgrades,
    salary_stats,
)
from analytics.salary_records import (
    map_survey_english,
    map_survey_language,
    parse_experience_years,
    parse_survey_salary,
)


def test_salary_record_parsers() -> None:
    assert parse_survey_salary("3000") == 3000.0
    assert parse_survey_salary(" 4 500 ") == 4500.0
    assert parse_survey_salary("0") is None
    assert parse_survey_salary("50") is None
    assert parse_survey_salary("50000") is None

    assert parse_experience_years("4 роки") == 4.0
    assert parse_experience_years("Півтора роки") == 1.5
    assert parse_experience_years("Пів року") == 0.5
    assert parse_experience_years("3 місяці") == 0.25
    assert parse_experience_years("15-20 років") == 17.5
    assert parse_experience_years("Понад 20 років") == 22.0
    assert parse_experience_years("-99") is None

    assert map_survey_language("C# / .NET") == "c#/.net"
    assert map_survey_language("Мови розробки БД (PL/SQL, Transact-SQL)") == "sql"
    assert map_survey_language("Bash / Shell") == "bash"
    assert map_survey_language("не використовую") is None

    assert map_survey_english("Upper-Intermediate") == "upper"
    assert map_survey_english("Advanced") == "fluent"
    assert map_survey_english("Не знаю взагалі") == "none"


def test_salary_records_build_and_process_once(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_salary_cache()
    df = load_salary_records()
    assert len(df) >= 20000
    assert df["salary_usd"].notna().all()
    assert (df["salary_usd"] >= 100.0).all()

    calls = 0
    orig_read_parquet = pd.read_parquet

    def counting_read_parquet(*args, **kwargs):
        nonlocal calls
        calls += 1
        return orig_read_parquet(*args, **kwargs)

    monkeypatch.setattr(pd, "read_parquet", counting_read_parquet)
    # Subsequent access hits in-memory cache without re-reading raw wave shards.
    df2 = load_salary_records()
    assert len(df2) == len(df)
    assert calls == 0
    df3 = build_salary_records(force=False)
    assert len(df3) == len(df)
    assert calls == 0


@pytest.mark.parametrize(
    ("position", "skills", "experience"),
    [
        ("Python", ["python", "django", "docker"], 3.0),
        ("QA", ["qa"], 2.0),
        ("Front End", ["typescript", "react"], 1.5),
        ("DevOps", ["devops", "aws"], 4.0),
        ("SAP", ["sap"], 5.0),
        ("Blockchain", ["blockchain"], 3.0),
        ("", [], None),
    ],
)
def test_salary_stats_all_profiles_and_widening(position: str, skills: list[str], experience: float | None) -> None:
    stats = salary_stats(position, skills, experience)
    assert stats["basis"] == "survey"
    assert stats["count"] >= 30
    assert stats["p25"] <= stats["median"] <= stats["p75"]
    assert sum(b["count"] for b in stats["histogram"]) == stats["count"]
    if position in {"SAP", "Blockchain", ""}:
        assert stats["filters"]["widened"] is True


@pytest.mark.parametrize(
    ("position", "skills"),
    [
        ("Python", ["python", "django"]),
        ("QA", ["qa"]),
        ("Front End", ["javascript", "react"]),
        ("Analyst", ["data analysis", "sql"]),
        ("Architect", ["architecture"]),
        ("", []),
    ],
)
def test_recommend_upgrades_for_any_profile(position: str, skills: list[str]) -> None:
    recs = recommend_upgrades(position, skills, top_n=5)
    assert len(recs) == 5
    user_set = {s.lower() for s in skills}
    for rec in recs:
        assert rec["skill"] not in user_set
        assert rec["sample_size"] >= 30
        assert rec["salary_gain_usd"] >= 0.0
        assert rec["new_jobs_count"] >= 0


def test_parse_cv_three_realistic_resumes() -> None:
    cv_python = """
    Oleksii Kovalenko — Senior Python Backend Engineer
    Experience: 4.5 years building APIs with Python, FastAPI, Django, PostgreSQL, Redis, Docker, and AWS.
    Worked closely with Product Manager and QA teams.
    English: Upper-Intermediate (B2).
    """
    res1 = parse_cv(cv_python)
    assert res1["detected_position"] == "Python"
    assert {"python", "fastapi", "django", "postgresql", "redis", "docker", "aws"} <= set(res1["detected_skills"])
    assert res1["detected_experience_years"] == 4.5
    assert res1["detected_english_level"] == "upper"

    cv_qa = """
    Ірина Мельник
    QA Automation Engineer (SDET)
    Досвід: 2023 – дотепер, автоматизація веб-тестування на Playwright, Python, Git, CI/CD.
    Англійська: середній рівень (Intermediate).
    """
    res2 = parse_cv(cv_qa)
    assert res2["detected_position"] == "QA"
    assert {"qa", "automation qa", "playwright", "python", "git", "ci/cd"} <= set(res2["detected_skills"])
    assert res2["detected_experience_years"] >= 3.0
    assert res2["detected_english_level"] == "intermediate"

    cv_analyst = """
    Maksym Savchenko
    Data Analyst / BI Specialist (3+ years)
    Skills: SQL, Power BI, Tableau, Excel, Python.
    English: Fluent (C1/C2).
    """
    res3 = parse_cv(cv_analyst)
    assert res3["detected_position"] == "Analyst"
    assert {"data analysis", "sql", "power bi", "tableau", "excel", "python"} <= set(res3["detected_skills"])
    assert res3["detected_experience_years"] == 3.0
    assert res3["detected_english_level"] == "fluent"

    empty_res = parse_cv("")
    assert empty_res["detected_skills"] == []
    assert len(empty_res["warnings"]) > 0
