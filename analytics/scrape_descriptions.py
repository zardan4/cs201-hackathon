"""One-time scraper for full DOU vacancy descriptions (DA task).

The active-vacancy CSV only carries a short listing snippet (~18-292 chars), so
skill extraction sees very little text. This script opens every vacancy link
once, extracts the full ``b-typo vacancy-section`` description and stores it as
JSONL in ``data/dou_vacancy_details/``. ``analytics.jobs`` then extracts
skills from that full text as well.

Run from the repository root:

    python -m analytics.scrape_descriptions              # resume / fill gaps
    python -m analytics.scrape_descriptions --force      # re-scrape all rows
    python -m analytics.scrape_descriptions --limit 20   # smoke test

The run is resumable: rows already present in the JSONL file are skipped, so a
network hiccup costs nothing. Failed rows are reported and picked up next run.
"""

from __future__ import annotations

import argparse
import gzip
import html
import lzma
import json
import random
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd

from analytics.jobs import DEFAULT_CSV_PATH, extract_job_id

ANALYTICS_DIR = Path(__file__).resolve().parent
ROOT_DIR = ANALYTICS_DIR.parent
DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "dou_vacancy_details" / "scraped.jsonl.xz"

USER_AGENT = "SwipeJobHackathon/1.0 (educational data collection; Kyiv hackathon project)"
REQUEST_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3

_DESCRIPTION_OPEN_RE = re.compile(
    r'<div[^>]*class=["\'][^"\']*\bb-typo\b[^"\']*\bvacancy-section\b[^"\']*["\'][^>]*>',
    re.IGNORECASE,
)
_DIV_TOKEN_RE = re.compile(r"<div\b|</div\s*>", re.IGNORECASE)
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_BLOCK_END_RE = re.compile(
    r"</(?:p|li|ul|ol|div|h[1-6]|tr|table|section|blockquote)\s*>|<br\s*/?>",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")
_INLINE_WS_RE = re.compile(r"[ \t\u00a0]+")


class PermanentFetchError(Exception):
    """The page is gone (404/410); retrying will not help."""


def extract_description(page_html: str) -> str:
    """Return the vacancy description as plain text, or ``""`` if not found."""
    match = _DESCRIPTION_OPEN_RE.search(page_html)
    if not match:
        return ""

    body_start = match.end()
    depth = 1
    body_end = len(page_html)
    for token in _DIV_TOKEN_RE.finditer(page_html, body_start):
        depth += 1 if token.group(0).lower().startswith("<div") else -1
        if depth == 0:
            body_end = token.start()
            break

    fragment = _SCRIPT_STYLE_RE.sub(" ", page_html[body_start:body_end])
    fragment = _BLOCK_END_RE.sub("\n", fragment)
    fragment = _TAG_RE.sub("", fragment)
    text = html.unescape(fragment)

    lines = []
    for raw_line in text.split("\n"):
        line = _INLINE_WS_RE.sub(" ", raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def fetch_page(url: str) -> str:
    """Download a vacancy page with retries for transient network errors."""
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 410):
                raise PermanentFetchError(f"HTTP {exc.code}") from exc
            last_error = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        if attempt < MAX_ATTEMPTS:
            time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"failed after {MAX_ATTEMPTS} attempts: {last_error}")


def scrape_vacancy(url: str) -> str:
    """Fetch one vacancy page and return its cleaned description text."""
    description = extract_description(fetch_page(url))
    if not description:
        raise ValueError("no vacancy-section found")
    return description


def _open_text(path: Path, mode: str):
    """Open plain or gzip-compressed JSONL transparently."""
    if path.suffix == ".xz":
        return lzma.open(path, mode, encoding="utf-8")
    if path.suffix == ".gz":
        return gzip.open(path, mode, encoding="utf-8")
    return path.open(mode, encoding="utf-8")


