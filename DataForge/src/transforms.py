"""Cleaning, standardization, repair, and quarantine logic."""

from __future__ import annotations

from typing import Callable

import pandas as pd

from src.config import Settings
from src.schemas import CLEAN_COLUMNS

SHIFT_MAP = {
    "A": "A",
    "SHIFT A": "A",
    "1": "A",
    "B": "B",
    "SHIFT B": "B",
    "2": "B",
    "C": "C",
    "SHIFT C": "C",
    "NIGHT": "C",
    "3": "C",
}
STATUS_MAP = {
    "RUNNING": "RUNNING",
    "RUN": "RUNNING",
    "ON": "RUNNING",
    "STOPPED": "STOPPED",
    "STOP": "STOPPED",
    "OFF": "STOPPED",
    "IDLE": "IDLE",
    "WAIT": "IDLE",
}
UNIT_MAP = {
    "PCS": "PCS",
    "PCS.": "PCS",
    "PIECES": "PCS",
    "KG": "KG",
    "KGS": "KG",
    "L": "L",
    "LITRE": "L",
    "LITER": "L",
}
MAINT_MAP = {
    "PREVENTIVE": "PREVENTIVE",
    "PM": "PREVENTIVE",
    "CORRECTIVE": "CORRECTIVE",
    "BREAKDOWN": "CORRECTIVE",
    "PREDICTIVE": "PREDICTIVE",
    "PDM": "PREDICTIVE",
}
RESULT_MAP = {
    "PASS": "PASS",
    "Y": "PASS",
    "1": "PASS",
    "OK": "PASS",
    "FAIL": "FAIL",
    "N": "FAIL",
    "0": "FAIL",
    "NOK": "FAIL",
}


def strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in out.columns:
        if out[column].dtype == object or str(out[column].dtype).startswith("string"):
            out[column] = out[column].astype("string").str.strip()
            out[column] = out[column].replace({"": pd.NA, "None": pd.NA, "nan": pd.NA, "NaN": pd.NA})
    return out


def parse_timestamps(df: pd.DataFrame, column: str) -> pd.DataFrame:
    out = df.copy()
    parsed = pd.to_datetime(out[column], errors="coerce", format="mixed", dayfirst=True)
    fill_value = parsed.median() if parsed.notna().any() else pd.Timestamp("2026-09-07 12:00:00")
    out[column] = parsed.fillna(fill_value)
    return out


def to_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def map_labels(series: pd.Series, mapping: dict[str, str]) -> pd.Series:
    normalized = series.astype("string").str.strip().str.upper()
    return normalized.map(mapping)


def impute_numeric(df: pd.DataFrame, columns: list[str], group_col: str | None = None) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column not in out.columns:
            continue
        if group_col and group_col in out.columns:
            out[column] = out.groupby(group_col)[column].transform(lambda s: s.fillna(s.median()))
        out[column] = out[column].fillna(out[column].median())
    return out


def impute_categorical(df: pd.DataFrame, columns: list[str], default: str = "UNKNOWN") -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column not in out.columns:
            continue
        mode = out[column].mode(dropna=True)
        fill_value = mode.iloc[0] if not mode.empty else default
        out[column] = out[column].fillna(fill_value)
    return out


