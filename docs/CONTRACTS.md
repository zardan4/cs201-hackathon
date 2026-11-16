# CONTRACTS — сутності та інтерфейси між ролями

> Єдине джерело правди про **сутності (entities)** і **інтерфейси**. Якщо щось змінюєте — спочатку правте цей файл і пишіть у чат команди, потім код.
> Усі сутності виведені з реальних даних у `data/` (див. «Звідки беруться поля»).
> Ролі й таски: [`TEAM.md`](TEAM.md). Ідея: [`../README.md`](../README.md).

> Каркас Flask розміщено в окремій папці `web/`: усі шляхи `app/...` у документації
> означають `web/app/...`. Python-імпорти залишаються `app.*` після
> `python -m pip install -r requirements.txt` з кореня репозиторію.
> `analytics/`, `data/` та `cache/` залишаються в корені репозиторію.

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
- `data/dou_vacancy_details/` — одноразовий скрейп повних описів вакансій, розбитий на `part-*.jsonl.xz` (`id`, `url`, `scraped_at`, `description`), який комітить DA. `analytics/jobs.py` використовує його лише для видобування навичок; веб його не читає. Перезбирання: `python -m analytics.scrape_descriptions` (resume) або `--force`.

## 2. Сутності (`app/models.py`, Python `dataclass`)

Власник файлу — **WE-A** (створює в таску A0 за 30 хв). Зміни — лише через PR-коміт + повідомлення в чат. Типи — стандартні Python (`str`, `int`, `float`, `bool`, `list`, `Optional`, `datetime`).

### 2.1 `Job` — вакансія (джерело: `data/dou_active_vacancies.csv`)
| Поле | Тип | Опис / правила |
|---|---|---|
| `id` | `str` | ID вакансії з `link`: `…/vacancies/380099/` → `"380099"`. Унікальний |
| `title` | `str` | з `title` |
| `company` | `str` | з `company` |
| `locations` | `list[str]` | `location` розбитий по комах, без маркерів віддаленої роботи (`віддалено`, `remote`), напр. `["Київ","Львів"]`; може бути `[]` |
| `is_remote` | `bool` | `True`, якщо у `location` є `віддалено` або `remote` (case-insensitive) |
| `salary_text` | `str \| None` | оригінальний `salary` (`"$560–1700"`, `"від $600"`, `"до $2500"`, `"$700"`) |
| `salary_min` / `salary_max` | `int \| None` | USD/міс. `"від X"` → min=X; `"до X"` → max=X; `"A–B"` → обидва; `"X"` → обидва = X. Позадіапазонні викиди (`< 100` погодинні або `> 30000`) → `None` |
| `salary_mid` | `int \| None` | середина інтервалу (або єдине значення), без викидів (`100..30000`). **Заповнене лише у ≈16 % вакансій; саме вони (і тільки вони) йдуть у свайпи** — див. розділ 0 |
| `categories` | `list[str]` | з `categories` через `;` (з fallback на `,`): `Python`, `Java`, `QA`, `DevOps`, `AI/ML`, … (це «позиції» DOU) |
| `skills` | `list[str]` | канонічні навички, витягнуті з `title`+`snippet`+`categories`+повного опису вакансії з `data/dou_vacancy_details/` (розділ 2.2) |
| `tags` | `list[str]` | додаткові теги з `title`+`snippet`+`location` (рівень: `senior/middle/junior/lead`, домен/формат: `fintech/miltech/igaming/saas/hybrid/part-time`) |
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
| `onboarding_completed` | `bool` | `False` до завантаження CV та підтвердження валідної форми; `True` після збереження |
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
- Виняток — скасування: якщо `SwipeAction` видалено (`reset_skipped`, `unsave_job`, `clear_saved`, розділ 4.2), вакансія знову потрапляє в стрічку.

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

A4–A5: `jobs_available` рахується через `analytics.matching.iter_ranked_jobs`
із `min_score=0.65`, `require_salary=True`, `remote_only` з профілю, без виключення
вже свайпнутих вакансій. Це кількість у всьому поточному датасеті, не довжина черги.
Upgrade counts із DA — для всіх локацій; salary gains порівнюють когорти без
фільтра стажу. UI пояснює відмінність від персональної salary_stats зі стажем.
Відсутні/нечислові salary stats показуються як «немає даних», не як $0.
`insights_service.salary_chart(profile) -> bytes` рендерить SVG з histogram DA
через matplotlib. `GET /insights/salary-distribution.svg` — захищений сесією графік.
Останній bucket включає всю верхню частину розподілу й підписується `from+`.

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
def build_jobs(force: bool = False) -> "pandas.DataFrame"       # збирає cache/jobs.parquet (1 раз, якщо немає кешу або force=True)
def load_jobs(refresh: bool = False, require_salary: bool | None = None) -> "pandas.DataFrame"  # lazy process-once; за замовчуванням бере SWIPE_REQUIRES_SALARY (розділ 0)
def iter_jobs(categories: list[str] | None = None, locations: list[str] | None = None,
              remote_only: bool = False, exclude_ids: set[str] | None = None,
              min_salary: int | None = None, skills: list[str] | None = None,
              tags: list[str] | None = None, require_salary: bool = False) -> "Iterator[dict]"  # yield відфільтровані Job dict
