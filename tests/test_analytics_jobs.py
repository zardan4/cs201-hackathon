"""Tests for analytics.jobs, analytics.skills, analytics.matching, and DA0 stubs."""

from __future__ import annotations

import inspect
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from analytics import (
    all_positions,
    all_skills,
    build_jobs,
    clear_cache,
    extract_job_id,
    extract_skills,
    extract_tags,
    iter_jobs,
    iter_ranked_jobs,
    load_jobs,
    parse_categories,
    parse_cv,
    parse_locations,
    parse_salary,
    rank_jobs,
    recommend_upgrades,
    salary_stats,
    vacancy_salary_stats,
)


def test_parse_salary_formats_and_outliers() -> None:
    assert parse_salary("$700") == (700, 700, 700)
    assert parse_salary("$560–1700") == (560, 1700, 1130)
    assert parse_salary("$1000-2000") == (1000, 2000, 1500)
    assert parse_salary("від $600") == (600, None, 600)
    assert parse_salary("до $2500") == (None, 2500, 2500)
    assert parse_salary("") == (None, None, None)
    assert parse_salary(None) == (None, None, None)

    # Hourly / extreme outliers filtered out
    assert parse_salary("$30") == (None, None, None)
    assert parse_salary("$20–25") == (None, None, None)
    assert parse_salary("$50000") == (None, None, None)
    # Valid trainee and C-level salaries remain intact
    assert parse_salary("$200–400") == (200, 400, 300)
    assert parse_salary("$10000–15000") == (10000, 15000, 12500)


def test_parse_locations_remote_and_cities() -> None:
    assert parse_locations("Київ, Львів, віддалено") == (["Київ", "Львів"], True)
    assert parse_locations("віддалено") == ([], True)
    assert parse_locations("Poland (remote), Remote Ukraine") == (["Poland", "Ukraine"], True)
    assert parse_locations("Київ (гібрид)") == (["Київ (гібрид)"], False)
    assert parse_locations("We're a fully remote team thus we do not have an office.") == ([], True)
    assert parse_locations("") == ([], False)


def test_parse_categories_and_id() -> None:
    assert parse_categories(".NET; Node.js; Python") == [".NET", "Node.js", "Python"]
    assert parse_categories("AI/ML; Design; AI/ML") == ["AI/ML", "Design"]
    assert parse_categories("") == []
    assert extract_job_id("https://jobs.dou.ua/companies/tov-is-siti/vacancies/380099/") == "380099"


def test_extract_skills_boundary_safety() -> None:
    assert extract_skills("Senior Python & Django developer with .NET, C++, C#, Node.js, PostgreSQL") == [
        "python",
        "c#/.net",
        "c++",
        "node.js",
        "django",
        "postgresql",
    ]
    # Guard against common substring false positives
    assert extract_skills("We are going to scale JavaScript and React Native apps") == [
        "javascript",
        "react native",
    ]
    assert "javascript" not in extract_skills("Backend Node.js and Next.js engineer")
    assert "java" not in extract_skills("JavaScript developer")
    assert "go" not in extract_skills("We are going to build a company")
    assert "c" not in extract_skills("Company CRM architecture with R&D team")
    assert "c" in extract_skills("Flight Control Software Engineer (Embedded C)")


def test_extract_tags_seniority_and_domain() -> None:
    tags = extract_tags(
        "Senior Embedded Engineer (part-time)",
        "Developing autonomous FPV drones for miltech and fintech systems",
        "Київ (гібрид)",
    )
    assert "senior" in tags
    assert "part-time" in tags
    assert "hybrid" in tags
    assert "miltech" in tags
    assert "fintech" in tags


