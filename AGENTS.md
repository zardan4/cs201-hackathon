# AGENTS.md — Rules for AI agents working in this repository

Read this file before doing any work. These rules come from the hackathon criteria and override any default behavior.

## Project context

Python hackathon on the topic **Open Data** (16 November, 16:30–21:00 Kyiv time; work until 20:15, defense 20:15–21:00 online in Google Meet). Max 15 points. The most important factor is that the program really works during the demo. The project idea is **SwipeJob** — a Tinder/Badoo-style web app for IT job search (3 tabs: swipes, profile, insights/upgrade). **Read the `Ідея проєкту (UA)` section in `README.md` first**: it defines the idea, data sources, module contracts and the task breakdown (T0–T10).

## How to work on the project (for agents)

- Take exactly **one task** (T0–T10 from `README.md`) from the developer who runs you; edit **only that task's files**.
- Respect the module contracts in `README.md` (function names, DataFrame columns). Do not change a contract without telling the user.
- Data lives in `data/` (read-only for the app code). The DOU CSV has a BOM: read it with `encoding="utf-8-sig"`. Only ~16% of vacancies have a salary.
- Backend, matching, statistics and parsing: **Python only** (Flask + pandas). HTML/CSS for templates; JS only for the minimal swipe gesture, never for business logic.
- Applying to jobs / sending resumes is **out of scope**; "like" only saves the vacancy in the profile.
- Run `git pull --rebase` before starting and before each commit. Keep commits small.

## Hard rules (violating any = 0 points for the team)

1. **Python is the main language.** All core logic (data loading, processing, calculations, application logic) must be in Python. Only **HTML (and CSS)** is allowed as an auxiliary language, for rendering the website. No JavaScript-based business logic, no other languages for core logic.
2. **Open data only.** The project must be built on data from an open source (e.g. data.gov.ua, kaggle.com/datasets, ourworldindata.org, data.worldbank.org, data.europa.eu, datasetsearch.research.google.com, or open APIs/scrapers). Always record the source and license of every dataset.
3. **Repository content before the hackathon start (16:30 Kyiv):** only the `data` folder may exist. No code or other files outside `data` before the start.
4. **⛔ Commit deadline: do NOT commit or push anything after 20:15 Kyiv time on 16 November.** The repository is frozen at 20:15; any later commit is **−5 points**. Check the time before every commit. If it is past 20:15, stop and tell the user.

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

- Demo time: the criteria say 1–2 minutes, the event slides say 3 minutes. Target **2 minutes, never over 3**; significantly longer = −1 point.
- After the demo there are ~2 minutes of questions: be ready to explain the code.
- Keep the app easy to show: one clear flow, ready sample data.

## AI usage

Using AI is allowed and does not lower the score, but **every team member must be able to explain how the code works** when asked. Write simple, understandable code and explain non-obvious decisions.
