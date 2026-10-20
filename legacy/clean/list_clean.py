import os

import pandas as pd

from dashboard.taxonomy import load_equip_type_map, normalize_equip_type, norm_equip_id, infer_equip_category_from_name

INPUT_DIR = os.path.join("data", "equipment", "raw")
TYPE_CSV = os.path.join("data", "equipment", "purchase", "Type.csv")
OUTPUT_DIR = os.path.join("data", "equipment", "cleaned")
SUMMARY_NAME = "all_equipment_summary.csv"

TARGET_COLS = [
    "EquipmentId",
    "Name",
    "Location",
    "EquipType",
    "Manufacturer",
    "SerialNumber",
    "PurchaseDate",
    "DepreciationYears",
    "Cost",
    "Age",
]

_RENAME = {
    "Equipment ID": "EquipmentId",
    "Equip. Name": "Name",
    "EquipmentName": "Name",
    "Equip. Type": "EquipType",
    "Serial Number": "SerialNumber",
    "Depreciation Yrs": "DepreciationYears",
    "Purch. Date": "PurchaseDate",
    "Purch. Cost": "Cost",
    "Current Value": "CurrentValue",
}


def _norm_header_token(s: str) -> str:
    t = str(s).strip().lstrip("\ufeff").lower().replace(".", " ").replace("_", " ")
    return "".join(t.split())


def _row_looks_like_equipment_header(row) -> bool:
    for x in row:
        if pd.isna(x) or str(x).strip() == "":
            continue
        if _norm_header_token(x) == "equipmentid":
            return True
    return False


def _detect_header_row(filepath: str, max_scan: int = 40) -> int | None:
    peek = pd.read_csv(
        filepath,
        header=None,
        nrows=max_scan,
        dtype=str,
        encoding_errors="replace",
    )
    for i in range(len(peek)):
        if _row_looks_like_equipment_header(peek.iloc[i]):
            return i
    return None


def _extract_location(series: pd.Series) -> pd.Series:
    """e.g. 'Location: Hinckley 153' -> 'Hinckley 153'."""
    return (
        series.astype(str)
        .str.replace(r"^Location:\s*", "", regex=True)
        .str.strip()
        .replace({"nan": pd.NA, "": pd.NA})
    )


def _prepare_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={k: v for k, v in _RENAME.items() if k in df.columns})
    if "Location" not in df.columns and "PersonnelId1" in df.columns:
        df["Location"] = _extract_location(df["PersonnelId1"])
    if "#" in df.columns:
        df = df.drop(columns=["#"], errors="ignore")
    if "CurrentValue" in df.columns:
        if "Cost" not in df.columns:
            df["Cost"] = df["CurrentValue"]
        else:
            df["Cost"] = df["Cost"].fillna(df["CurrentValue"])
        df = df.drop(columns=["CurrentValue"], errors="ignore")
    return df


def _read_with_header_skip(filepath: str, skip: int) -> pd.DataFrame:
    df = pd.read_csv(
        filepath,
        skiprows=list(range(skip)),
        header=0,
        encoding_errors="replace",
    )
    df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
    return _prepare_columns(df)


def read_equipment_table(filepath: str) -> pd.DataFrame:
    """Raw Compuclean export or already-cleaned CSV with standard headers."""
    if os.path.basename(filepath) == SUMMARY_NAME:
        df = pd.read_csv(filepath, encoding_errors="replace")
        df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
        return df

    found = _detect_header_row(filepath)
    tries = []
    if found is not None:
        tries.append(found)
    for s in (1, 0):
        if s not in tries:
            tries.append(s)

    last_cols = None
    for skip in tries:
        df = _read_with_header_skip(filepath, skip)
        last_cols = list(df.columns)
        if "EquipmentId" in df.columns and "Name" in df.columns:
            return df

    raise ValueError(
        "Missing EquipmentId/Name after reading. "
        f"Tried header row offsets {tries!r}. Columns: {last_cols!r}"
    )


