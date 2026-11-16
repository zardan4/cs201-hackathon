"""CLI entry point to pre-build analytics cache artifacts."""

from __future__ import annotations

import argparse

from analytics.jobs import build_jobs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SwipeJob analytics cache tables.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild cache/jobs.parquet even if it already exists.",
    )
    args = parser.parse_args(argv)

    df = build_jobs(force=args.force)
    total = len(df)
    salary_valid = int(df["salary_mid"].notna().sum())
    salary_raw = int(df["salary_text"].notna().sum())
    outliers_filtered = salary_raw - salary_valid
    with_skills = int(df["skills"].apply(lambda s: len(s) > 0).sum())
    with_tags = int(df["tags"].apply(lambda t: len(t) > 0).sum())
    remote_count = int(df["is_remote"].sum())
    unique_cats = len({c for cats in df["categories"] for c in cats})

    print(f"Built cache/jobs.parquet: {total} vacancies, {unique_cats} categories")
    print(f"  Remote-friendly: {remote_count}/{total} ({remote_count / total * 100:.1f}%)")
    print(f"  With skills:     {with_skills}/{total} ({with_skills / total * 100:.1f}%)")
    print(f"  With tags:       {with_tags}/{total} ({with_tags / total * 100:.1f}%)")
    print(f"  Valid salaries:  {salary_valid}/{total} ({salary_valid / total * 100:.1f}%), outliers filtered: {outliers_filtered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
