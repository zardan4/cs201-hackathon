"""Normalize DOU salary survey waves into SalaryRecord cache/salary_records.parquet."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ANALYTICS_DIR = Path(__file__).resolve().parent
ROOT_DIR = ANALYTICS_DIR.parent
SALARY_DATASETS_DIR = ROOT_DIR / "data" / "datasets" / "devua-salaries"
DEFAULT_SALARY_CACHE_PATH = ROOT_DIR / "cache" / "salary_records.parquet"

MIN_SURVEY_SALARY_USD = 100.0
MAX_SURVEY_SALARY_USD = 35000.0

SALARY_RECORD_COLUMNS = [
    "survey",
    "salary_usd",
    "position",
    "main_language",
    "specialization",
    "experience_years",
    "english_level",
    "company_size",
]


@dataclass(frozen=True)
class _WaveSpec:
    survey_name: str
    folder: str
    salary_col: str
    category_col: str
    role_col: str
    spec_col: str
    lang_col: str
    exp_col: str
    english_col: str
    company_size_col: str


_WAVES: tuple[_WaveSpec, ...] = (
    _WaveSpec(
        survey_name="2026_june",
        folder="2026_june_raw",
        salary_col="ЗАРПЛАТА СУМАРНИЙ ДОХІД в ІТ",
        category_col="Категорії",
        role_col="Посади",
        spec_col="Спеціалізації: SE",
        lang_col="Основна мова програмування",
        exp_col="Загальний стаж роботи за нинішньою ІТ-спеціальністю",
        english_col="Знання англійської мови",
        company_size_col="Кількість спеціалістів у вашій компанії в Україні",
    ),
    _WaveSpec(
        survey_name="2025_dec",
        folder="2025_dec_raw",
        salary_col="ЗАРПЛАТА / СУМАРНИЙ ДОХІД в IT у $$$ за місяць, лише ставка \nЧИСТИМИ - після сплати податків",
        category_col="Категорії",
        role_col="Почніть вводити і оберіть вашу ОСНОВНУ посаду зі списку",
        spec_col="Спеціалізації: SE",
        lang_col="Основна мова програмування",
        exp_col="Загальний стаж роботи за нинішньою ІТ-спеціальністю",
        english_col="Знання англійської мови",
        company_size_col="Кількість спеціалістів у вашій компанії в Україні",
    ),
    _WaveSpec(
        survey_name="2025_june",
        folder="2025_june_raw",
        salary_col="ЗАРПЛАТА / СУМАРНИЙ ДОХІД в IT у $$$ за місяць, лише ставка \nЧИСТИМИ - після сплати податків",
        category_col="Категорія",
        role_col="Почніть вводити і оберіть вашу ОСНОВНУ посаду зі списку",
        spec_col="Вкажіть вашу основну спеціалізацію",
        lang_col="Основна мова програмування",
        exp_col="Загальний стаж роботи за нинішньою ІТ-спеціальністю",
        english_col="Знання англійської мови",
        company_size_col="Кількість спеціалістів у вашій компанії в Україні",
    ),
)

_LANGUAGE_MAP: dict[str, str] = {
    "python": "python",
    "typescript": "typescript",
    "javascript": "javascript",
    "java": "java",
    "c# / .net": "c#/.net",
    "c#  net": "c#/.net",
    "c++": "c++",
    "c": "c",
    "go": "go",
    "php": "php",
    "sql": "sql",
    "мови розробки бд (pl/sql, transact-sql)": "sql",
    "мови розробки бд (plsql transact-sql)": "sql",
    "kotlin": "kotlin",
    "swift": "swift",
    "bash / shell": "bash",
    "bash  shell": "bash",
    "bashshell": "bash",
    "bash": "bash",
    "powershell": "bash",
    "dart": "dart",
    "ruby": "ruby",
    "rust": "rust",
    "scala": "scala",
    "1c": "1c/bas",
    "1с": "1c/bas",
    "abap": "abap",
    "apex": "apex",
    "salesforce apex": "apex",
    "node.js": "node.js",
    "node js": "node.js",
    "nodejs": "node.js",
    "next.js": "next.js",
    "solidity": "blockchain",
    "terraform": "terraform",
    "hcl": "terraform",
    "hcl - hashicorp configuration language": "terraform",
    "vhdl": "fpga",
    "verilog, system verilog": "fpga",
    "html": "html/css",
    "html-css": "html/css",
    "htmlscss": "html/css",
    "css": "html/css",
    "react  react native": "react",
}

_ENGLISH_MAP: dict[str, str] = {
    "не знаю взагалі": "none",
    "elementary": "basic",
    "pre-intermediate": "pre",
    "intermediate": "intermediate",
    "upper-intermediate": "upper",
    "advanced": "fluent",
}

_EXP_RANGE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*рок", re.IGNORECASE)
_EXP_NUM_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*(?:рок|$)", re.IGNORECASE)

_LANG_TO_POSITION: dict[str, str] = {
    "python": "Python",
    "java": "Java",
    "c#/.net": ".NET",
    "c++": "C++",
    "c": "C++",
    "go": "Golang",
    "php": "PHP",
    "ruby": "Ruby",
    "rust": "Rust",
    "scala": "Scala",
    "node.js": "Node.js",
    "dart": "Flutter",
    "1c/bas": "ERP/CRM",
    "abap": "SAP",
    "apex": "Salesforce",
    "blockchain": "Blockchain",
}

_MEM_SALARY_DF: pd.DataFrame | None = None


def clear_salary_cache() -> None:
    """Clear in-memory cached salary survey DataFrame."""
    global _MEM_SALARY_DF
    _MEM_SALARY_DF = None


def _clean_opt_str(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "немає відповіді"}:
        return None
    return text


def parse_survey_salary(value: object) -> float | None:
    """Parse DOU survey salary USD value and drop out-of-range outliers."""
    text = _clean_opt_str(value)
    if text is None:
        return None
    cleaned = text.replace(" ", "").replace(",", ".")
    try:
        amount = float(cleaned)
    except ValueError:
        return None
    if not (MIN_SURVEY_SALARY_USD <= amount <= MAX_SURVEY_SALARY_USD):
        return None
    return amount


def parse_experience_years(value: object) -> float | None:
    """Parse DOU experience strings (e.g. '4 роки', 'Півтора роки', '15-20 років', '2.5')."""
    text = _clean_opt_str(value)
    if text is None or text == "-99":
        return None
    low = text.lower()
    if "менше як 3" in low:
        return 0.15
    if "3 місяц" in low:
        return 0.25
    if "пів року" in low or "півроку" in low:
        return 0.5
    if "півтора" in low:
        return 1.5
    if "понад 20" in low:
        return 22.0
    if m := _EXP_RANGE_RE.match(low):
        return (float(m.group(1)) + float(m.group(2))) / 2.0
    if m := _EXP_NUM_RE.match(low):
        return float(m.group(1))
    try:
        num = float(low.replace(",", "."))
        return num if num >= 0 else None
    except ValueError:
        return None


def map_survey_language(value: object) -> str | None:
    """Map survey main programming language to canonical skill name."""
    text = _clean_opt_str(value)
    if text is None:
        return None
    low = text.lower()
    if low in _LANGUAGE_MAP:
        return _LANGUAGE_MAP[low]
    if low.startswith("не використовую") or low.startswith("не можу обрати") or low.startswith("інше") or low == "other":
        return None
    if "hcl" in low or "terraform" in low:
        return "terraform"
    if "powershell" in low or "bash" in low:
        return "bash"
    if "x++" in low or "d365" in low:
        return "dynamics 365"
    if "node" in low:
        return "node.js"
    return None


def map_survey_english(value: object) -> str | None:
    """Map DOU English proficiency text to none/basic/pre/intermediate/upper/fluent."""
    text = _clean_opt_str(value)
    if text is None:
        return None
    return _ENGLISH_MAP.get(text.lower())


def map_survey_position(
    category: str | None,
    role: str | None,
    specialization: str | None,
    main_language: str | None,
) -> str:
    """Map DOU survey role/category/language/specialization onto canonical Job positions."""
    role_low = (role or "").lower()
    cat_low = (category or "").lower()
    spec_low = (specialization or "").lower()

    if "scrum" in role_low or "agile" in cat_low:
        return "Scrum Master"
    if "qa" in role_low or "sdet" in role_low or "qa" in cat_low:
        return "QA"
    if "devops" in role_low or "sre" in role_low or "devops" in cat_low:
        return "DevOps"
    if "data engineer" in role_low or "big data" in role_low:
        return "Data Engineer"
    if "ai engineer" in role_low or "ml engineer" in role_low or "machine learning" in role_low:
        return "AI/ML"
    if "data scientist" in role_low:
        return "Data Science"
    if "ds / ai" in cat_low or cat_low in {"ds", "data science"}:
        return "Data Science" if "scientist" in role_low else "AI/ML"
    if "analyst" in role_low or "analytics" in cat_low or "analyst" in cat_low:
        return "Analyst"
    if "product manager" in role_low or "product owner" in role_low or "product management" in cat_low or "product mgmt" in cat_low:
        return "Product Manager"
    if "project manager" in role_low or "delivery manager" in role_low or "project management" in cat_low or "project mgmt" in cat_low:
        return "Project Manager"
    if "architect" in role_low:
        return "Architect"
    if "engineering manager" in role_low:
        return "Engineering Manager"
    if "cto" in role_low or "ceo" in role_low or "chief" in role_low or "general leadership" in cat_low:
        return "C-level"
    if "sysadmin" in role_low or "sysadmin" in cat_low:
        return "SysAdmin"
    if "security" in role_low or "security" in cat_low:
        return "Security"
    if "support" in role_low or "customer success" in role_low or "support" in cat_low or "customer success" in cat_low:
        return "Support"
    if "dba" in role_low or "dba" in cat_low or "database розробка" in spec_low:
        return "DBA"
    if "technical writer" in role_low or "techwriter" in role_low or "tech wr" in cat_low or "tech writer" in cat_low:
        return "Technical Writer"
    if "hardware" in role_low or "hardware" in cat_low:
        return "Hardware"
    if "ui/ux" in role_low or "uiux" in role_low or "designer" in role_low or "design" in cat_low or "artist" in cat_low:
        return "Design"
    if "embedded" in spec_low or ("embedded" in role_low and "software engineer" not in role_low):
        return "Embedded"
    if "платформна" in spec_low or "salesforce" in role_low or "sap" in role_low or "1с" in role_low or "1c" in role_low:
        if main_language == "abap":
            return "SAP"
        if main_language == "apex":
            return "Salesforce"
        return "ERP/CRM"

    # Software engineering / tech lead: disambiguate using main_language and specialization.
    if "software engineer" in role_low or "software engineering" in cat_low or cat_low == "se" or "tech lead" in role_low:
        if main_language in _LANG_TO_POSITION:
            return _LANG_TO_POSITION[main_language]
        if main_language == "kotlin" and "mobile" in spec_low:
            return "Android"
        if main_language in {"javascript", "typescript"}:
            if "back-end" in spec_low:
                return "Node.js"
            return "Front End"
        if "front-end" in spec_low:
            return "Front End"

    if main_language in _LANG_TO_POSITION:
        return _LANG_TO_POSITION[main_language]
    return "Other"


def _normalize_wave(spec: _WaveSpec, datasets_dir: Path) -> list[dict]:
    parquet_path = datasets_dir / spec.folder / "part-00000.parquet"
    if not parquet_path.exists():
        return []
    raw_df = pd.read_parquet(parquet_path)
    records: list[dict] = []

    for row in raw_df.to_dict(orient="records"):
        salary_usd = parse_survey_salary(row.get(spec.salary_col))
        if salary_usd is None:
            continue

        category = _clean_opt_str(row.get(spec.category_col))
        role = _clean_opt_str(row.get(spec.role_col))
        specialization = _clean_opt_str(row.get(spec.spec_col))
        main_language = map_survey_language(row.get(spec.lang_col))
        position = map_survey_position(category, role, specialization, main_language)

        records.append(
            {
                "survey": spec.survey_name,
                "salary_usd": salary_usd,
                "position": position,
                "main_language": main_language,
                "specialization": specialization,
                "experience_years": parse_experience_years(row.get(spec.exp_col)),
                "english_level": map_survey_english(row.get(spec.english_col)),
                "company_size": _clean_opt_str(row.get(spec.company_size_col)),
            }
        )
    return records


def build_salary_records(
    datasets_dir: Path = SALARY_DATASETS_DIR,
    cache_path: Path = DEFAULT_SALARY_CACHE_PATH,
    force: bool = False,
) -> pd.DataFrame:
    """Normalize DOU salary survey waves into cache/salary_records.parquet."""
    global _MEM_SALARY_DF

    if not force and cache_path.exists():
        return load_salary_records(refresh=False, datasets_dir=datasets_dir, cache_path=cache_path)

    all_rows: list[dict] = []
    for spec in _WAVES:
        all_rows.extend(_normalize_wave(spec, datasets_dir))

    df = pd.DataFrame.from_records(all_rows, columns=SALARY_RECORD_COLUMNS)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp_path, index=False)
    os.replace(tmp_path, cache_path)

    if cache_path.resolve() == DEFAULT_SALARY_CACHE_PATH.resolve():
        _MEM_SALARY_DF = df

    return df.copy()


def load_salary_records(
    refresh: bool = False,
    datasets_dir: Path = SALARY_DATASETS_DIR,
    cache_path: Path = DEFAULT_SALARY_CACHE_PATH,
) -> pd.DataFrame:
    """Load normalized DOU salary records (lazy process-once on first access)."""
    global _MEM_SALARY_DF
    is_default = cache_path.resolve() == DEFAULT_SALARY_CACHE_PATH.resolve()

    if not refresh and is_default and _MEM_SALARY_DF is not None:
        return _MEM_SALARY_DF.copy()

    if not refresh and cache_path.exists():
        df = pd.read_parquet(cache_path)
        if is_default:
            _MEM_SALARY_DF = df
        return df.copy()

    return build_salary_records(datasets_dir=datasets_dir, cache_path=cache_path, force=True)
