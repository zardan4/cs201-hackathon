# Python Open Data Hackathon — Rules

Event: KSE · CS201 Programming — Python hackathon on the topic **Open Data**, 16 November, 16:30–21:00 (Kyiv time).
Maximum score: **15 points**. 34 teams, 5 groups. The most important thing: the program must actually work during the demo.

> Project idea: see the **Ідея проєкту (UA)** section below (SwipeJob). Hackathon rules are in English, the idea is in Ukrainian.

## 💡 Ідея проєкту (UA)

**Назва (робоча):** *SwipeJob* — «Tinder для IT-вакансій».

Веб-застосунок із інтерфейсом у стилі Tinder/Badoo: користувач вказує свою IT-позицію та навички, а система показує **лише відповідні йому актуальні вакансії** як картки, які можна свайпати. Додатково застосунок аналізує дані та показує, **скільки користувач може заробляти і які навички варто підкачати**, щоб заробляти більше.

Фокус — **IT-ринок України**. Вся логіка (обробка даних, матчинг, статистика, бекенд) — на **Python**; HTML/CSS — лише для відображення.

### Як це працює (користувацький сценарій)

1. Користувач відкриває сайт → **онбординг**: обирає IT-позицію (Python, QA, DevOps, Data, Design…) і відмічає свої навички (теги). *Додатково (stretch):* завантажує резюме (TXT/PDF), а ми самі витягуємо навички з тексту.
2. Система аналізує профіль: рахує очікувану зарплату та підбирає вакансії.
3. Застосунок із **3 вкладками** (зліва направо):
   - **Вкладка 1 — Свайпи.** Картки вакансій, які підходять користувачу (відсортовані за відповідністю). На картці: назва, компанія, зарплата (якщо вказана), локація / віддалено, необхідні навички, короткий опис, % збігу з профілем. **Свайп вліво / кнопка ✗** — не подобається. **Свайп вправо / кнопка ♥** — подобається, вакансія зберігається в профіль.
   - **Вкладка 2 — Профіль.** Позиція та навички користувача (можна редагувати) + список **збережених (вподобаних) вакансій** із посиланням на оригінал (`link`). Користувач сам подає заявки за посиланням — **автоматична відправка резюме/заявок поза скоупом проєкту**.
   - **Вкладка 3 — Інсайти / Апгрейд (дашборд).** Статистика «що я можу зі своїми навичками»: медіана та середня зарплата для моїх навичок, розподіл зарплат, кількість доступних вакансій; а також **рекомендації «що підкачати»**: які 1–3 навички дадуть найбільший приріст зарплати та відкриють найбільше нових вакансій.

### Основні функції (MVP vs. stretch)

| # | Функція | Пріоритет |
|---|---|---|
| F1 | Завантаження й очищення датасету вакансій (pandas) | MVP |
| F2 | Витягування навичок/категорії/формату (remote/office) з вакансій | MVP |
| F3 | Онбординг: вибір позиції та навичок | MVP |
| F4 | Матчинг: рейтинг вакансій під профіль користувача | MVP |
| F5 | Вкладка свайпів (ліво/право, збереження вподобаних) | MVP |
| F6 | Вкладка профілю + список вподобаних вакансій | MVP |
| F7 | Вкладка інсайтів: медіана/середня зарплата за навичками, графіки | MVP |
| F8 | Рекомендації «що підкачати» (приріст зарплати + нові вакансії) | MVP (спрощено) |
| F9 | Завантаження резюме та автоматичне витягування навичок | Stretch |
| F10 | Фільтри (remote, місто, мінімальна зарплата) | Stretch |

Якщо часу не вистачає — **вкладка 3 може бути простою (лише рекомендації), а F9/F10 відкладаються**. Пріоритет №1 — стабільно працююче демо (до 2 хвилин).

### Дані (open data)

Усі дані лежать у папці `data/` (див. `data/sources.json`):

