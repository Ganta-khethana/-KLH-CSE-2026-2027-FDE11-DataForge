"""Data-quality profiling, scoring, and rule evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

import pandas as pd

from src.config import Settings


@dataclass
class QualityScore:
    source_name: str
    stage: str
    row_count: int
    completeness: float
    uniqueness: float
    validity: float
    consistency: float
    timeliness: float
    overall_score: float

    def as_dict(self) -> dict:
        payload = asdict(self)
        for key, value in payload.items():
            if isinstance(value, float):
                payload[key] = round(value, 4)
        return payload


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (numerator / denominator)))


def completeness_score(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    total = df.size
    missing = int(df.isna().sum().sum())
    return _ratio(missing, total)


def uniqueness_score(df: pd.DataFrame, key_columns: list[str]) -> float:
    if df.empty:
        return 0.0
    available = [c for c in key_columns if c in df.columns]
    if not available:
        duplicate_count = int(df.duplicated().sum())
        return _ratio(duplicate_count, len(df))
    duplicate_count = int(df.duplicated(subset=available).sum())
    return _ratio(duplicate_count, len(df))


def _parse_ts(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=True)


def validity_score(df: pd.DataFrame, rules: dict) -> float:
    if df.empty:
        return 0.0
    violations = 0
    checks = 0
    for column, bounds in (rules.get("numeric_ranges") or {}).items():
        if column not in df.columns:
            continue
        numeric = pd.to_numeric(df[column], errors="coerce")
        checks += len(df)
        bad = numeric.isna() | (numeric < bounds["min"]) | (numeric > bounds["max"])
        violations += int(bad.sum())
    for column, allowed in (rules.get("allowed_values") or {}).items():
        if column not in df.columns:
            continue
        checks += len(df)
        normalized = df[column].astype("string").str.strip().str.upper()
        violations += int((~normalized.isin(allowed) | normalized.isna()).sum())
    if checks == 0:
        return 1.0
    return _ratio(violations, checks)


def consistency_score(df: pd.DataFrame, source_name: str) -> float:
    if df.empty:
        return 0.0
    issues = 0
    checks = 0
    object_cols = [c for c in df.columns if df[c].dtype == object or str(df[c].dtype) == "string"]
    for column in object_cols:
        values = df[column].dropna().astype(str)
        checks += len(values)
        padded = values.str.match(r"^\s+|\s+$", na=False)
        issues += int(padded.sum())
        mixed_case = values != values.str.upper()
        if column in {"shift", "status", "unit", "result", "maintenance_type", "product_code", "sku"}:
            issues += int(mixed_case.sum())
    if source_name == "quality" and {"defect_count", "result"}.issubset(df.columns):
        numeric = pd.to_numeric(df["defect_count"], errors="coerce")
        result = df["result"].astype("string").str.strip().str.upper()
        checks += len(df)
        inconsistent = ((numeric > 0) & result.isin(["PASS", "Y", "1", "OK"])) | (
            (numeric == 0) & result.isin(["FAIL", "N", "0", "NOK"])
        )
        issues += int(inconsistent.fillna(False).sum())
    if checks == 0:
        return 1.0
    return _ratio(issues, checks)


def timeliness_score(df: pd.DataFrame, timestamp_column: str | None) -> float:
    if df.empty:
        return 0.0
    if not timestamp_column or timestamp_column not in df.columns:
        return 1.0
    parsed = _parse_ts(df[timestamp_column])
    parseable = parsed.notna()
    start = datetime(2026, 8, 1)
    end = datetime(2026, 9, 30)
    in_window = parseable & (parsed >= start) & (parsed <= end)
    return float(in_window.mean()) if len(df) else 0.0


def profile_dataset(df: pd.DataFrame, source_name: str, stage: str, settings: Settings) -> QualityScore:
    rules = settings.quality_rules.get(source_name, {})
    weights = settings.pipeline["quality"]["weights"]
    completeness = completeness_score(df)
    uniqueness = uniqueness_score(df, rules.get("key_columns", []))
    validity = validity_score(df, rules)
    consistency = consistency_score(df, source_name)
    timeliness = timeliness_score(df, rules.get("timestamp_column"))
    overall = (
        completeness * weights["completeness"]
        + uniqueness * weights["uniqueness"]
        + validity * weights["validity"]
        + consistency * weights["consistency"]
        + timeliness * weights["timeliness"]
    )
    return QualityScore(
        source_name=source_name,
        stage=stage,
        row_count=int(len(df)),
        completeness=completeness * 100,
        uniqueness=uniqueness * 100,
        validity=validity * 100,
        consistency=consistency * 100,
        timeliness=timeliness * 100,
        overall_score=overall * 100,
    )


def summarize_scores(scores: list[QualityScore]) -> dict:
    if not scores:
        return {"overall_score": 0.0, "row_count": 0}
    total_rows = sum(item.row_count for item in scores)
    if total_rows == 0:
        overall = 0.0
    else:
        overall = sum(item.overall_score * item.row_count for item in scores) / total_rows
    return {
        "overall_score": round(overall, 4),
        "row_count": total_rows,
        "by_source": [item.as_dict() for item in scores],
    }
