# Python Open Data Hackathon — Rules

Event: KSE · CS201 Programming — Python hackathon on the topic **Open Data**, 16 November, 16:30–21:00 (Kyiv time).
Maximum score: **15 points**. 34 teams, 5 groups. The most important thing: the program must actually work during the demo.

> Project idea: see the **Ідея проєкту (UA)** section below (BlowMyJob). Hackathon rules are in English, the idea is in Ukrainian.

## 🚀 Запуск (Run)

Потрібен Python 3.11+. Усі команди виконуються з кореня репозиторію.

```bash
python -m venv web/.venv
source web/.venv/bin/activate          # Windows: web\.venv\Scripts\activate
pip install -r requirements.txt
python -m analytics.build              # один раз: будує cache/ з даних у data/ (~30 с)
cp web/.env.example .env               # вписати GEMINI_API_KEY (потрібен для аналізу резюме)
python -m app.main                     # відкрити http://127.0.0.1:5000
```

Наступні запуски: `source web/.venv/bin/activate && python -m app.main`.
Тести: `python -m pytest tests`. Детальніше про вебчастину — [`web/README.md`](web/README.md); демо-сценарій — [`docs/DEMO.md`](docs/DEMO.md).

## 💡 Ідея проєкту (UA)

**Назва:** *BlowMyJob* — «Tinder для IT-вакансій».

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
| **DOU salaries** | `data/datasets/devua-salaries/`, `data/raw/devua/` | Історичні опитування зарплат IT-спеціалістів | Статистика зарплат (опитування DOU, ~14k рядків у `2026_june_raw`: зарплата, посада, мова, стаж) |
| **Djinni recruitment dataset** (MIT) | `data/datasets/jobs-en`, `jobs-uk`, `candidates-en`, `candidates-uk`, `data/raw/djinni/` | ~140k+ описів вакансій та ~200k профілів кандидатів (2020–2023), parquet | Словник навичок (**зарплат у Djinni немає**) |

⚠️ **Важливі особливості даних:**
- У `dou_active_vacancies.csv` зарплата вказана лише у **~16 %** вакансій (≈550 з 3 512), формати різні: `$700`, `$560–1700`, `від $600`, `до $2500`. Потрібен парсер → поля `salary_min`, `salary_max`, `salary_mid` (USD). Вакансії без зарплати все одно показуємо, але для статистики використовуємо лише ті, де вона є (+ історичні датасети).
- Колонка `categories` — це категорії DOU (Python, Java, QA, DevOps, AI/ML, Hardware, Analyst, Design, Project Manager…); у фактичному CSV кілька категорій розділені `;` (парсер має підтримувати і `;`, і `,`). Файл має BOM (`encoding="utf-8-sig"`).
- `location` може бути порожнім або містити кілька значень (`Київ, Львів, віддалено`) → з нього виводимо `is_remote`.
- `snippet` — короткий опис (англійською або українською): із нього + `title` витягуємо навички за словником ключових слів.
- **Перед стартом розробки** перевірте колонки parquet-датасетів Djinni та DOU salaries (`pd.read_parquet(...).columns`) — вони описані лише в маніфестах, у README не гарантовані.
- **Рішення щодо зарплат:** у стрічку свайпів потрапляють **лише вакансії з вказаною зарплатою** (≈550). **Статистика зарплат (вкладка 3) рахується лише з опитувань DOU** (`devua-salaries`, свіжі роки), а не з вакансій. Деталі — `docs/CONTRACTS.md`, розділ 0.
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

### Ролі, сутності та таски

Детальна документація (читайте **перед стартом роботи**):
- 👥 [`docs/TEAM.md`](docs/TEAM.md) — ролі (**Data Analyst**, **Web Engineer A: профіль + CV + інсайти**, **Web Engineer B: свайпи**), власні файли, таски з залежностями, графік до 20:15.
- 📐 [`docs/CONTRACTS.md`](docs/CONTRACTS.md) — **сутності** (`Job`, `UserProfile`, `JobMatch`, `SwipeAction`, `SalaryRecord`, `SalaryStats`, `UpgradeSuggestion`, `CvParseResult`, `InsightsReport`), артефакти `cache/`, Python-інтерфейси `analytics/` і `app/services/`, HTTP-роути.

Коротко: **DA** перетворює `data/` на таблиці й аналітичні функції (`analytics/`), **WE** підключають їх до сайту через шар `app/services/` і сутності з `app/models.py`. Між собою ролі спілкуються лише через ці контракти.

```
analytics/   # DA: jobs, skills, salary_records, matching, salary, upgrade, cv, build, fixtures/
app/         # WE: main.py, models.py, storage.py, services/, web/, templates/, static/
cache/       # згенеровані таблиці (не в git)
docs/        # TEAM.md, CONTRACTS.md, DATA_NOTES.md, DEMO.md
requirements.txt
```

### Актуальність

Пошук роботи на традиційних сайтах забирає багато часу, виснажує через інформаційний шум і не дає фахівцям об'єктивного розуміння їхньої ринкової вартості. Ми поєднали гейміфікацію (пошук вакансій через свайпи) з розумною кар'єрною аналітикою. Замість звичайного каталогу користувач отримує персоналізовану добірку релевантних пропозицій. Це дозволяє швидко знаходити роботу, бачити реальну медіанну та середню зарплату й отримувати підкріплені даними поради, які навички розвивати для зростання доходу.
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