def test_process_once_caching_no_reprocessing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample_csv = tmp_path / "jobs.csv"
    sample_cache = tmp_path / "jobs.parquet"
    sample_csv.write_text(
        "\ufeffdate,title,company,location,salary,categories,link,snippet\n"
        '2026-11-16,Senior Python Engineer,Acme,"Київ, віддалено",$3000–4000,Python,https://jobs.dou.ua/companies/acme/vacancies/1001/,"Python, FastAPI, Docker, PostgreSQL"\n'
        '2026-11-15,Hourly Mentor,Edu,віддалено,$30,Python; AI/ML,https://jobs.dou.ua/companies/edu/vacancies/1002/,"Part-time mentor"\n',
        encoding="utf-8",
    )

    calls = 0
    orig_read_csv = pd.read_csv

    def counting_read_csv(*args, **kwargs):
        nonlocal calls
        calls += 1
        return orig_read_csv(*args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", counting_read_csv)

    # First access builds cache
    df1 = load_jobs(require_salary=False, csv_path=sample_csv, cache_path=sample_cache)
    assert calls == 1
    assert sample_cache.exists()
    assert len(df1) == 2

    # Second access reads cache without re-reading CSV
    df2 = load_jobs(require_salary=False, csv_path=sample_csv, cache_path=sample_cache)
    assert calls == 1
    assert len(df2) == 2

    # Subsequent build_jobs(force=False) also skips CSV
    df3 = build_jobs(csv_path=sample_csv, cache_path=sample_cache, force=False)
    assert calls == 1
    assert len(df3) == 2

    # Default require_salary=True returns only valid monthly salaried row
    df_sal = load_jobs(csv_path=sample_csv, cache_path=sample_cache)
    assert len(df_sal) == 1
    assert df_sal.iloc[0]["id"] == "1001"

    # Outlier "$30" keeps salary_text but drops numeric salary_mid
    row_outlier = df3[df3["id"] == "1002"].iloc[0]
    assert row_outlier["salary_text"] == "$30"
    assert pd.isna(row_outlier["salary_mid"])


def test_generators_filters_and_best_to_worst_ranking() -> None:
    clear_cache()
    gen_jobs = iter_jobs(categories=["Python"], remote_only=True)
    assert inspect.isgenerator(gen_jobs)
    python_remote = list(gen_jobs)
    assert len(python_remote) > 0
    assert all("Python" in j["categories"] and j["is_remote"] for j in python_remote)
    assert all(isinstance(j["posted_at"], date) for j in python_remote[:5])

    kyiv_jobs = list(iter_jobs(locations=["Київ"]))
    assert len(kyiv_jobs) > 100
    assert all(any("київ" in loc.lower() for loc in j["locations"]) for j in kyiv_jobs[:20])

    ranked_gen = iter_ranked_jobs(
        position="Python",
        skills=["python", "django", "docker", "postgresql"],
        exclude_ids={"380099"},
        categories=["Python", "AI/ML"],
        locations=["Київ"],
    )
    assert inspect.isgenerator(ranked_gen)
    ranked = list(ranked_gen)
    assert len(ranked) > 0
    assert all("380099" != m["job"]["id"] for m in ranked)
    assert all(m["job"]["salary_mid"] is not None for m in ranked)
    scores = [m["score"] for m in ranked]
    assert scores == sorted(scores, reverse=True)

    # Unfiltered (require_salary=False) exposes full active pool
    ranked_all = list(
        iter_ranked_jobs(
            position="Python",
            skills=["python", "django", "docker", "postgresql"],
            exclude_ids={"380099"},
            categories=["Python", "AI/ML"],
            locations=["Київ"],
            require_salary=False,
        )
    )
    assert len(ranked_all) > len(ranked)

    # Verify rank_jobs wrapper matches contract
    top5 = rank_jobs(
        position="Python",
        skills=["python", "django", "docker", "postgresql"],
        exclude_ids={"380099"},
        remote_only=False,
        limit=5,
        categories=["Python", "AI/ML"],
        locations=["Київ"],
    )
    assert len(top5) == min(5, len(ranked))
    assert top5 == ranked[:5]


def test_full_dataset_coverage_and_catalog() -> None:
    df_all = load_jobs(require_salary=False)
    assert len(df_all) == 3512
    assert df_all["id"].nunique() == 3512
    with_skills_ratio = float(df_all["skills"].apply(lambda s: len(s) > 0).mean())
    assert with_skills_ratio >= 0.80

    df_salaried = load_jobs()
    assert len(df_salaried) == 545
    assert df_salaried["salary_mid"].notna().all()

    assert len(all_positions()) == 43
    assert len(all_skills()) >= 60


def test_da0_stubs_contract_shapes() -> None:
    stats = salary_stats("Python", ["python"], 3.0)
    assert {"median", "mean", "p25", "p75", "count", "basis", "filters", "histogram"} <= stats.keys()

    vac_stats = vacancy_salary_stats("Python", ["python"])
    assert vac_stats is not None
    assert vac_stats["basis"] == "vacancies"
    assert vac_stats["count"] > 0

    upgrades = recommend_upgrades("Python", ["python"], top_n=3)
    assert len(upgrades) == 3
    assert {"skill", "salary_gain_usd", "salary_gain_pct", "new_jobs_count", "example_job_ids", "sample_size"} <= upgrades[0].keys()

    cv = parse_cv("Senior Python Engineer, 4 years experience, Upper-Intermediate English, FastAPI, Docker")
    assert "python" in cv["detected_skills"]
    assert "fastapi" in cv["detected_skills"]
    assert cv["detected_experience_years"] == 4.0
    assert cv["detected_english_level"] == "upper"
