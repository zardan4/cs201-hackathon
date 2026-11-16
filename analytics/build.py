"""CLI entry point to pre-build all analytics cache tables (DA8)."""

from __future__ import annotations

import argparse

from analytics.jobs import build_jobs
from analytics.salary_records import build_salary_records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SwipeJob analytics cache tables.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild cache parquet files even if they already exist.",
    )
    args = parser.parse_args(argv)

    jobs_df = build_jobs(force=args.force)
    total = len(jobs_df)
    salary_valid = int(jobs_df["salary_mid"].notna().sum())
    salary_raw = int(jobs_df["salary_text"].notna().sum())
    outliers_filtered = salary_raw - salary_valid
    with_skills = int(jobs_df["skills"].apply(lambda s: len(s) > 0).sum())
    with_tags = int(jobs_df["tags"].apply(lambda t: len(t) > 0).sum())
    remote_count = int(jobs_df["is_remote"].sum())
    unique_cats = len({c for cats in jobs_df["categories"] for c in cats})

    print(f"Built cache/jobs.parquet: {total} vacancies, {unique_cats} categories")
    print(f"  Remote-friendly: {remote_count}/{total} ({remote_count / total * 100:.1f}%)")
    print(f"  With skills:     {with_skills}/{total} ({with_skills / total * 100:.1f}%)")
    print(f"  With tags:       {with_tags}/{total} ({with_tags / total * 100:.1f}%)")
    print(f"  Valid salaries:  {salary_valid}/{total} ({salary_valid / total * 100:.1f}%), outliers filtered: {outliers_filtered}")

    salary_df = build_salary_records(force=args.force)
    surveys = ", ".join(f"{k}={v}" for k, v in salary_df["survey"].value_counts().items())
    print(f"Built cache/salary_records.parquet: {len(salary_df)} records ({surveys})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