def split_quarantine(df: pd.DataFrame, mask: pd.Series, reason: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rejected = df.loc[mask].copy()
    kept = df.loc[~mask].copy()
    if not rejected.empty:
        rejected["dq_reason"] = reason
    return kept, rejected


def _concat_quarantine(frames: list[pd.DataFrame]) -> pd.DataFrame:
    valid = [frame for frame in frames if not frame.empty]
    if not valid:
        return pd.DataFrame()
    return pd.concat(valid, ignore_index=True)


def clean_production(df: pd.DataFrame, settings: Settings) -> tuple[pd.DataFrame, pd.DataFrame]:
    rules = settings.quality_rules["production"]
    out = strip_strings(df)
    if "plant_id" not in out.columns:
        out["plant_id"] = "PLANT-HYD-01"
    else:
        out["plant_id"] = out["plant_id"].fillna("PLANT-HYD-01")
    out["product_code"] = out["product_code"].astype("string").str.upper()
    out["shift"] = map_labels(out["shift"], SHIFT_MAP)
    out["status"] = map_labels(out["status"], STATUS_MAP)
    out = parse_timestamps(out, "event_ts")
    out = to_numeric(out, ["quantity", "cycle_time_sec"])
    out = impute_numeric(out, ["quantity", "cycle_time_sec"], group_col="line_id")
    out = impute_categorical(out, ["operator_id", "shift", "status"])

    quarantines: list[pd.DataFrame] = []
    qty_bad = (out["quantity"] < rules["numeric_ranges"]["quantity"]["min"]) | (
        out["quantity"] > rules["numeric_ranges"]["quantity"]["max"]
    )
    out, q = split_quarantine(out, qty_bad.fillna(True), "INVALID_QUANTITY_RANGE")
    quarantines.append(q)
    cycle_bad = (out["cycle_time_sec"] < rules["numeric_ranges"]["cycle_time_sec"]["min"]) | (
        out["cycle_time_sec"] > rules["numeric_ranges"]["cycle_time_sec"]["max"]
    )
    out, q = split_quarantine(out, cycle_bad.fillna(True), "INVALID_CYCLE_TIME")
    quarantines.append(q)
    out, q = split_quarantine(out, out["shift"].isna() | ~out["shift"].isin(rules["allowed_values"]["shift"]), "INVALID_SHIFT")
    quarantines.append(q)
    out, q = split_quarantine(out, out["status"].isna() | ~out["status"].isin(rules["allowed_values"]["status"]), "INVALID_STATUS")
    quarantines.append(q)

    dup_mask = out.duplicated(subset=rules["key_columns"], keep="first")
    out, q = split_quarantine(out, dup_mask, "DUPLICATE")
    quarantines.append(q)
    out = out[CLEAN_COLUMNS["production"]].copy()
    return out.reset_index(drop=True), _concat_quarantine(quarantines)


def clean_sensors(df: pd.DataFrame, settings: Settings) -> tuple[pd.DataFrame, pd.DataFrame]:
    rules = settings.quality_rules["sensors"]
    out = strip_strings(df)
    out = parse_timestamps(out, "event_ts")
    out = to_numeric(out, ["temperature_c", "vibration_mms", "pressure_bar", "humidity_pct"])
    out = impute_numeric(out, ["temperature_c", "vibration_mms", "pressure_bar", "humidity_pct"], "machine_id")
    quarantines: list[pd.DataFrame] = []
    for column, bounds in rules["numeric_ranges"].items():
        bad = (out[column] < bounds["min"]) | (out[column] > bounds["max"])
        out, q = split_quarantine(out, bad.fillna(True), f"INVALID_RANGE_{column.upper()}")
        quarantines.append(q)
    dup_mask = out.duplicated(subset=rules["key_columns"], keep="first")
    out, q = split_quarantine(out, dup_mask, "DUPLICATE")
    quarantines.append(q)
    return out[CLEAN_COLUMNS["sensors"]].reset_index(drop=True), _concat_quarantine(quarantines)


def clean_inventory(df: pd.DataFrame, settings: Settings) -> tuple[pd.DataFrame, pd.DataFrame]:
    rules = settings.quality_rules["inventory"]
    out = strip_strings(df)
    out["sku"] = out["sku"].astype("string").str.upper()
    out["unit"] = map_labels(out["unit"], UNIT_MAP)
    out = parse_timestamps(out, "event_ts")
    out = to_numeric(out, ["quantity", "reorder_level"])
    out = impute_numeric(out, ["quantity", "reorder_level"], "warehouse_id")
    out = impute_categorical(out, ["unit"], default="PCS")
    quarantines: list[pd.DataFrame] = []
    qty_bad = (out["quantity"] < rules["numeric_ranges"]["quantity"]["min"]) | (
        out["quantity"] > rules["numeric_ranges"]["quantity"]["max"]
    )
    out, q = split_quarantine(out, qty_bad.fillna(True), "INVALID_QUANTITY_RANGE")
    quarantines.append(q)
    out, q = split_quarantine(out, out["unit"].isna() | ~out["unit"].isin(rules["allowed_values"]["unit"]), "INVALID_UNIT")
    quarantines.append(q)
    dup_mask = out.duplicated(subset=rules["key_columns"], keep="first")
    out, q = split_quarantine(out, dup_mask, "DUPLICATE")
    quarantines.append(q)
    return out[CLEAN_COLUMNS["inventory"]].reset_index(drop=True), _concat_quarantine(quarantines)


def clean_maintenance(df: pd.DataFrame, settings: Settings) -> tuple[pd.DataFrame, pd.DataFrame]:
    rules = settings.quality_rules["maintenance"]
    out = strip_strings(df)
    out["maintenance_type"] = map_labels(out["maintenance_type"], MAINT_MAP)
    out = parse_timestamps(out, "event_ts")
    out = to_numeric(out, ["downtime_hours"])
    out = impute_numeric(out, ["downtime_hours"], "machine_id")
    out = impute_categorical(out, ["technician_id", "maintenance_type"])
    quarantines: list[pd.DataFrame] = []
    bad = (out["downtime_hours"] < rules["numeric_ranges"]["downtime_hours"]["min"]) | (
        out["downtime_hours"] > rules["numeric_ranges"]["downtime_hours"]["max"]
    )
    out, q = split_quarantine(out, bad.fillna(True), "INVALID_DOWNTIME")
    quarantines.append(q)
    out, q = split_quarantine(
        out,
        out["maintenance_type"].isna() | ~out["maintenance_type"].isin(rules["allowed_values"]["maintenance_type"]),
        "INVALID_MAINTENANCE_TYPE",
    )
    quarantines.append(q)
    dup_mask = out.duplicated(subset=rules["key_columns"], keep="first")
    out, q = split_quarantine(out, dup_mask, "DUPLICATE")
    quarantines.append(q)
    return out[CLEAN_COLUMNS["maintenance"]].reset_index(drop=True), _concat_quarantine(quarantines)


def clean_quality(df: pd.DataFrame, settings: Settings) -> tuple[pd.DataFrame, pd.DataFrame]:
    rules = settings.quality_rules["quality"]
    out = strip_strings(df)
    out["product_code"] = out["product_code"].astype("string").str.upper()
    out["result"] = map_labels(out["result"], RESULT_MAP)
    out = parse_timestamps(out, "event_ts")
    out = to_numeric(out, ["defect_count"])
    out = impute_numeric(out, ["defect_count"])
    out = impute_categorical(out, ["inspector_id", "defect_type", "result"])
    # repair obvious result/defect inconsistency after standardization
    out.loc[out["defect_count"] > 0, "result"] = "FAIL"
    out.loc[out["defect_count"] == 0, "result"] = "PASS"
    out["defect_count"] = out["defect_count"].round().astype("Int64")
    quarantines: list[pd.DataFrame] = []
    bad = (out["defect_count"] < rules["numeric_ranges"]["defect_count"]["min"]) | (
        out["defect_count"] > rules["numeric_ranges"]["defect_count"]["max"]
    )
    out, q = split_quarantine(out, bad.fillna(True), "INVALID_DEFECT_COUNT")
    quarantines.append(q)
    dup_mask = out.duplicated(subset=rules["key_columns"], keep="first")
    out, q = split_quarantine(out, dup_mask, "DUPLICATE")
    quarantines.append(q)
    out["defect_count"] = out["defect_count"].astype(int)
    return out[CLEAN_COLUMNS["quality"]].reset_index(drop=True), _concat_quarantine(quarantines)


CLEANERS: dict[str, Callable[[pd.DataFrame, Settings], tuple[pd.DataFrame, pd.DataFrame]]] = {
    "production": clean_production,
    "sensors": clean_sensors,
    "inventory": clean_inventory,
    "maintenance": clean_maintenance,
    "quality": clean_quality,
}


def clean_source(source_name: str, df: pd.DataFrame, settings: Settings) -> tuple[pd.DataFrame, pd.DataFrame]:
    if source_name not in CLEANERS:
        raise KeyError(f"No cleaner registered for source '{source_name}'")
    return CLEANERS[source_name](df, settings)