| Джерело | Де | Що містить | Для чого |
|---|---|---|---|
| **DOU — актуальні вакансії** | `data/dou_active_vacancies.csv` | ~3 500 вакансій; колонки: `date, title, company, location, salary, categories, link, snippet` | **Основне джерело для свайпів** (актуальні вакансії) |
| **DOU salaries** | `data/datasets/devua-salaries/`, `data/raw/devua/` | Історичні опитування зарплат IT-спеціалістів | Статистика зарплат за навичками/позиціями |
| **Djinni recruitment dataset** (MIT) | `data/datasets/jobs-en`, `jobs-uk`, `candidates-en`, `candidates-uk`, `data/raw/djinni/` | ~140k+ описів вакансій та ~200k профілів кандидатів (2020–2023), parquet | Словник навичок, зарплатна статистика, ціна навичок |

⚠️ **Важливі особливості даних:**
- У `dou_active_vacancies.csv` зарплата вказана лише у **~16 %** вакансій (≈550 з 3 512), формати різні: `$700`, `$560–1700`, `від $600`, `до $2500`. Потрібен парсер → поля `salary_min`, `salary_max`, `salary_mid` (USD). Вакансії без зарплати все одно показуємо, але для статистики використовуємо лише ті, де вона є (+ історичні датасети).
- Колонка `categories` — це категорії DOU (Python, Java, QA, DevOps, AI/ML, Hardware, Analyst, Design, Project Manager…); багато вакансій мають кілька категорій через кому. Файл має BOM (`encoding="utf-8-sig"`).
- `location` може бути порожнім або містити кілька значень (`Київ, Львів, віддалено`) → з нього виводимо `is_remote`.
- `snippet` — короткий опис (англійською або українською): із нього + `title` витягуємо навички за словником ключових слів.
- **Перед стартом розробки** перевірте колонки parquet-датасетів Djinni та DOU salaries (`pd.read_parquet(...).columns`) — вони описані лише в маніфестах, у README не гарантовані.
- Не комітьте великі згенеровані файли (>50 MB). Кеш / результати обробки кладіть у `cache/` і додайте в `.gitignore`.

### Логіка обчислень (Python)

- **Навички вакансії:** словник навичок (`python`, `django`, `react`, `sql`, `docker`, `aws`, …) + пошук у `title` + `snippet` + `categories` → множина навичок `skills`.
- **Матчинг:** `score = |user_skills ∩ job_skills| / |job_skills|` (з бонусом, якщо збігається категорія/позиція). Показуємо вакансії зі `score` вище порога, від найкращих до гірших; вже свайпнуті не повторюємо.
- **Зарплата за навичками:** медіана та середня `salary_mid` по вакансіях/записах, що містять навички користувача.
- **«Що підкачати»:** для кожної навички, якої в користувача немає: (а) приріст медіани зарплати, якщо додати її до набору; (б) скільки нових вакансій стане доступно (`score` перетне поріг). Сортуємо за приростом → топ-N.

### Технічний стек

- **Python 3.11+**, **pandas** (дані), **Flask** (бекенд і Jinja-шаблони), **matplotlib** або **Plotly** (графіки; можна рендерити на сервері в PNG/SVG).
- **HTML/CSS** — шаблони й стилі. Мінімальний JS допускається **лише** для жестів свайпу (drag) — вся логіка залишається в Python; свайп також має працювати кнопками ✗ / ♥ (POST-запит на Python-ендпоінт).
- Збереження стану користувача (профіль, вподобані вакансії): Flask `session`/cookie або простий JSON-файл — без складної БД і без реєстрації.

### Структура проєкту (пропозиція)

```
app/
  main.py          # Flask: маршрути /, /swipe, /profile, /insights, POST /like, /skip
  data_loader.py   # читання CSV/parquet, очищення, парсинг зарплати
  skills.py        # словник навичок, витягування навичок з тексту
  matching.py      # скоринг та відбір вакансій під профіль
  salary.py        # статистика зарплат (медіана/середня), розподіли
  upgrade.py       # рекомендації «що підкачати»
  storage.py       # збереження профілю та вподобаних вакансій
  templates/       # base.html, onboarding.html, swipe.html, profile.html, insights.html
  static/          # style.css, (мінімальний) swipe.js
requirements.txt
```

### Розбиття на таски

Кожен таск має **власні файли** (щоб розробники й агенти не конфліктували в Git) і чіткий вихід. Між модулями домовляємось про контракти нижче — це дозволяє працювати паралельно.

