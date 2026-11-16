# DATA_NOTES — Open Data Audit & Citations

## 1. Active Vacancies ([`data/dou_active_vacancies.csv`](../data/dou_active_vacancies.csv))

- **Source:** DOU Jobs (`https://jobs.dou.ua/`).
- **Encoding & Size:** UTF-8 with BOM (`encoding="utf-8-sig"`), **3,512** active vacancies spanning `2026-09-30` to `2026-11-16`, all with unique numeric IDs extracted from `link`.
- **Categories:** **43** unique DOU categories (`Hardware`, `Analyst`, `Other`, `QA`, `AI/ML`, `Design`, `Support`, `Product Manager`, `Project Manager`, `Embedded`, `DevOps`, `Security`, `SysAdmin`, `Python`, `C-level`, `Node.js`, `C++`, `Data Engineer`, `.NET`, `ERP/CRM`, `Java`, `Architect`, `Engineering Manager`, `Front End`, `PHP`, `Data Science`, `Technical Writer`, `SAP`, `Golang`, `DBA`, `Salesforce`, `Android`, `Big Data`, `Unity`, `Unreal Engine`, `Flutter`, `Rust`, `Scrum Master`, `Blockchain`, `No-code`, `Ruby`, `Scala`, `React Native`). Multi-category rows are separated by **semicolon `;`**, not comma.
- **Locations & Remote:** 137 rows have empty `location`; **1,713 (48.8%)** are remote-friendly (matching `"віддалено"` or `"remote"` tokens such as `"Poland (remote)"`, `"Remote Ukraine"`, `"Ukraine (remote)"`). Hybrid tokens (`"Київ (гібрид)"`, `"гібрид"`) are captured via `tags`.
- **Salaries & Outliers:** 547 rows (15.6%) list a salary string matching `(від |до )?$\d+([–-]\d+)?`. Two instructor/part-time postings list hourly rates (`"$20–25"`, `"$30"`), which are filtered out (`< $100`) from numeric `salary_min`/`salary_max`/`salary_mid`, leaving **545 (15.5%)** valid monthly USD salaries (`$200–400` up to `$10,000–15,000`).
- **Salaried Swipe Pool by Position (`SWIPE_REQUIRES_SALARY = True`):**
  - `Hardware`: 85, `Analyst`: 44, `Other`: 41, `Support`: 40, `QA`: 39, `SysAdmin`: 37, `Embedded`: 33, `Design`: 31, `AI/ML`: 29, `Security`: 26, `Project Manager`: 25, `DevOps`: 23, `Python`: 17, `Product Manager`: 15, `Node.js`: 14, `C-level`: 14, `ERP/CRM`: 13, `C++`: 11, `Data Engineer`: 10, `Front End`: 10, `PHP`: 9, `.NET`: 9, `Technical Writer`: 7, `Java`: 5, `Data Science`: 4, `Android`: 4, `DBA`: 3, `Architect`: 2, `No-code`: 2, `SAP`: 1, `Unity`: 1, `Ruby`: 1, `Salesforce`: 1, `Engineering Manager`: 1.
  - Note: 9 categories (`Golang`, `Big Data`, `Unreal Engine`, `Flutter`, `Rust`, `Scrum Master`, `Blockchain`, `Scala`, `React Native`) currently have `0` salaried postings; setting `SWIPE_REQUIRES_SALARY = False` in `analytics/config.py` (or `require_salary=False`) expands the feed to all 3,512 active vacancies.
- **Snippets & Extraction Coverage:** Snippets are 18–292 characters (DOU listing excerpts). Combining `title + snippet + categories` with [`analytics/skills_catalog.json`](../analytics/skills_catalog.json) extracts ≥ 1 skill on **3,236 / 3,512 (92.1%)** vacancies and ≥ 1 secondary tag on **2,242 / 3,512 (63.8%)** vacancies.

---

## 2. DOU Salary Surveys (`data/datasets/devua-salaries/`)

- **Source & Attribution:** [devua/csv](https://github.com/devua/csv/tree/master/salaries) — DOU IT salary surveys. **Mandatory attribution:** publications/demos must cite **DOU** with an active link (`https://dou.ua/` / `https://github.com/devua/csv`).
- **Normalized Table (`cache/salary_records.parquet`):** **38,535** normalized records across the 3 latest survey waves (`2026_june`: 14,361, `2025_dec`: 12,502, `2025_june`: 11,672 — filtering out `$0` or `> $35,000` invalid entries).
- **Schema Harmonization:**
  - Differing wave column names (`ЗАРПЛАТА СУМАРНИЙ ДОХІД в ІТ` vs multiline net salary header, `Посади` vs `Почніть вводити і оберіть вашу ОСНОВНУ посаду зі списку`, `Категорії` vs `Категорія`) are unified into `SalaryRecord`.
  - Experience strings (`"4 роки"`, `"Півтора роки"`, `"15-20 років"`, `"-99"`) and numeric strings (`"2.5"`) parse to `float | None`.
  - English proficiency maps onto `none/basic/pre/intermediate/upper/fluent`.
  - Generic `"Software Engineer / Developer"` roles are disambiguated onto DOU positions (`Python`, `.NET`, `Java`, `Front End`, `Node.js`, `PHP`, `C++`, `Golang`, `Android`, `Flutter`, `Ruby`, `Rust`, `Scala`, `Embedded`) via `Основна мова програмування` and `Спеціалізації: SE`.
- **Survey Medians & Upgrade Cohorts:** Overall median across the 38,535 records is `$2,800`; `salary_stats()` automatically widens filters whenever `count < 30`, and `recommend_upgrades()` enforces `sample_size >= 30` per DOU cohort.

---

## 3. Djinni Recruitment Dataset (`data/datasets/jobs*`, `candidates*`)

- **Source & License:** [lang-uk/djinni-recruitment-dataset](https://huggingface.co/collections/lang-uk/djinni-recruitment-dataset) — **MIT License** (see [`data/sources.json`](../data/sources.json)).
- **Inspected Columns (`jobs-en` 141,897 rows / `jobs-uk` 27,461 rows):** `Position`, `Long Description`, `Company Name`, `Exp Years`, `Primary Keyword`, `English Level`, `Published`, `Long Description_lang`, `id`. Contains **no salary data**; used to align `Primary Keyword` values and skill aliases in [`analytics/skills_catalog.json`](../analytics/skills_catalog.json).
