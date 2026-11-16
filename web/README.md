# BlowMyJob Flask app

Python 3.11+. Run these commands from the repository root:

```bash
python -m venv web/.venv
source web/.venv/bin/activate
python -m pip install -r requirements.txt
python -m app.main
```

Open http://127.0.0.1:5000. Subsequent runs need only `python -m app.main` in the
activated environment. The editable installation exposes the `app` package while
keeping its source in `web/`. Run from the repository root so future `analytics.*`
imports resolve to the DA's package. CV analysis needs a Gemini API key and the
shared skills JSON catalogue. Matching and salary features need the DA's modules and dependencies.

Configure the server before uploading CVs:

```bash
# If .env does not already exist:
cp web/.env.example .env
```

Set `GEMINI_API_KEY` in that ignored root `.env` file or the server environment.
`GOOGLE_API_KEY` is also accepted. Never add a real key to source code or HTML.
`GEMINI_MODEL` selects the model (default `gemini-3.5-flash-lite`). The API key is sent
only in a server-to-Google request header; it is not included in the prompt,
browser, user JSON files or error messages.

The DA supplies `analytics/skills_catalog.json` with canonical skill names:

```json
[
  {"name": "python", "aliases": ["py"], "group": "language"},
  {"name": "django", "aliases": [], "group": "framework"},
  {"name": "sql", "aliases": [], "group": "language"}
]
```

A simple list such as `["python", "django", "sql"]` is also supported. The actual
file is authoritative for extraction, the profile's skill checkboxes and server
validation. Changes are read on the next request. Missing or invalid catalogues
prevent extraction; there is no fallback to a fabricated skill list or regex parser.

For automatic reload during development:

```bash
python -m flask --app app.main:create_app run --debug
```

Set `BLOWMYJOB_SECRET_KEY` to supply your own private signing key. Otherwise the
server generates and reuses a private key in ignored `cache/.session-key`, keeping
existing browser sessions valid across restarts. `PORT` changes the port for `python -m app.main`.
Runtime profiles and swipes live in the repository's ignored `cache/users/`.
The storage uses a lock within one process; use one server process for the demo.

## Structure and ownership

```text
web/
├── pyproject.toml
└── app/
    ├── main.py                   WE-A: factory, configuration, session setup
    ├── models.py                 WE-A: shared contract dataclasses
    ├── storage.py                WE-A: profile and swipe persistence
    ├── services/
    │   ├── catalog_service.py    WE-A: canonical skills JSON + DOU positions
    │   ├── profile_service.py    WE-A: Gemini extraction, validation, confirmation
    │   ├── insights_service.py   WE-A: A4–A5 skeleton
    │   └── jobs_service.py       WE-B creates this file
    ├── web/
    │   ├── __init__.py           shared swipe blueprint registration
    │   ├── profile.py            WE-A
    │   ├── insights.py           WE-A
    │   └── swipe.py              WE-B creates this file
    ├── templates/
    │   ├── base.html             shared layout
    │   ├── placeholder.html      temporary swipe page
    │   ├── onboarding/           WE-A
    │   ├── profile/              WE-A
    │   ├── insights/             WE-A
    │   └── swipe/                WE-B
    └── static/
        ├── profile/              WE-A, including shared base.css
        ├── insights/             WE-A
        └── swipe/                WE-B
```

Empty directories are not tracked by Git; create your first files at the paths
above. WE-B's implementation files are deliberately left for their owner.

## WE-B: start here

Create `web/app/web/swipe.py`:

```python
from flask import Blueprint, g, render_template

swipe_bp = Blueprint("swipe", __name__)


@swipe_bp.get("/swipe")
def index():
    # B0–B1: obtain matches through jobs_service.next_matches(g.profile).
    return render_template("swipe/index.html", profile=g.profile)
```

Create `web/app/templates/swipe/index.html`:

```html
{% extends "base.html" %}
{% block title %}Swipe{% endblock %}
{% block styles %}
<link rel="stylesheet" href="{{ url_for('static', filename='swipe/swipe.css') }}">
{% endblock %}
{% block content %}
<section class="panel"><h1>Your job feed</h1></section>
{% endblock %}
```

Add `web/app/static/swipe/swipe.css`, then restart the server. No changes to
`main.py`, shared models or navigation are needed. The application uses your
`swipe_bp` instead of the placeholder; errors in your module remain visible.
Add `/api/next-jobs` and `/api/swipe` to the same blueprint according to
[`../docs/CONTRACTS.md`](../docs/CONTRACTS.md). They are not present in the skeleton.

