# Python Open Data Hackathon — Rules

Event: KSE · CS201 Programming — Python hackathon on the topic **Open Data**, 16 November, 16:30–21:00 (Kyiv time).
Maximum score: **15 points**. 34 teams, 5 groups. The most important thing: the program must actually work during the demo.

> Project idea: TBD (not defined yet).

## Mandatory requirements

If either requirement is not met, the team gets **0 points**.

1. **Python is the main language.** All core logic (data processing, calculations, application logic) is written in Python. Other languages are allowed only as auxiliary ones. In this project: **Python only, plus HTML (and CSS) for rendering the website.**
2. **The project uses open data.** The data comes from an open source and is the foundation of the project.

## Format

- Teams of 3 to 5 people (no fewer, no more). Members may come from different groups.
- Work time: **16:30 – 20:15** (3 h 45 min). Defense: **20:15 – 21:00**.
- Defense: a short demo of the working program (see Demo below), then questions.
- Hybrid format: you can work from anywhere, but commit on time.
- Defense is online: each group defends in its own Google Meet (links are sent separately).
- Using AI is allowed. It does not lower the score, but **every team member must be able to explain how the code works** if asked during the defense.
- Data can be found e.g. on data.gov.ua, kaggle.com/datasets, ourworldindata.org, data.worldbank.org, data.europa.eu, datasetsearch.research.google.com. APIs and web scrapers are also allowed.

## Scoring

| Criterion | What is evaluated | Points |
|---|---|---|
| Working program | Runs and does what is claimed during the demo, without errors | 0–6 |
| Python code quality | Readable, structured code (functions, clear names), proper use of Python and its libraries | 0–4 |
| Idea and usefulness | How interesting and original the idea is, how useful the result is | 0–3 |
| Teamwork in Git | Commits made during the hackathon by different team members | 0–1 |
| Demo | Fits in 1–2 minutes and clearly shows what was done | 0–1 |
| **Total** | | **15** |

### Working program (0–6)
- 6: everything works stably, functionality is complete.
- 4–5: main part works, minor glitches or something unfinished.
- 2–3: works only partially, or the demo has errors.
- 1: starts, but does almost nothing.
- 0: does not start.

### Python code quality (0–4)
- 4: clean code split into functions or modules, libraries used appropriately (pandas, matplotlib, etc.).
- 3: well organized, minor flaws.
- 2: generally understandable, but has repetition or "spaghetti" code.
- 1: hard to read.

### Idea and usefulness (0–3)
- 3: original idea with a useful or interesting result.
- 2: good idea, but fairly standard.
- 1: simple idea, result has little substance.

## Disqualification (0 points for the whole hackathon)

- Mandatory requirements are not met.
- The repository contains code or anything other than the `data` folder **before the hackathon starts**.
- The team did not register by 14 November.

**Penalty −1 point:** the demo lasts significantly longer than the time limit (see Demo).

**Penalty −5 points:** any commit after 20:15 (the repository is frozen at 20:15).

## Demo and timings

- Time per team: 3 min demo + 2 min answers + 1 min reserve = 6 min. 7 teams per group = 42 of 45 min.
- The criteria document says the demo should be 1–2 minutes; the event slides say 3 minutes. **Plan for 2 minutes, never exceed 3.**
- Show clearly what was done and how it works. Every team member must be able to explain their code.

## ⛔ Commit deadline

**No commits may be pushed to the repository after 20:15 Kyiv time (16 November). The repository is frozen at 20:15; a commit after that costs −5 points.**

## Repository rules

- Public GitHub repository.
- Before the start only the `data` folder (with project data, if needed) may exist. Code is written during the hackathon.
- Commits must be made by **different team members** (Teamwork in Git criterion).
