# CONTRACTS — сутності та інтерфейси між ролями

> Єдине джерело правди про **сутності (entities)** і **інтерфейси**. Якщо щось змінюєте — спочатку правте цей файл і пишіть у чат команди, потім код.
> Усі сутності виведені з реальних даних у `data/` (див. «Звідки беруться поля»).
> Ролі й таски: [`TEAM.md`](TEAM.md). Ідея: [`../README.md`](../README.md).

## 0. Рішення щодо зарплат (зафіксовано)

- **Вкладка свайпів показує лише вакансії, де зарплата вказана** (`salary_mid` не `None`): у `dou_active_vacancies.csv` це ≈550 із 3 512 (≈16 %). Вакансії без зарплати в стрічку **не потрапляють**.
- **Вся статистика зарплат (вкладка 3) рахується тільки з опитувань DOU** (`data/datasets/devua-salaries/`, свіжі: `2026_june_raw`, `2025_dec_raw`, за потреби `2025_june_raw`), а **не** з вакансій. Вакансії — лише джерело карток і «нових вакансій» для апгрейду.
- ⚠️ Ризик: пул ≈550 вакансій після фільтра за навичками може бути малим. DA на старті (DA1) рахує, скільки вакансій у пулі по кожній позиції, і пише це в `docs/DATA_NOTES.md`. Для запасу в `analytics/config.py` є прапорець `SWIPE_REQUIRES_SALARY = True` (якщо виставити `False`, у стрічці з'являться й вакансії без зарплати; картка тоді показує «зарплата не вказана»).

## 1. Потік даних (хто кого годує)

```
data/*  ──►  analytics/ (Data Analyst)  ──►  cache/*.parquet + Python API  ──►  app/services/ (Web Engineers)  ──►  routes + templates
```

- **Data Analyst (DA)** читає сирі дані з `data/`, чистить їх і **кладе готові таблиці у `cache/`** (`python -m analytics.build`). Також надає Python-функції (розділ 4).
- **Web Engineers (WE-A, WE-B)** *ніколи не читають `data/` напряму* і не працюють із сирими DataFrame у шаблонах. Вони читають `cache/` та викликають `analytics.*` **лише через шар `app/services/`**, який перетворює результат на **dataclass-сутності** з `app/models.py` (розділ 2).
- Папка `cache/` у `.gitignore`. Кожен локально збирає її командою `python -m analytics.build` (< 1 хв). **Виняток:** DA комітить маленькі `analytics/fixtures/*.json` (≈20 вакансій, 200 записів зарплат) — щоб веб-інженери могли працювати на моках, не чекаючи на готові дані.

## 2. Сутності (`app/models.py`, Python `dataclass`)

Власник файлу — **WE-A** (створює в таску A0 за 30 хв). Зміни — лише через PR-коміт + повідомлення в чат. Типи — стандартні Python (`str`, `int`, `float`, `bool`, `list`, `Optional`, `datetime`).

### 2.1 `Job` — вакансія (джерело: `data/dou_active_vacancies.csv`)
| Поле | Тип | Опис / правила |
|---|---|---|
| `id` | `str` | ID вакансії з `link`: `…/vacancies/380099/` → `"380099"`. Унікальний |
| `title` | `str` | з `title` |
| `company` | `str` | з `company` |
| `locations` | `list[str]` | `location` розбитий по комах, без `віддалено` (напр. `["Київ","Львів"]`); може бути `[]` |
| `is_remote` | `bool` | `True`, якщо у `location` є `віддалено` |
| `salary_text` | `str \| None` | оригінальний `salary` (`"$560–1700"`, `"від $600"`, `"до $2500"`, `"$700"`) |
| `salary_min` / `salary_max` | `int \| None` | USD/міс. `"від X"` → min=X; `"до X"` → max=X; `"A–B"` → обидва; `"X"` → обидва = X |
| `salary_mid` | `int \| None` | середина інтервалу (або єдине значення). **Заповнене лише у ≈16 % вакансій; саме вони (і тільки вони) йдуть у свайпи** — див. розділ 0 |
| `categories` | `list[str]` | з `categories` через кому: `Python`, `Java`, `QA`, `DevOps`, `AI/ML`, … (це «позиції» DOU) |
| `skills` | `list[str]` | канонічні навички, витягнуті з `title`+`snippet`+`categories` (розділ 2.2) |
| `snippet` | `str` | короткий опис (EN/UK) |
| `url` | `str` | `link` — оригінал вакансії |
| `posted_at` | `date` | `date` |

### 2.2 `Skill` / `Position` — довідники
- **Навичка** = канонічний рядок у нижньому регістрі, напр. `"python"`, `"django"`, `"react"`, `"sql"`, `"docker"`, `"aws"`, `"c#/.net"`. Повний каталог: `analytics/skills_catalog.json` (`[{"name","aliases":[...],"group":"language|framework|tool|cloud|other"}]`). Веб читає каталог через `services.catalog_service.all_skills()`.
- **Позиція** = одна зі значень `categories` DOU (`Python`, `Java`, `.NET`, `Front End`, `Node.js`, `C++`, `QA`, `DevOps`, `AI/ML`, `Data Engineer`, `Analyst`, `Design`, `Product Manager`, `Project Manager`, `Security`, `SysAdmin`, `Support`, `Embedded`, …). Список: `services.catalog_service.all_positions()`.
- Основні мови програмування в опитуванні зарплат DOU (`Основна мова програмування`) мапляться на ті самі канонічні навички.

### 2.3 `UserProfile` — користувач (без реєстрації; ідентифікатор у cookie-сесії)
| Поле | Тип | Опис |
|---|---|---|
| `user_id` | `str` | `uuid4`, генерується при першому візиті |
| `position` | `str` | одна з позицій (2.2) |
| `skills` | `list[str]` | канонічні навички |
| `experience_years` | `float` | загальний стаж; для порівняння з опитуванням DOU (`Загальний стаж роботи…`) |
| `english_level` | `str` | `none/basic/pre/intermediate/upper/fluent` (як у Djinni `English Level`) |
| `remote_only` | `bool` | фільтр у свайпах (за замовчуванням `False`) |
| `cv_text` | `str \| None` | сирий текст резюме (якщо завантажено) |
| `created_at` / `updated_at` | `datetime` | |

### 2.4 `CvParseResult` — результат аналізу резюме (вихід DA, вхід WE-A)
`raw_text: str`, `detected_position: str | None`, `detected_skills: list[str]`, `detected_experience_years: float | None`, `detected_english_level: str | None`, `warnings: list[str]`. Користувач у профілі підтверджує/редагує те, що знайдено.

### 2.5 `JobMatch` — рекомендація (вихід DA, вхід WE-B)
| Поле | Тип | Опис |
|---|---|---|
| `job` | `Job` | вакансія |
| `score` | `float` | 0..1, відповідність профілю |
| `matched_skills` | `list[str]` | навички вакансії, які є у користувача |
| `missing_skills` | `list[str]` | навички вакансії, яких немає (показуємо на картці як «підкачати») |
| `reason` | `str` | коротке пояснення для картки (`"Python, Django · 3 з 4 навичок"`) |

### 2.6 `SwipeAction` / `SavedJob` — дії користувача (власник: WE-B пише, WE-A читає для профілю)
- `SwipeAction`: `user_id`, `job_id`, `action: "like" | "skip"`, `created_at`.
- `SavedJob` = `SwipeAction` з `action="like"` + денормалізований `Job` для показу у профілі.
- Правило: вакансія, на яку вже є `SwipeAction`, **не показується повторно**.

### 2.7 `SalaryRecord` — рядок опитування зарплат (джерело: `data/datasets/devua-salaries/`)
Нормалізована таблиця `cache/salary_records.parquet`. **Схеми файлів різні за роками** (колонки перейменовуються) — DA мапить їх до єдиної схеми. Для MVP беремо найсвіжіші: `2026_june_raw` (14 361 рядків), `2025_dec_raw` (12 502), за потреби `2025_june_raw`.
| Поле | Тип | Звідки (приклад для `2026_june_raw`) |
|---|---|---|
| `survey` | `str` | назва папки, напр. `"2026_june"` |
| `salary_usd` | `float` | `ЗАРПЛАТА СУМАРНИЙ ДОХІД в ІТ` (USD/міс., чисті) |
| `position` | `str` | `Посади` / `Тайтл` / `Категорії` → мапінг на позиції (2.2) |
| `main_language` | `str \| None` | `Основна мова програмування` → канонічна навичка |
| `specialization` | `str \| None` | `Спеціалізації: SE` |
| `experience_years` | `float \| None` | `Загальний стаж роботи за нинішньою ІТ-спеціальністю` (`"4 роки"`, `"15-20 років"` → середина) |
| `english_level` | `str \| None` | `Знання англійської мови` |
| `company_size` | `str \| None` | `Кількість спеціалістів у вашій компанії в Україні` |

> ⚠️ Опитування DOU: у README/публікаціях обов'язково вказувати DOU як джерело (див. `data/manifests/devua-csv.json`). Дані Djinni (`jobs-*`, `candidates-*`) — MIT; **зарплат у них немає**, колонки: jobs — `Position, Long Description, Company Name, Exp Years, Primary Keyword, English Level, Published, id`; candidates — `Position, Moreinfo, Looking For, Highlights, Primary Keyword, English Level, Experience Years, CV, id`. Їх використовуємо для словника навичок і (stretch) спільної зустрічальності навичок.

### 2.8 `SalaryStats` — статистика зарплат (вихід DA)
`median: float`, `mean: float`, `p25: float`, `p75: float`, `count: int` (розмір вибірки), `basis: "survey"` (завжди — статистика лише з опитувань DOU, розділ 0), `filters: dict` (які фільтри застосовано: position/skills/experience), `histogram: list[{"from": int, "to": int, "count": int}]`. Якщо `count < 30` — DA розширює фільтр і повертає це у `filters`, щоб UI міг показати «мало даних».

### 2.9 `UpgradeSuggestion` — «що підкачати» (вихід DA)
`skill: str`, `salary_gain_usd: float` (приріст медіани, якщо додати навичку), `salary_gain_pct: float`, `new_jobs_count: int` (скільки додаткових вакансій з'являється), `example_job_ids: list[str]`, `sample_size: int`.

### 2.10 `InsightsReport` — усе для вкладки 3
`profile_salary: SalaryStats` (опитування DOU), `jobs_available: int` (вакансій із зарплатою, що підходять профілю), `top_upgrades: list[UpgradeSuggestion]`.

## 3. Артефакти `cache/` (контракт DA → WE)

| Файл | Створює | Схема |
|---|---|---|
| `cache/jobs.parquet` | `analytics.build` | колонки = поля `Job` (списки як `list`); **лише вакансії з `salary_mid`** (пул для свайпів) |
| `cache/salary_records.parquet` | `analytics.build` | колонки = поля `SalaryRecord` |
| `analytics/skills_catalog.json` | DA (комітиться) | див. 2.2 |
| `analytics/fixtures/*.json` | DA (комітиться) | зразки `Job`, `SalaryRecord`, `JobMatch`, `SalaryStats`, `UpgradeSuggestion`, `CvParseResult` у форматі цього документа |
| `cache/users/<user_id>.json` | WE-A (`storage`) | `UserProfile` + `swipes: list[SwipeAction]` |

## 4. Інтерфейси Python-функцій

### 4.1 `analytics/` — пише DA (чисті функції, без Flask)
```python
# analytics/jobs.py
def load_jobs() -> "pandas.DataFrame"                       # cache/jobs.parquet, колонки Job (лише вакансії з зарплатою)
# analytics/skills.py
def extract_skills(text: str) -> list[str]
def all_skills() -> list[dict]                              # skills_catalog.json
def all_positions() -> list[str]
# analytics/cv.py
def parse_cv(text: str) -> dict                             # поля CvParseResult
# analytics/matching.py
def rank_jobs(position: str, skills: list[str], exclude_ids: set[str],
              remote_only: bool = False, limit: int = 50) -> list[dict]   # поля JobMatch (+ job як dict); лише вакансії з зарплатою (розділ 0)
# analytics/salary.py
def salary_stats(position: str, skills: list[str], experience_years: float | None) -> dict   # SalaryStats
# analytics/upgrade.py
def recommend_upgrades(position: str, skills: list[str], top_n: int = 5) -> list[dict]      # UpgradeSuggestion
```
Вхід/вихід — прості типи (`dict`, `list`, `str`); **`dict` мають рівно ті ключі, що описані в розділі 2**.

### 4.2 `app/services/` — пишуть Web Engineers (єдиний шар між `analytics` і роутами)
| Модуль | Власник | Функції |
|---|---|---|
| `app/services/catalog_service.py` | WE-A | `all_skills() -> list[str]`, `all_positions() -> list[str]` |
| `app/services/profile_service.py` | WE-A | `get_or_create_profile(user_id) -> UserProfile`, `save_profile(profile)`, `import_cv(user_id, file) -> CvParseResult` |
| `app/services/jobs_service.py` | WE-B | `next_matches(profile, limit=10) -> list[JobMatch]`, `record_swipe(user_id, job_id, action)`, `saved_jobs(user_id) -> list[Job]` |
| `app/services/insights_service.py` | WE-A | `build_report(profile) -> InsightsReport` |

Правило: функції сервісів приймають/повертають **dataclass-сутності з `app/models.py`**, а не DataFrame/dict. Перетворення `dict → dataclass` робиться тільки тут.

### 4.3 HTTP-роути (межі між вкладками)
| Метод + URL | Власник | Призначення |
|---|---|---|
| `GET /` | WE-A | редірект: немає профілю → `/onboarding`, інакше → `/swipe` |
| `GET/POST /onboarding` | WE-A | вибір позиції, навичок, (опц.) CV |
| `POST /profile/cv` | WE-A | завантаження резюме → `CvParseResult` |
| `GET /profile` | WE-A | профіль, редагування, **список вподобаних вакансій** (з `jobs_service.saved_jobs`) |
| `POST /profile` | WE-A | збереження змін профілю |
| `GET /swipe` | WE-B | вкладка свайпів (перші картки рендеряться на сервері) |
| `GET /api/next-jobs?limit=10` | WE-B | JSON: `list[JobMatch]` (наступна порція карток) |
| `POST /api/swipe` | WE-B | тіло `{"job_id": "...", "action": "like"|"skip"}` → `{"ok": true}` |
| `GET /insights` | WE-A | вкладка 3: дашборд + «що підкачати» |

Файли роутів: `app/web/profile.py` (WE-A, `profile_bp`), `app/web/swipe.py` (WE-B, `swipe_bp`), `app/web/insights.py` (WE-A, `insights_bp`). `app/main.py` лише реєструє blueprint-и (пише WE-A у A0). Шаблони й статика — **у підпапках кожної вкладки**: `templates/swipe/…`, `templates/profile/…`, `static/swipe/…`, щоб не було конфліктів у Git.