Each request supplies `g.profile` (`UserProfile`), `g.onboarding_complete` and
`session["user_id"]`. Until the user uploads a CV and confirms the review form,
direct page requests (including `/swipe`, `/profile`, `/insights`) redirect to
`/onboarding`, while `/api/*` requests return HTTP 403 with
`{"error": "onboarding_required", "redirect": "/onboarding"}`. This guard applies
automatically to WE-B's routes. Use the upload flow to create a profile for development.

Use `app.storage.list_swipes(user_id)` for exclusion IDs and
`app.storage.append_swipe(SwipeAction(...))` to persist actions. Profile edits
preserve swipes, appending swipes preserves profile fields, and the first action
for each job wins. These functions require a Flask application context (already
present in route handlers). `jobs_service.saved_jobs(user_id)` must return
`list[Job]` for the profile page. Read analytics only through services.

## CV onboarding

1. A new visitor opens `/` and is directed to `/onboarding`.
2. Upload a TXT or text-based PDF using `POST /profile/cv`. The request limit is
   5 MiB, PDFs may contain at most 30 pages, and extracted text at most 100,000
   characters. Empty, unreadable, password-protected or scanned documents show
   an error and leave the current profile/draft intact.
3. The server extracts file text locally, sends that text to Google Gemini, and
   validates the structured response against the catalogue before populating an
   editable form. Refreshing the page preserves the review draft.
4. Confirm a valid role, at least one skill, experience and English level.
   `POST /onboarding` stores the profile, clears the draft and opens `/profile`.
   Swipe and insights are now accessible. The profile page supports editing
   and uploading a replacement CV; an upload never replaces saved details until confirmed.

The cookie contains only the session user ID and temporary messages. Extracted CV
text, detected fields, confirmed profile and swipes remain in the session owner's
server-side `cache/users/<user_id>.json`. Original TXT/PDF files are not retained.
Form mutations use a CSRF token tied to that session; user IDs and completion flags
are never accepted from submitted fields. Access to a profile requires its browser
session; this demo has no login or recovery across browsers.

Gemini returns only role, canonical skills, experience, English level and review
warnings. The full skills catalogue is supplied in the prompt; Python enforces
catalogue membership, while JSON schema limits roles to DOU categories. A large
skill enum exceeds Gemini's schema branching limit. Python maps known skill aliases to
canonical names. Unknown skills are omitted with a warning, and missing details
remain editable. The saved `UserProfile.position` and `skills` can be passed
directly to `analytics.matching.rank_jobs` through WE-B's `jobs_service`.

Positions come from the DA's `all_positions()` API or a snapshot of the 43
categories in the provided DOU CSV. Multiple categories in the actual CSV are
separated by semicolons; adapters split on both semicolons and commas. The role
is `Golang`, for example, rather than an invented `Go` category. Web runtime does
not read raw datasets or call the previous regex CV parser.

The upload form discloses that CV text goes to Google Gemini. AI extraction can
be inaccurate; users can edit every field before saving and again in their profile.
Network, credentials, catalogue or provider failures show an error and preserve
the existing draft/profile. Requests time out after 30 seconds; invalid or
incomplete model responses are not saved. There are no automatic paid retries.

Provider reference: [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output).

Example TXT CV to exercise the flow:

```text
Python Developer
3 years of experience
Skills: Python, Django, SQL, PostgreSQL, Docker
English: B2
```

## DOU insights (A4–A5)

`/insights` uses the DA library exclusively through `insights_service`:

- `analytics.salary.salary_stats` supplies median, average, p25/p75, sample size,
  effective filters and distribution buckets from DOU salary surveys.
- `analytics.matching.iter_ranked_jobs` counts the entire set of salaried jobs at
  a match score of at least 65%, applying the profile's remote preference. Swiped
  jobs remain in this market count; it is independent of the swipe queue length.
- `analytics.upgrade.recommend_upgrades` provides up to five missing-skill
  comparisons with salary differences, newly reachable jobs and sample sizes.
- `/insights/salary-distribution.svg` renders the library's histogram using
  matplotlib, with an accessible distribution table on the page. The last
  bucket includes the upper tail and is labelled with a plus sign.

The page explains broadened cohorts, actual survey filters and sources. Upgrade
salary comparisons use all experience levels; upgrade job counts use all locations,
as defined by DA's API. They describe cohort associations, not guaranteed raises.
No survey responses or supported upgrades produce explicit empty states; unavailable
data produces a retry page. Both the page and chart require completed onboarding.
Profile edits affect the next request. No Gemini requests or raw dataset reads
are made by the insights web layer.
