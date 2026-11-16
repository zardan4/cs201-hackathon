# AGENTS.md — Rules for AI agents working in this repository

Read this file before doing any work. These rules come from the hackathon criteria and override any default behavior.

## Project context

Python hackathon on the topic **Open Data** (16 November, 16:30 Kyiv time). Max 15 points. The project idea is not defined yet; do not invent or assume one.

## Hard rules (violating any = 0 points for the team)

1. **Python is the main language.** All core logic (data loading, processing, calculations, application logic) must be in Python. Only **HTML (and CSS)** is allowed as an auxiliary language, for rendering the website. No JavaScript-based business logic, no other languages for core logic.
2. **Open data only.** The project must be built on data from an open source (e.g. data.gov.ua, kaggle.com/datasets, ourworldindata.org, data.worldbank.org, data.europa.eu, datasetsearch.research.google.com, or open APIs/scrapers). Always record the source and license of every dataset.
3. **Repository content before the hackathon start (16:30 Kyiv):** only the `data` folder may exist. No code or other files outside `data` before the start.
4. **⛔ Commit deadline: do NOT commit or push anything after 20:15 Kyiv time on 16 November.** Check the time before every commit. If it is past 20:15, stop and tell the user.

## Code quality rules (scored 0–4)

- Split code into functions and modules; no long "spaghetti" scripts, no copy-paste repetition.
- Use clear, descriptive names.
- Use Python libraries appropriately (pandas, matplotlib, etc.).
- Add short docstrings/comments where logic is not obvious.
- Keep a `requirements.txt` and a simple one-command way to run the app.

## Working program rules (scored 0–6)

- The program must start without errors and do what is claimed during the demo.
- Prefer a small, stable, finished feature set over a big unfinished one.
- Test the demo path end-to-end before the deadline.

## Git rules (scored 0–1)

- Commits must come from **different team members** (3–5 people). Do not squash everything into one author.
- Commit small and often, with clear messages.
- Never add `Co-Authored-By` or any AI attribution lines to commits.
- Never rewrite history or force-push.
- Stop committing at 20:15 Kyiv time.

## Demo rules (scored 0–1)

- The demo must fit in **1–2 minutes**; significantly longer = −1 point.
- Keep the app easy to show: one clear flow, ready sample data.

## AI usage

Using AI is allowed and does not lower the score, but **every team member must be able to explain how the code works** when asked. Write simple, understandable code and explain non-obvious decisions.