# analytics/skills.py
def extract_skills(text: str) -> list[str]
def extract_tags(title: str, snippet: str = "", location_text: str = "") -> list[str]
def all_skills() -> list[dict]                              # skills_catalog.json
def all_positions() -> list[str]
# analytics/cv.py
def parse_cv(text: str) -> dict                             # поля CvParseResult
# analytics/matching.py
def iter_ranked_jobs(position: str = "", skills: list[str] = (), exclude_ids: set[str] | None = None,
                     *, categories: list[str] | None = None, locations: list[str] | None = None,
                     remote_only: bool = False, min_salary: int | None = None,
                     tags: list[str] | None = None, min_score: float = 0.0) -> "Iterator[dict]"  # yield JobMatch від найкращих до гірших
def rank_jobs(position: str, skills: list[str], exclude_ids: set[str],
              remote_only: bool = False, limit: int = 50,
              *, categories: list[str] | None = None, locations: list[str] | None = None,
              min_salary: int | None = None, tags: list[str] | None = None,
              min_score: float = 0.0, require_salary: bool | None = None) -> list[dict]  # поля JobMatch (+ job як dict); при SWIPE_REQUIRES_SALARY=True лише вакансії з зарплатою (розділ 0)
# analytics/salary.py
def salary_stats(position: str, skills: list[str], experience_years: float | None) -> dict   # SalaryStats
# analytics/upgrade.py
def recommend_upgrades(position: str, skills: list[str], top_n: int = 5) -> list[dict]      # UpgradeSuggestion
```
Вхід/вихід — прості типи (`dict`, `list`, `str`); **`dict` мають рівно ті ключі, що описані в розділі 2**.

### 4.2 `app/services/` — пишуть Web Engineers (єдиний шар між `analytics` і роутами)
| Модуль | Власник | Функції |
|---|---|---|
| `app/services/catalog_service.py` | WE-A | `all_skills() -> list[str]`, `all_positions() -> list[str]`, `skill_entries() -> list[dict]` (канонічні назви + aliases для Gemini) |
| `app/services/profile_service.py` | WE-A | `get_or_create_profile(user_id) -> UserProfile`, `save_profile(profile)`, `import_cv(user_id, file) -> CvParseResult` |
| `app/services/jobs_service.py` | WE-B | `next_matches(profile, limit=10) -> list[JobMatch]`, `record_swipe(user_id, job_id, action)`, `saved_jobs(user_id) -> list[Job]` (найновіші лайки першими), `swiped_job_ids(user_id) -> set[str]`; скасування свайпів: `skipped_count(user_id) -> int`, `reset_skipped(user_id) -> int` (повертає всі skip у стрічку, лайки лишаються), `unsave_job(user_id, job_id) -> bool` (прибирає один лайк), `clear_saved(user_id) -> int` (прибирає всі лайки, skip лишаються). Стрічка: `rank_jobs` повертає до `FEED_POOL_SIZE = 200` кандидатів зі score ≥ `MIN_FEED_SCORE = 0.2`, з них `weighted_shuffle(rows, limit)` обирає `limit` карток зваженим випадковим вибором (вага `SCORE_BIAS + score`, `SCORE_BIAS = 0.25`) |
| `app/services/insights_service.py` | WE-A | `build_report(profile) -> InsightsReport` |

Правило: функції сервісів приймають/повертають **dataclass-сутності з `app/models.py`**, а не DataFrame/dict. Перетворення `dict → dataclass` робиться тільки тут.

### 4.3 HTTP-роути (межі між вкладками)
| Метод + URL | Власник | Призначення |
|---|---|---|
| `GET /` | WE-A | редірект: немає профілю → `/onboarding`, інакше → `/swipe` |
| `GET/POST /onboarding` | WE-A | обов'язковий CV → перегляд/редагування знайдених полів → підтвердження профілю |
| `POST /profile/cv` | WE-A | multipart `cv` (TXT/PDF, до 5 MiB запиту) → серверна чернетка `CvParseResult` → HTTP 303 на форму перегляду |
| `GET /profile` | WE-A | профіль, редагування, **список вподобаних вакансій** (з `jobs_service.saved_jobs`) |
| `POST /profile` | WE-A | збереження змін профілю |
| `POST /profile/saved/remove` | WE-A | форма `job_id` (+ `csrf_token`, опц. `next=swipe`) → `jobs_service.unsave_job` → HTTP 303 назад |
| `POST /profile/saved/clear` | WE-A | `csrf_token` (опц. `next=swipe`) → `jobs_service.clear_saved` → HTTP 303 назад |
| `POST /profile/feed/reset` | WE-A | `csrf_token` (опц. `next=swipe`) → `jobs_service.reset_skipped` → HTTP 303 назад; кнопка «Show skipped jobs again» на порожній стрічці `/swipe` |
| `GET /swipe` | WE-B | вкладка свайпів (перші картки рендеряться на сервері) |
| `GET /api/next-jobs?limit=10` | WE-B | JSON: `list[JobMatch]` (наступна порція карток) |
| `POST /api/swipe` | WE-B | тіло `{"job_id": "...", "action": "like"|"skip"}` → `{"ok": true}` |
| `GET /insights` | WE-A | вкладка 3: дашборд + «що підкачати» |

Файли роутів: `app/web/profile.py` (WE-A, `profile_bp`), `app/web/swipe.py` (WE-B, `swipe_bp`), `app/web/insights.py` (WE-A, `insights_bp`). `app/main.py` лише реєструє blueprint-и (пише WE-A у A0). Шаблони й статика — **у підпапках кожної вкладки**: `templates/swipe/…`, `templates/profile/…`, `static/swipe/…`, щоб не було конфліктів у Git.

## 5. Спільний каркас WE-A → WE-B (A0)

- Запуск каркаса з кореня: `python -m pip install -r requirements.txt && python -m app.main`.
  Поки DA не додав `analytics.build`, каркас працює без даних і показує порожні сторінки.
- Фабрика: `app.main.create_app(config: dict | None = None) -> Flask`.
  `USER_STORAGE_DIR` у Flask config за замовчуванням — абсолютний `cache/users/` у корені.
  У cookie-сесії зберігається `user_id` (UUID) та службові flash-повідомлення,
  а не текст CV, чернетка чи історія свайпів. Ключ підпису сесії береться з
  `BLOWMYJOB_SECRET_KEY` або з приватного `cache/.session-key`, щоб сесія переживала перезапуск.
  Перед кожним запитом `g.profile` містить `UserProfile`;
  `g.onboarding_complete` = підтверджений профіль із непорожніми CV та позицією.
  До підтвердження дозволені лише onboarding, upload CV, `/` та static;
  решта сторінок редіректять на onboarding, `/api/*` повертають HTTP 403
  `{"error": "onboarding_required", "redirect": "/onboarding"}`.
- Blueprint-и / endpoint-и: `profile_bp` має ім'я `profile` і endpoint-и
  `profile.onboarding`, `profile.index`, `profile.upload_cv`; `insights_bp` —
  `insights`, endpoint `insights.index`; WE-B створює `swipe_bp = Blueprint("swipe", __name__)`
  у `app/web/swipe.py`, з endpoint `swipe.index` для `GET /swipe`.
  Після появи цього модуля фабрика реєструє його замість спільної порожньої сторінки
  (потрібен перезапуск). Помилки всередині наявного модуля не приховуються.
- Шаблони наслідують `base.html`; блоки: `title`, `styles`, `content`, `scripts`.
  Навігація: Swipe → Profile → Insights. Спільні стилі — `static/profile/base.css`.
- Форми WE-A використовують прихований `csrf_token`, прив'язаний до user_id та ключа сесії.
  API свайпів реалізує WE-B, каркас їх не імітує.

### 5.1 `app.storage` (виклики всередині Flask application context)

```python
def load_profile(user_id: str) -> UserProfile | None: ...
def save_profile(profile: UserProfile) -> None: ...
def list_swipes(user_id: str) -> list[SwipeAction]: ...
def append_swipe(swipe: SwipeAction) -> None: ...
def remove_swipes(user_id: str, *, action: str | None = None, job_id: str | None = None) -> int: ...
def load_cv_draft(user_id: str) -> CvParseResult | None: ...
def save_cv_draft(user_id: str, result: CvParseResult | None) -> None: ...
```

Файл `cache/users/<user_id>.json` має форму `{"profile": {...}, "swipes": [...], "cv_draft": {...} | null}`;
часові мітки — ISO 8601 (UTC), при читанні відновлюються як `datetime`.
Оновлення профілю зберігає свайпи, додавання свайпу зберігає профіль.
Повторний свайп одного `job_id` ігнорується (перша дія залишається).
`append_swipe` потребує існуючого профілю; невідомий профіль → `ValueError`.
`remove_swipes` видаляє свайпи за `action` та/або `job_id` і повертає кількість видалених;
без жодного фільтра → `ValueError` (захист від випадкового стирання всієї історії).
Запис — через тимчасовий файл + atomic replace; read-modify-write захищений
lock у межах одного процесу (локальний Flask-сервер для демо).
Для кількох worker-процесів потрібне інше сховище або міжпроцесне блокування.

### 5.2 CV та підтвердження профілю (A1–A3)

- Перед показом чернетки всі відомі навички, знайдені DA `extract_skills` у тексті CV,
  об'єднуються з результатом Gemini та обмежуються поточним JSON каталогом.
  `profile_service.get_cv_draft(user_id)` оновлює також раніше створені чернетки.
  Усі знайдені навички позначені у формі за замовчуванням; після підтвердження
  ручне зняття checkbox зберігається і не скасовується повторним аналізом.

- `profile_service.import_cv(user_id, file)` читає TXT (UTF-8/UTF-16 з BOM) або PDF
  (`pypdf`, до 30 сторінок), надсилає текст у Google Gemini через серверний API,
  валідує структурований JSON і зберігає `CvParseResult` у `cv_draft`.
  Оригінальні файли не зберігаються; витягнутий текст — максимум 100 000 символів.
  Парольні PDF, PDF без тексту, бінарні TXT та порожні файли відхиляються.
  Помилки файлу → `ValueError` → форма з повідомленням HTTP 400; завеликий запит → 413.
- Gemini використовує `GEMINI_API_KEY` (або `GOOGLE_API_KEY`), `GEMINI_MODEL`
  (за замовчуванням `gemini-3.5-flash-lite`) та timeout 30 секунд. Коренева `.env`
  завантажується сервером і не комітиться. Токен не передається браузеру, у промпт
  або сховище профілів. CV-текст передається Google — це зазначено біля upload.
- Навички беруться з `analytics/skills_catalog.json` (підтверджений шлях):
  список `[{"name": "python", "aliases": [...], "group": "language"}, ...]`;
  також підтримується простий список канонічних рядків. За наявності файлу він
  є авторитетним джерелом для Gemini, форми та валідації; інакше можливий каталог
  із DA `analytics.skills.all_skills()`. Немає каталогу → extraction недоступний,
  без тихої заміни regex-парсером чи вигаданим списком.
- Позиції беруться з DA `all_positions()` з розбиттям `;`/`,`; поки модуля немає,
  використовується знімок 43 категорій фактичного DOU CSV у `catalog_service`
  (напр. `Golang`, `Data Science`). Runtime вебкод не читає сирий CSV.
- Повний каталог навичок передається у промпті; Python обмежує результат його
  канонічними ключами (великий enum навичок перевищує ліміт branching Gemini).
  JSON Schema задає список рядків для навичок, позиції — категоріями DOU,
  English — enum профілю, стаж — 0–80 років. Python повторно перевіряє типи,
  нормалізує відомі aliases до канонічних ключів, відкидає невідомі навички
  з попередженням і не дозволяє відповіді моделі змінювати session/user_id.
  Для відсутніх даних — `null`/порожній список та ручне редагування у формі.
- Налаштування/мережа/ліміт Gemini → контрольована помилка 503;
  некоректна відповідь моделі → 502. Поточний профіль і чернетка зберігаються.
  `analytics.cv.parse_cv` залишається DA API для інших споживачів;
  CV upload тепер явно використовує Gemini за запитом користувача.
- Додаткові функції `profile_service`: `is_profile_ready(profile) -> bool`,
  `confirm_profile(user_id, form) -> UserProfile`. `form` — Flask/Werkzeug MultiDict;
  поля: `position`, повторюване `skills`, `experience_years`, `english_level`,
  опційний checkbox `remote_only`. Невалідні значення → `ValueError`.
- Перше підтвердження потребує серверної чернетки CV. Форма не приймає `user_id`,
  `cv_text` чи `onboarding_completed` від браузера: вони беруться із сесії/сховища.
  Після перевірки позиції, канонічних навичок, стажу 0–80 та рівня англійської
  профіль зберігається, `onboarding_completed=True`, чернетка очищується.
  Завантаження нового CV не перезаписує підтверджений профіль до збереження форми.
