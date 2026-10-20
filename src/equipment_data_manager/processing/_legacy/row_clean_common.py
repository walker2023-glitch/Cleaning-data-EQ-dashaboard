"""Shared helpers for raw ``row/`` export cleaners (repairs, requests, service)."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

LABOR_RATE_PER_HOUR = 12.5
FOUND_HOURS = 0.5
DEFAULT_HOURS_WHEN_BLANK = 1.0


def project_root() -> Path:
    """Repository root (parent of the ``clean`` package)."""
    return Path(__file__).resolve().parent.parent


def row_input_dir(kind: str) -> Path:
    return project_root() / "data" / kind / "row"


def output_dir(kind: str) -> Path:
    return project_root() / "data" / kind


def list_row_files(kind: str, extensions: tuple[str, ...]) -> list[Path]:
    folder = row_input_dir(kind)
    if not folder.is_dir():
        return []
    out: list[Path] = []
    for name in sorted(folder.iterdir()):
        if name.is_file() and name.suffix.lower() in extensions:
            out.append(name)
    return out


def parse_dollar(value) -> float:
    if pd.isna(value):
        return 0.0
    s = str(value).strip().replace("$", "").replace(",", "")
    if not s:
        return 0.0
    n = pd.to_numeric(s, errors="coerce")
    return 0.0 if pd.isna(n) else float(n)


def extract_label(value, label: str) -> str:
    """``Equipment Id: 102395`` → ``102395``."""
    if pd.isna(value):
        return ""
    s = str(value).strip()
    key = label.strip().lower()
    if key and key in s.lower() and ":" in s:
        return s.split(":", 1)[1].strip()
    return s


def row_text(series: pd.Series) -> str:
    return " ".join(str(v) for v in series if pd.notna(v) and str(v).strip())


def row_mentions_found(series: pd.Series) -> bool:
    return bool(re.search(r"\bfound\b", row_text(series).lower()))


def parse_repair_hours(details, series: pd.Series) -> float:
    """Parse duration from the Details column (between parts cost and description).

    - ``found`` (or starts with found) → 0.5 h
    - blank → 0.5 h if the row mentions found, else 1 h
    - otherwise parse numeric / fractional duration
    """
    if pd.isna(details) or not str(details).strip() or str(details).strip().lower() == "nan":
        return FOUND_HOURS if row_mentions_found(series) else DEFAULT_HOURS_WHEN_BLANK

    s = str(details).strip()
    low = s.lower()
    if low == "found" or re.match(r"^found\b", low):
        return FOUND_HOURS

    norm = (
        low.replace("hours", "")
        .replace("hour", "")
        .replace("hrs", "")
        .replace("hr", "")
        .strip()
    )
    norm = re.sub(r"\s+", " ", norm)

    frac = re.search(r"(\d+)\s*/\s*(\d+)", norm)
    if frac:
        denom = float(frac.group(2))
        return float(frac.group(1)) / denom if denom else DEFAULT_HOURS_WHEN_BLANK

    typo = re.match(r"^(\d+)\s+(\d)$", norm.strip())
    if typo:
        return float(f"{typo.group(1)}.{typo.group(2)}")

    num = re.search(r"(\d+\.?\d*)", norm.replace(",", "."))
    if num:
        return float(num.group(1))

    if row_mentions_found(series):
        return FOUND_HOURS
    return DEFAULT_HOURS_WHEN_BLANK


def infer_month_key_from_name(filename: str) -> str | None:
    """``May Repair Report.csv`` → ``2026-05`` (year assumed from project data)."""
    m = re.search(
        r"\b(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\b",
        filename,
        re.I,
    )
    if not m:
        return None
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    month = months[m.group(1).lower()]
    year_m = re.search(r"\b(20\d{2})\b", filename)
    year = int(year_m.group(1)) if year_m else 2026
    return f"{year}-{month:02d}"


def month_key_for_date(value) -> str | None:
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.to_period("M").strftime("%Y-%m")