**Контракти між модулями:**
- `data_loader.load_jobs() -> pandas.DataFrame` з колонками: `id, title, company, location, is_remote, salary_min, salary_max, salary_mid, categories (list[str]), skills (set[str]), snippet, link`.
- `skills.extract_skills(text: str) -> set[str]`; `skills.ALL_SKILLS: list[str]`.
- `matching.rank_jobs(jobs, user_skills, position, exclude_ids) -> DataFrame` (+ колонка `match_score` 0–1).
- `salary.salary_stats(jobs, user_skills) -> dict` (`median`, `mean`, `count`, `distribution`).
- `upgrade.recommend(jobs, user_skills, top_n=5) -> list[dict]` (`skill`, `salary_gain`, `new_jobs`).
- `storage`: `get_profile()`, `save_profile(position, skills)`, `like(job_id)`, `skip(job_id)`, `liked_jobs()`.

| Таск | Опис | Файли | Залежить від | Done-критерій |
|---|---|---|---|---|
| **T0. Каркас** | Flask-проєкт, `requirements.txt`, `base.html` з нижньою навігацією на 3 вкладки, запуск `python -m app.main` | `app/main.py`, `requirements.txt`, `templates/base.html` | — | Сайт відкривається, 3 вкладки перемикаються |
| **T1. Дані** | Завантажити CSV, очистити, парсинг зарплати (`$700`, `$560–1700`, `від/до`), `is_remote`, список категорій, унікальний `id` | `app/data_loader.py` | — | `load_jobs()` повертає DataFrame за контрактом; юніт-перевірка на прикладах зарплат |
| **T2. Навички** | Словник навичок (з Djinni + вручну), `extract_skills`, додати колонку `skills` | `app/skills.py` | T1 | У ≥80 % вакансій категорії IT знайдено ≥1 навичку |
| **T3. Онбординг** | Екран вибору позиції та навичок (теги), збереження профілю | `templates/onboarding.html`, `app/storage.py` | T0, T2 | Після вибору профіль зберігається й відкриваються вкладки |
| **T4. Матчинг** | `rank_jobs`, скоринг, відсів уже свайпнутих | `app/matching.py` | T1, T2 | Для тестового профілю повертає відсортований список зі `match_score` |
| **T5. Свайпи (вкладка 1)** | Картка вакансії, кнопки ✗/♥, жест свайпу, POST `/like` `/skip`, наступна картка | `templates/swipe.html`, `static/swipe.js`, `static/style.css`, роути в `main.py` | T0, T3, T4 | Вправо — вакансія в збережених, вліво — зникає; черга закінчується красивим порожнім станом |
| **T6. Профіль (вкладка 2)** | Показ позиції/навичок, редагування, список вподобаних вакансій із посиланнями | `templates/profile.html`, `app/storage.py` | T3, T5 | Вподобані вакансії відображаються й відкриваються за посиланням |
| **T7. Статистика (вкладка 3, частина A)** | Медіана/середня зарплата за навичками, розподіл, графік | `app/salary.py`, `templates/insights.html` | T1, T2 | Дашборд показує числа й графік для профілю користувача |
| **T8. Апгрейд (вкладка 3, частина B)** | Рекомендації «що підкачати»: приріст зарплати + нові вакансії | `app/upgrade.py`, блок у `insights.html` | T4, T7 | Топ-5 навичок із цифрами для будь-якого профілю |
| **T9. Резюме (stretch)** | Завантаження TXT/PDF → `extract_skills` → попередній вибір навичок | `app/resume.py`, форма в `onboarding.html` | T2, T3 | Навички з резюме підставляються в онбординг |
| **T10. Полірування й демо** | Стилі «як у Tinder/Badoo», порожні стани, помилки, сценарій демо на 2 хв, перевірка запуску з нуля | `static/style.css`, `docs/` | усі | Свіжий `git clone` + `pip install -r requirements.txt` + запуск працює без помилок |

**Рекомендований порядок:** T0 і T1 одночасно → T2 → (T3, T4, T7 паралельно) → (T5, T6, T8 паралельно) → T10. T9 — лише якщо лишився час.

**Правила паралельної роботи:** кожен розробник/агент бере один таск і працює лише в його файлах; перед стартом `git pull --rebase`; коміти малі й часті, **від різних учасників**; не змінюйте чужі контракти без домовленості в чаті команди.

---

# Hackathon rules (EN)

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