def load_existing_ids(output_path: Path) -> set[str]:
    """Read IDs already scraped into the JSONL (.jsonl or .jsonl.gz) file."""
    if not output_path.exists():
        return set()
    ids: set[str] = set()
    with _open_text(output_path, "rt") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(str(json.loads(line)["id"]))
            except (json.JSONDecodeError, KeyError):
                continue
    return ids


def load_vacancy_links(csv_path: Path) -> list[tuple[str, str]]:
    """Return ``(vacancy_id, link)`` pairs from the active-vacancy CSV."""
    raw_df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for link in raw_df.get("link", []):
        link = str(link).strip()
        if not link:
            continue
        vacancy_id = extract_job_id(link)
        if vacancy_id in seen:
            continue
        seen.add(vacancy_id)
        pairs.append((vacancy_id, link))
    return pairs


def _sort_jsonl(path: Path) -> None:
    """Rewrite the JSONL file sorted by vacancy ID (stable, review-friendly)."""
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    rows.sort(key=lambda row: str(row["id"]))
    with _open_text(path, "wt") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def scrape_all(
    csv_path: Path = DEFAULT_CSV_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    force: bool = False,
    workers: int = 4,
    delay: float = 0.25,
    limit: int | None = None,
) -> dict[str, int]:
    """Scrape missing vacancy descriptions into ``output_path``.

    Returns counts: ``scraped``, ``skipped``, ``failed`` and ``total`` rows now
    present in the output file.
    """
    links = load_vacancy_links(csv_path)
    existing = set() if force else load_existing_ids(output_path)
    pending = [(vid, link) for vid, link in links if vid not in existing]
    if limit is not None:
        pending = pending[:limit]

    print(f"Vacancies: {len(links)}, already scraped: {len(existing)}, to fetch: {len(pending)}")

    scraped = 0
    failures: list[tuple[str, str]] = []
    output_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    with _open_text(output_path, "at") as out:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {pool.submit(scrape_vacancy, link): (vid, link) for vid, link in pending}
            for done, future in enumerate(as_completed(futures), start=1):
                vacancy_id, link = futures[future]
                try:
                    description = future.result()
                except Exception as exc:  # noqa: BLE001 - report and keep going
                    failures.append((vacancy_id, f"{type(exc).__name__}: {exc}"))
                else:
                    out.write(
                        json.dumps(
                            {
                                "id": vacancy_id,
                                "url": link,
                                "scraped_at": date.today().isoformat(),
                                "description": description,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    out.flush()
                    scraped += 1
                time.sleep(random.uniform(delay * 0.5, delay * 1.5))
                if done % 100 == 0 or done == len(pending):
                    elapsed = time.monotonic() - started
                    rate = done / elapsed if elapsed else 0.0
                    print(f"  {done}/{len(pending)} fetched ({rate:.1f}/s), failures: {len(failures)}")

    _sort_jsonl(output_path)
    total = len(load_existing_ids(output_path))
    try:
        shown_path = output_path.resolve().relative_to(ROOT_DIR)
    except ValueError:
        shown_path = output_path
    print(f"Wrote {shown_path}: {total} descriptions total")
    if failures:
        print(f"Failed rows ({len(failures)}), rerun to retry:")
        for vacancy_id, reason in failures[:20]:
            print(f"  {vacancy_id}: {reason}")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")
    return {"scraped": scraped, "skipped": len(links) - len(pending), "failed": len(failures), "total": total}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape full DOU vacancy descriptions (one-time job).")
    parser.add_argument("--force", action="store_true", help="Re-scrape rows that already exist.")
    parser.add_argument("--limit", type=int, default=None, help="Fetch at most N missing rows (smoke test).")
    parser.add_argument("--workers", type=int, default=4, help="Parallel requests (keep it modest).")
    parser.add_argument("--delay", type=float, default=0.25, help="Base delay between requests per worker.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH, help="Source vacancy CSV.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Destination JSONL file.")
    args = parser.parse_args(argv)

    counts = scrape_all(
        csv_path=args.csv,
        output_path=args.output,
        force=args.force,
        workers=args.workers,
        delay=args.delay,
        limit=args.limit,
    )
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
