# `analytics` — Library Documentation

The `analytics` package is BlowMyJob's pure-Python data-access, normalization, skill-extraction, and job-ranking library. It reads open data from [`data/`](file:///home/artiekra/personal/kse/cs201-hackathon/data/), caches normalized tables in `cache/`, and exposes generator-based and DataFrame APIs for the web service layer (`app/services/`).

---

## 1. Process-Once Caching Lifecycle

Reading and parsing [`data/dou_active_vacancies.csv`](file:///home/artiekra/personal/kse/cs201-hackathon/data/dou_active_vacancies.csv) happens **only once**:

1. **First access** (`load_jobs()`, `iter_jobs()`, `iter_ranked_jobs()`, or `rank_jobs()`):
   - Checks the in-memory process cache.
   - If empty, checks whether `cache/jobs.parquet` exists on disk.
   - If `cache/jobs.parquet` does not exist yet, parses the CSV once, normalizes salaries/locations/categories/skills/tags, and atomically writes `cache/jobs.parquet` (`tmp` + `os.replace`).
2. **All subsequent calls** read directly from in-memory records or `cache/jobs.parquet` without re-parsing the CSV or re-running regex extraction.
3. **Explicit rebuild:** pass `force=True` to `build_jobs(force=True)`, `refresh=True` to `load_jobs(refresh=True)`, or run:

```bash
python -m analytics.build --force
```

---

## 2. Quickstart

### Stream filtered vacancies (`yield`)

```python
from analytics import iter_jobs

for job in iter_jobs(
    categories=["Python", "AI/ML"],
    locations=["Київ"],
    remote_only=False,
    min_salary=1500,
):
    print(job["id"], job["title"], job["salary_mid"], job["skills"], job["tags"])
```

### Stream best-to-worst ranked matches (`yield`)

```python
from analytics import iter_ranked_jobs

for match in iter_ranked_jobs(
    position="Python",
    skills=["python", "django", "docker", "postgresql"],
    categories=["Python", "AI/ML"],
    locations=["Київ", "віддалено"],
    exclude_ids={"380099"},
):
    job = match["job"]
    print(f"[{match['score']:.2f}] {job['title']} ({match['reason']})")
    print("  matched:", match["matched_skills"], "| missing:", match["missing_skills"])
```

### Contract list interface (`app/services/jobs_service.py`)

```python
from analytics import rank_jobs

top_matches = rank_jobs(
    position="Python",
    skills=["python", "fastapi", "docker"],
    exclude_ids={"380099"},
    remote_only=True,
    limit=20,
)
```

---

## 3. API Reference

### `analytics.jobs`

- **`load_jobs(refresh: bool = False, require_salary: bool | None = None) -> pandas.DataFrame`**
  Returns the normalized vacancies DataFrame with columns defined in [`docs/CONTRACTS.md`](file:///home/artiekra/personal/kse/cs201-hackathon/docs/CONTRACTS.md) §2.1 (`id`, `title`, `company`, `locations`, `is_remote`, `salary_text`, `salary_min`, `salary_max`, `salary_mid`, `categories`, `skills`, `tags`, `snippet`, `url`, `posted_at`). Builds `cache/jobs.parquet` lazily on first access. When `require_salary` is `None`, follows `SWIPE_REQUIRES_SALARY` from [`analytics/config.py`](file:///home/artiekra/personal/kse/cs201-hackathon/analytics/config.py) (default `True` → salaried vacancies only; pass `require_salary=False` to access all 3,512 vacancies).
- **`build_jobs(force: bool = False) -> pandas.DataFrame`**
  Reads `cache/jobs.parquet` if present (unless `force=True`), otherwise builds and persists it atomically.
- **`iter_jobs(categories=None, locations=None, remote_only=False, exclude_ids=None, min_salary=None, skills=None, tags=None, require_salary=False) -> Iterator[dict]`**
  Lazily yields normalized `Job` dictionaries matching all supplied filters:
  - `categories`: case-insensitive any-overlap against `job["categories"]`.
  - `locations`: case-insensitive substring match against `job["locations"]` (passing `"remote"` or `"віддалено"` also matches `job["is_remote"]`).
  - `remote_only`: keeps only `is_remote == True`.
  - `exclude_ids`: skips any job whose `id` is in the set.
  - `min_salary`: keeps jobs where `salary_mid is not None and salary_mid >= min_salary`.
  - `skills` / `tags`: optional any-overlap hard filters.
  - `require_salary`: if `True`, keeps only jobs with `salary_mid is not None`.
- **`clear_cache() -> None`**
  Clears in-memory caches without deleting `cache/jobs.parquet`.
- **Pure parsers:** `extract_job_id(link)`, `parse_salary(salary_text)`, `parse_locations(location_text)`, `parse_categories(categories_text)`.

### `analytics.skills`

- **`all_skills() -> list[dict]`**
  Loads canonical skill definitions from [`analytics/skills_catalog.json`](file:///home/artiekra/personal/kse/cs201-hackathon/analytics/skills_catalog.json) (`{"name", "aliases", "group"}`).
- **`all_positions() -> list[str]`**
  Returns sorted DOU category/position strings from the vacancies dataset.
- **`extract_skills(text: str) -> list[str]`**
  Extracts deduplicated canonical lowercase skills from arbitrary text using boundary-safe regexes (handles `.net`, `c++`, `c#`, `node.js`, `ci/cd`, Ukrainian aliases, and guards ambiguous tokens like `Go`, `C`, `Java` vs `JavaScript`, `React` vs `React Native`).
- **`extract_job_skills(title: str, snippet: str, categories: list[str]) -> list[str]`**
  Combines `extract_skills(title + snippet)` with unambiguous category mappings (e.g., `Java` -> `java`, `Node.js` -> `node.js`, `.NET` -> `c#/.net`, `DevOps` -> `devops`) and context-aware `Analyst` / `Design` rules.
- **`extract_tags(title: str, snippet: str = "", location_text: str = "") -> list[str]`**
  Extracts secondary non-skill tags kept separate from `Job.skills`:
  - Seniority: `trainee`, `junior`, `middle`, `senior`, `lead`, `c-level`
  - Format: `part-time`, `hybrid`
  - Domain: `miltech`, `fintech`, `igaming`, `gamedev`, `saas`, `b2b`, `edtech`, `ecommerce`, `healthcare`

### `analytics.matching`

- **`iter_ranked_jobs(position="", skills=(), exclude_ids=None, *, categories=None, locations=None, remote_only=False, min_salary=None, tags=None, min_score=0.0, require_salary=None) -> Iterator[dict]`**
  Filters via `iter_jobs(...)` (respecting `SWIPE_REQUIRES_SALARY` when `require_salary is None`), scores every candidate, and yields `JobMatch` dicts (`job`, `score`, `matched_skills`, `missing_skills`, `reason`) ordered strictly **best-to-worst**.
- **`rank_jobs(position, skills, exclude_ids, remote_only=False, limit=50, *, categories=None, locations=None, min_salary=None, tags=None, min_score=0.0, require_salary=None) -> list[dict]`**
  Returns the top `limit` items from `iter_ranked_jobs(...)` matching [`docs/CONTRACTS.md`](file:///home/artiekra/personal/kse/cs201-hackathon/docs/CONTRACTS.md) §4.1.
- **`score_job(job, position="", user_skills=frozenset(), target_categories=frozenset(), target_tags=frozenset()) -> tuple[float, list[str], list[str], str]`**
  Computes the match score for a single job.

### DOU Salary Surveys, Upgrades & CV Parsing (`DA3`, `DA5`, `DA6`, `DA7`)

- **`analytics.salary_records`**: `build_salary_records(force=False)` & `load_salary_records(refresh=False)` normalize `2026_june_raw`, `2025_dec_raw`, and `2025_june_raw` (`38,535` rows) into `cache/salary_records.parquet` lazily (process-once).
- **`analytics.salary`**: `salary_stats(position, skills, experience_years=None)` computes `median`, `mean`, `p25`, `p75`, `count`, `basis="survey"`, `filters` (with `widened: bool` & `mode`), and `histogram` strictly from DOU survey records, automatically widening filters when `count < 30`.
- **`analytics.upgrade`**: `recommend_upgrades(position, skills, top_n=5)` computes missing-skill salary gains (`sample_size >= 30`, checking within-position survey cohorts first) and counts newly unlocked salaried jobs crossing `0.65` match score in `load_jobs()`.
- **`analytics.cv`**: `parse_cv(text)` extracts `detected_position` (headline-first pattern matching + skill fallback), `detected_skills` (`extract_skills`), `detected_experience_years` (`N years` / `N років` / year ranges), `detected_english_level` (`none..fluent` in EN/UK), and `warnings`.

---

## 4. Normalization, Outliers & Ranking Rules

- **Categories:** Split on `";"` (with `","` fallback) because DOU CSV multi-category strings use semicolons (e.g., `"Design; Hardware"`).
- **Locations & Remote:** `is_remote` is `True` when `"віддалено"` or `"remote"` appears anywhere in `location`. Pure remote markers (`"віддалено"`, `"remote"`, `"We're a fully remote team..."`) are removed from `locations`, and suffixes/prefixes like `"Poland (remote)"` or `"Remote Ukraine"` are normalized to `"Poland"` / `"Ukraine"`.
- **Salaries & Outliers:** Parses `"$X"`, `"$A–B"`, `"від $X"`, `"до $X"` into `(salary_min, salary_max, salary_mid)`. Preserves `salary_text`, while filtering out non-monthly outliers (`< $100` hourly rates or `> $30,000`) to `None`.
- **Match Scoring Formula:**
  - `skill_score = |user_skills ∩ job_skills| / |job_skills|` (or `0.0` if `job_skills` is empty)
  - `category_bonus = +0.20` when `position` or requested `categories` overlap `job["categories"]`
  - `tag_bonus = +0.05` when requested `tags` overlap `job["tags"]`
  - `score = min(1.0, 0.8 * skill_score + category_bonus + tag_bonus)`
  - **Tie-breakers:** `(score desc, matched_skills count desc, missing_skills count asc, posted_at desc, has_salary desc, id desc)`.

---

## 5. CLI & Testing

```bash
# Pre-build cache/jobs.parquet (or rebuild with --force)
python -m analytics.build
python -m analytics.build --force

# Run test suite
pytest -v tests/test_analytics_jobs.py
```