def clean_equipment_file(filepath: str) -> pd.DataFrame:
    df = read_equipment_table(filepath)

    df = df[
        (df["EquipmentId"].notna())
        & (df["Name"].notna())
        & (~df["Name"].astype(str).str.contains(r"\(Repair\)|\(PM\)", na=False))
    ]

    df = df[[c for c in TARGET_COLS if c != "Age" and c in df.columns]]

    df["EquipmentId"] = (
        df["EquipmentId"].astype(str).str.replace(" ", "", regex=False).str.strip()
    )

    if "Cost" in df.columns:
        df["Cost"] = (
            df["Cost"].astype(str).str.replace(r"[\$,]", "", regex=True)
        )
        df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce")

    if "PurchaseDate" in df.columns:
        df["PurchaseDate"] = pd.to_datetime(df["PurchaseDate"], errors="coerce")
        df = df.sort_values(by="PurchaseDate", ascending=False)

    df = df.drop_duplicates(subset="EquipmentId", keep="first")

    if "PurchaseDate" in df.columns:
        today = pd.Timestamp.today()
        df["Age"] = (today - df["PurchaseDate"]).dt.days / 365

    for col in TARGET_COLS:
        if col not in df.columns:
            df[col] = pd.NA

    type_map = load_equip_type_map(TYPE_CSV)
    if type_map:
        missing = df["EquipType"].map(normalize_equip_type) == ""
        df.loc[missing, "EquipType"] = df.loc[missing, "EquipmentId"].map(
            lambda x: type_map.get(norm_equip_id(x), pd.NA)
        )

    missing = df["EquipType"].map(normalize_equip_type) == ""
    if missing.any() and "Name" in df.columns:
        df.loc[missing, "EquipType"] = df.loc[missing, "Name"].map(
            lambda n: infer_equip_category_from_name(n) or pd.NA
        )

    return df[TARGET_COLS]


def _dedupe_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame(columns=TARGET_COLS)
    out = pd.concat(frames, ignore_index=True)
    if "PurchaseDate" in out.columns:
        out["PurchaseDate"] = pd.to_datetime(out["PurchaseDate"], errors="coerce")
        out = out.sort_values(by="PurchaseDate", ascending=False)
    return out.drop_duplicates(subset="EquipmentId", keep="first")[TARGET_COLS]


def _load_existing_cleaned() -> list[pd.DataFrame]:
    """Previously cleaned per-file CSVs in OUTPUT_DIR (not the summary)."""
    if not os.path.isdir(OUTPUT_DIR):
        return []
    frames = []
    for name in sorted(os.listdir(OUTPUT_DIR)):
        if not name.endswith(".csv") or name == SUMMARY_NAME:
            continue
        path = os.path.join(OUTPUT_DIR, name)
        if not os.path.isfile(path):
            continue
        print(f"Merging existing: {name}")
        frames.append(clean_equipment_file(path))
    return frames


def main():
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    new_frames: list[pd.DataFrame] = []
    raw_files = sorted(
        f for f in os.listdir(INPUT_DIR) if f.endswith(".csv") and os.path.isfile(
            os.path.join(INPUT_DIR, f)
        )
    )

    if not raw_files:
        print(f"No CSV in {INPUT_DIR} — will only merge existing cleaned files.")

    for file in raw_files:
        filepath = os.path.join(INPUT_DIR, file)
        print(f"Processing: {file}")
        cleaned_df = clean_equipment_file(filepath)
        out = os.path.join(OUTPUT_DIR, file.replace(".csv", "_cleaned.csv"))
        cleaned_df.to_csv(out, index=False)
        new_frames.append(cleaned_df)

    # Re-read cleaned folder so prior *_cleaned.csv are included in the summary.
    all_frames = _load_existing_cleaned()
    if not all_frames and not new_frames:
        print(f"Nothing to merge. Put exports in {INPUT_DIR}")
        return

    final_df = _dedupe_frames(all_frames)
    final_df.to_csv(os.path.join(OUTPUT_DIR, SUMMARY_NAME), index=False)
    print(f"Done: {os.path.join(OUTPUT_DIR, SUMMARY_NAME)} ({len(final_df)} rows)")


if __name__ == "__main__":
    main()
