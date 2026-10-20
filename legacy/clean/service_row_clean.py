"""Clean service / equipment-detail exports from ``data/service/row/`` into ``data/service/``."""

from __future__ import annotations

import os
import re

import pandas as pd

from clean.row_clean_common import (
    infer_month_key_from_name,
    list_row_files,
    month_key_for_date,
    output_dir,
    parse_dollar,
    row_input_dir,
)

SERVICE_COLUMNS = [
    "Equipment Id",
    "Equipment Name",
    "Sched. Date",
    "Completed Date",
    "Location",
    "Description",
    "Status",
    "Estimated Price",
]

# Compuclean Service Order List (SSRS) column aliases → logical names.
_ORDER_LIST_RENAME = {
    "EquipmentId1": "EquipmentId",
    "EquipmentName1": "EquipmentName",
    "Textbox21": "StatusRaw",
}


def _clean_description(desc: str) -> str:
    s = str(desc).strip()
    s = re.sub(r"\s*-\s*\(Repair\)\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*-\s*\(PM\)\s*$", "", s, flags=re.I)
    return s.strip()


def _is_placeholder_description(desc: str) -> bool:
    s = str(desc).strip().lower()
    return s in ("", "- (repair)", "- (pm)", "nan")


def _cell(row: pd.Series, *keys: str):
    for key in keys:
        if key in row.index:
            return row.get(key)
    return None


def _is_order_list_export(df: pd.DataFrame) -> bool:
    """True for Compuclean Service Order List exports (flat one-row-per-order)."""
    cols = {str(c).lstrip("\ufeff") for c in df.columns}
    return "EquipmentId1" in cols or "EquipmentName1" in cols


def _prepare_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    out = df.copy()
    out.columns = [str(c).lstrip("\ufeff").strip() for c in out.columns]
    is_order_list = _is_order_list_export(out)
    if is_order_list:
        out = out.rename(columns=_ORDER_LIST_RENAME)
        # In order-list exports, ``Name`` is building/room, not equipment name.
        if "Name" in out.columns and "Location" not in out.columns:
            out = out.rename(columns={"Name": "Location"})
    return out, is_order_list

def _append_service_row(
    rows: list[dict],
    *,
    equip_id: str,
    equip_name: str,
    location: str,
    sched_raw,
    comp_raw,
    desc_raw,
    month_key: str | None,
    estimated_price: float = 0.0,
    status_raw=None,
) -> None:
    if pd.isna(sched_raw) or not str(sched_raw).strip():
        return
    if _is_placeholder_description(desc_raw):
        return
    if not equip_id:
        return

    sched = pd.to_datetime(sched_raw, errors="coerce")
    comp = pd.to_datetime(comp_raw, errors="coerce")
    if pd.isna(sched) and pd.isna(comp):
        return

    if month_key:
        keys = {month_key_for_date(sched), month_key_for_date(comp)}
        keys.discard(None)
        if keys and month_key not in keys:
            return

    desc = _clean_description(desc_raw)
    if not desc or desc.lower().startswith("delete duplicate"):
        return

    status_hint = str(status_raw).strip() if pd.notna(status_raw) else ""
    if status_hint.lower() in ("completed", "scheduled"):
        status = status_hint.title()
    else:
        status = "Completed" if pd.notna(comp) else "Scheduled"

    rows.append(
        {
            "Equipment Id": equip_id,
            "Equipment Name": equip_name,
            "Sched. Date": sched.strftime("%Y-%m-%d") if pd.notna(sched) else "",
            "Completed Date": comp.strftime("%Y-%m-%d") if pd.notna(comp) else "",
            "Location": location,
            "Description": desc,
            "Status": status,
            "Estimated Price": estimated_price if estimated_price > 0 else "",
        }
    )


def clean_service_raw(df: pd.DataFrame, month_key: str | None) -> pd.DataFrame:
    df, is_order_list = _prepare_frame(df)
    rows: list[dict] = []

    if is_order_list:
        # Flat Service Order List: one equipment + order per row.
        for _, row in df.iterrows():
            eid = _cell(row, "EquipmentId")
            if pd.isna(eid) or not str(eid).strip():
                continue
            _append_service_row(
                rows,
                equip_id=str(eid).strip(),
                equip_name=str(_cell(row, "EquipmentName") or "").strip(),
                location=str(_cell(row, "Location") or "").strip(),
                sched_raw=_cell(row, "ScheduledDate"),
                comp_raw=_cell(row, "CompletedDate"),
                desc_raw=_cell(row, "Description"),
                month_key=month_key,
                estimated_price=parse_dollar(_cell(row, "Cost")),
                status_raw=_cell(row, "StatusRaw"),
            )
        return pd.DataFrame(rows, columns=SERVICE_COLUMNS)

    # Legacy Equipment Details export: equipment header rows carry context.
    context: dict = {}
    for _, row in df.iterrows():
        eid = _cell(row, "EquipmentId")
        if pd.notna(eid) and str(eid).strip():
            context = {
                "Equipment Id": str(eid).strip(),
                "Equipment Name": str(_cell(row, "Name") or "").strip(),
                "Location": str(_cell(row, "Location") or "").strip(),
                "Estimated Price": parse_dollar(_cell(row, "Cost")),
            }

        _append_service_row(
            rows,
            equip_id=str(context.get("Equipment Id") or ""),
            equip_name=str(context.get("Equipment Name") or ""),
            location=str(context.get("Location") or ""),
            sched_raw=_cell(row, "ScheduledDate"),
            comp_raw=_cell(row, "CompletedDate"),
            desc_raw=_cell(row, "Description"),
            month_key=month_key,
            estimated_price=float(context.get("Estimated Price") or 0.0),
        )

    return pd.DataFrame(rows, columns=SERVICE_COLUMNS)


def _default_output_name(source: str, month_key: str | None) -> str:
    if month_key:
        label = pd.Period(month_key, freq="M").strftime("%B")
        return f"{label}_Service_Orders_with_Prices.csv"
    stem = re.sub(r"[^\w]+", "_", os.path.splitext(source)[0]).strip("_")
    return f"{stem}_cleaned.csv"


def process_file(path: str, out_dir: str) -> str | None:
    df = pd.read_csv(path, encoding_errors="replace")
    month_key = infer_month_key_from_name(os.path.basename(path))
    cleaned = clean_service_raw(df, month_key)
    if cleaned.empty:
        print(f"  [skip] No service rows in {os.path.basename(path)}")
        return None

    out_name = _default_output_name(os.path.basename(path), month_key)
    out_path = os.path.join(out_dir, out_name)
    cleaned.to_csv(out_path, index=False)
    print(f"  Wrote {out_name} ({len(cleaned)} rows)")
    return out_path


def main():
    in_dir = row_input_dir("service")
    out_dir = output_dir("service")
    os.makedirs(out_dir, exist_ok=True)

    files = list_row_files("service", (".csv",))
    if not files:
        print(f"No CSV files in {in_dir}")
        return

    print(f"Cleaning service from {in_dir} → {out_dir}")
    for path in files:
        print(f"Processing {path.name}")
        process_file(str(path), str(out_dir))


if __name__ == "__main__":
    main()
