# SwipeJob Flask skeleton

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
imports resolve to the DA's package. The skeleton needs neither datasets nor
`analytics.build` to start; real features will need the DA's modules and dependencies.

For automatic reload during development:

```bash
python -m flask --app app.main:create_app run --debug
```

Set `SWIPEJOB_SECRET_KEY` to a stable private value to keep cookie sessions valid
across server restarts. Otherwise each server startup generates a new key and
visitors receive new profiles. `PORT` changes the port for `python -m app.main`.
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
    │   ├── catalog_service.py    WE-A: A1 adapter skeleton
    │   ├── profile_service.py    WE-A: persistence + A3 import boundary
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

Each request supplies `g.profile` (`UserProfile`) and `session["user_id"]`.
The initial profile has an empty position; the root URL continues to redirect
to onboarding until a position is saved. While A1 is pending, `/swipe` can still
be opened directly, and services can be exercised using a constructed profile.

Use `app.storage.list_swipes(user_id)` for exclusion IDs and
`app.storage.append_swipe(SwipeAction(...))` to persist actions. Profile edits
preserve swipes, appending swipes preserves profile fields, and the first action
for each job wins. These functions require a Flask application context (already
present in route handlers). `jobs_service.saved_jobs(user_id)` must return
`list[Job]` for the profile page. Read analytics only through services.

## Current functionality

Working: application factory, navigation, shared dataclasses, UUID sessions,
profile persistence and swipe storage. Pages are placeholders: onboarding and
profile submissions and CV upload return HTTP 501; catalogue, CV and insights
service stubs raise `NotImplementedError`. No fabricated vacancies, matching or
salary statistics are included. Implement A1–A5 and B0–B5 against the contracts.
