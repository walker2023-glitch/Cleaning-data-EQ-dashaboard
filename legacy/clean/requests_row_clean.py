"""Clean work-request exports from ``data/requests/row/`` into ``data/requests/``."""

from __future__ import annotations

import csv
import os
import re

import pandas as pd

from clean.row_clean_common import infer_month_key_from_name, list_row_files, output_dir, row_input_dir

REQUEST_COLUMNS = [
    "Work Order #",
    "Request Date",
    "Requestor",
    "Request",
    "Assigned To",
]


def _read_requests_table(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        raw = pd.read_csv(path, header=None, encoding_errors="replace")
    elif ext in (".xls", ".xlsx"):
        try:
            raw = pd.read_excel(path, header=None)
        except ImportError as e:
            raise SystemExit(
                "Reading .xls requires xlrd. Install with: pip install xlrd>=2.0.1"
            ) from e
    else:
        raise ValueError(f"Unsupported request export: {path}")

    header_idx = None
    for i in range(min(25, len(raw))):
        first = raw.iat[i, 0]
        if pd.isna(first):
            continue
        if str(first).strip().lower() == "work order #":
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"Could not find 'Work Order #' header in {path}")

    header = [str(c).strip() if not pd.isna(c) else "" for c in raw.iloc[header_idx]]
    df = raw.iloc[header_idx + 1 :].copy()
    df.columns = header[: df.shape[1]]
    df = df.loc[:, [c for c in df.columns if c]]
    return df


def clean_requests_raw(df: pd.DataFrame) -> pd.DataFrame:
    wo_col = "Work Order #"
    if wo_col not in df.columns:
        raise ValueError(f"Missing {wo_col!r} column")

    out = df.copy()
    out = out[out[wo_col].notna()]
    out = out[~out[wo_col].astype(str).str.strip().str.lower().str.startswith("total")]
    out = out[out[wo_col].astype(str).str.strip().ne("")]

    out["Request Date"] = pd.to_datetime(out.get("Request Date"), errors="coerce")
    out = out[out["Request Date"].notna()]
    out["Request Date"] = out["Request Date"].dt.strftime("%m/%d/%Y")

    for col in REQUEST_COLUMNS:
        if col not in out.columns:
            out[col] = "" if col == "Assigned To" else pd.NA

    return out[REQUEST_COLUMNS].reset_index(drop=True)


def _default_output_name(source: str, month_key: str | None) -> str:
    if month_key:
        label = pd.Period(month_key, freq="M").strftime("%B_%Y")
        return f"Work_Orders_{label}_Request.csv"
    stem = re.sub(r"[^\w]+", "_", os.path.splitext(source)[0]).strip("_")
    return f"{stem}_cleaned.csv"


def _write_requests_csv(df: pd.DataFrame, path: str, month_key: str | None) -> None:
    month_label = (
        pd.Period(month_key, freq="M").strftime("%B %Y") if month_key else "Requests"
    )
    title = f"CU Repair WO History — {month_label}"
    preamble = pd.DataFrame(
        [
            [title, "", "", "", ""],
            list(REQUEST_COLUMNS),
        ],
        columns=REQUEST_COLUMNS,
    )
    body = df[REQUEST_COLUMNS]
    pd.concat([preamble, body], ignore_index=True).to_csv(
        path,
        index=False,
        header=False,
        quoting=csv.QUOTE_NONNUMERIC,
    )


def process_file(path: str, out_dir: str) -> str | None:
    raw = _read_requests_table(path)
    cleaned = clean_requests_raw(raw)
    if cleaned.empty:
        print(f"  [skip] No request rows in {os.path.basename(path)}")
        return None

    month_key = infer_month_key_from_name(os.path.basename(path))
    if month_key is None and "Request Date" in cleaned.columns:
        sample = pd.to_datetime(cleaned["Request Date"].iloc[0], format="%m/%d/%Y", errors="coerce")
        if pd.notna(sample):
            month_key = sample.to_period("M").strftime("%Y-%m")

    out_name = _default_output_name(os.path.basename(path), month_key)
    out_path = os.path.join(out_dir, out_name)
    _write_requests_csv(cleaned, out_path, month_key)
    print(f"  Wrote {out_name} ({len(cleaned)} rows)")
    return out_path


def main():
    in_dir = row_input_dir("requests")
    out_dir = output_dir("requests")
    os.makedirs(out_dir, exist_ok=True)

    files = list_row_files("requests", (".csv", ".xls", ".xlsx"))
    if not files:
        print(f"No CSV/XLS files in {in_dir}")
        return

    print(f"Cleaning requests from {in_dir} → {out_dir}")
    for path in files:
        print(f"Processing {path.name}")
        process_file(str(path), str(out_dir))


if __name__ == "__main__":
    main()
