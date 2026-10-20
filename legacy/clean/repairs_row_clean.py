"""Clean Compuclean repair exports from ``data/repairs/row/`` into ``data/repairs/``."""

from __future__ import annotations

import os
import re

import pandas as pd

from clean.row_clean_common import (
    LABOR_RATE_PER_HOUR,
    extract_label,
    infer_month_key_from_name,
    list_row_files,
    output_dir,
    parse_dollar,
    parse_repair_hours,
    row_input_dir,
)

OUTPUT_COLUMNS = [
    "#",
    "Completed Date",
    "Equipment Name",
    "Equipment ID",
    "Location",
    "Service Vendor",
    "# of Repairs",
    "Repair Person-Hrs",
    "Parts Cost $",
    "Total Labor $",
    "Est. Total $",
]


def _default_output_name(source: str, month_key: str | None) -> str:
    if month_key:
        label = pd.Period(month_key, freq="M").strftime("%B")
        return f"{label}_Repair_List_All_Work_Orders.csv"
    stem = re.sub(r"[^\w]+", "_", os.path.splitext(source)[0]).strip("_")
    return f"{stem}_cleaned.csv"


def clean_repairs_raw(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, row in df.iterrows():
        equip_name = extract_label(row.get("PersonnelId5"), "Equip. Name")
        equip_id = extract_label(row.get("PersonnelId1"), "Equipment Id")
        if not equip_name and not equip_id:
            continue
        completed = pd.to_datetime(row.get("CompletedDate1"), errors="coerce")
        if pd.isna(completed):
            continue

        location = extract_label(row.get("PersonnelId4"), "Location")
        vendor = extract_label(row.get("PersonnelId3"), "Service Vendor")
        parts = parse_dollar(row.get("Textbox38"))
        hours = parse_repair_hours(row.get("Details"), row)
        labor = round(hours * LABOR_RATE_PER_HOUR, 2)
        total = round(parts + labor, 2)

        rows.append(
            {
                "#": len(rows) + 1,
                "Completed Date": completed.strftime("%Y-%m-%d"),
                "Equipment Name": equip_name,
                "Equipment ID": equip_id,
                "Location": location,
                "Service Vendor": vendor or "—",
                "# of Repairs": 1,
                "Repair Person-Hrs": hours,
                "Parts Cost $": parts,
                "Total Labor $": labor,
                "Est. Total $": total,
            }
        )

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _write_repairs_csv(df: pd.DataFrame, path: str, title: str) -> None:
    """Write the multi-row preamble format expected by ``load_repairs``."""
    header_cells = OUTPUT_COLUMNS
    lines = [
        [title] + [""] * (len(header_cells) - 1),
        [
            f"Generated from row export | Repair lines: {len(df)}",
        ]
        + [""] * (len(header_cells) - 1),
        [""] * len(header_cells),
    ]
    lines.append(header_cells)
    for _, row in df.iterrows():
        lines.append([row[c] for c in OUTPUT_COLUMNS])

    out = pd.DataFrame(lines)
    out.to_csv(path, index=False, header=False)


def process_file(path: str, out_dir: str) -> str | None:
    df = pd.read_csv(path, encoding_errors="replace")
    cleaned = clean_repairs_raw(df)
    if cleaned.empty:
        print(f"  [skip] No repair rows in {os.path.basename(path)}")
        return None

    month_key = infer_month_key_from_name(os.path.basename(path))
    out_name = _default_output_name(os.path.basename(path), month_key)
    out_path = os.path.join(out_dir, out_name)
    title = (
        f"BYU–Idaho  |  Equipment Repair Log  |  "
        f"{pd.Period(month_key, freq='M').strftime('%B %Y') if month_key else 'Repairs'}"
    )
    _write_repairs_csv(cleaned, out_path, title)
    print(f"  Wrote {out_name} ({len(cleaned)} rows)")
    return out_path


def main():
    in_dir = row_input_dir("repairs")
    out_dir = output_dir("repairs")
    os.makedirs(out_dir, exist_ok=True)

    files = list_row_files("repairs", (".csv",))
    if not files:
        print(f"No CSV files in {in_dir}")
        return

    print(f"Cleaning repairs from {in_dir} → {out_dir}")
    for path in files:
        print(f"Processing {path.name}")
        process_file(str(path), str(out_dir))


if __name__ == "__main__":
    main()
