"""Generate dirty manufacturing datasets for the DataForge Review 3 demo.

The generator simulates five source systems in one Hyderabad plant:
production, machine sensors, inventory, maintenance, and quality inspection.

Intentional data-quality issues are injected so the ETL pipeline can
demonstrate measurable improvement:
missing values, duplicates, invalid ranges, mixed date formats,
inconsistent labels, extra whitespace, and unparseable numbers.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import load_settings
from src.schemas import SOURCE_COLUMNS

RNG = np.random.default_rng(42)

PLANT_ID = "PLANT-HYD-01"
LINES = ["L1", "L2", "L3", "L4"]
MACHINES = [f"M-{i:03d}" for i in range(101, 121)]
PRODUCTS = ["GEAR-A", "SHAFT-B", "BOLT-C", "HOUSING-D", "BEARING-E"]
SHIFTS = ["A", "B", "C"]
STATUSES = ["RUNNING", "STOPPED", "IDLE"]
WAREHOUSES = ["WH-A", "WH-B", "WH-C"]
UNITS = ["PCS", "KG", "L"]
MAINT_TYPES = ["PREVENTIVE", "CORRECTIVE", "PREDICTIVE"]
DEFECT_TYPES = ["NONE", "SURFACE", "DIMENSION", "CRACK", "ASSEMBLY"]
SKUS = [f"SKU-{code}" for code in PRODUCTS]


def _ids(prefix: str, n: int) -> list[str]:
    return [f"{prefix}-{i:06d}" for i in range(1, n + 1)]


def _base_timestamps(n: int, days: int = 14) -> list[datetime]:
    start = datetime(2026, 9, 1, 6, 0, 0)
    offsets = RNG.integers(0, days * 24 * 60, size=n)
    return [start + timedelta(minutes=int(m)) for m in offsets]


def _dirty_timestamp(value: datetime) -> object:
    mode = int(RNG.choice([0, 1, 2, 3, 4, 5], p=[0.5, 0.18, 0.12, 0.1, 0.05, 0.05]))
    if mode == 0:
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if mode == 1:
        return value.strftime("%d/%m/%Y %H:%M")
    if mode == 2:
        return value.strftime("%d-%m-%Y %H:%M:%S")
    if mode == 3:
        return value.strftime("%Y/%m/%d %H:%M:%S")
    if mode == 4:
        return value.strftime("%d %b %Y %H:%M")
    return None


def _inject_missing(series: pd.Series, rate: float) -> pd.Series:
    mask = RNG.random(len(series)) < rate
    out = series.copy()
    out.loc[mask] = None
    return out


def _inject_whitespace(series: pd.Series, rate: float = 0.03) -> pd.Series:
    out = series.astype("object").copy()
    mask = RNG.random(len(series)) < rate
    out.loc[mask] = out.loc[mask].map(lambda x: f"  {x}  " if pd.notna(x) else x)
    return out


def _messy_shift(values: pd.Series) -> pd.Series:
    mapping_pool = {
        "A": ["A", "a", "Shift A", "1"],
        "B": ["B", "b", "Shift B", "2"],
        "C": ["C", "c", "night", "3"],
    }
    out = []
    for value in values:
        choices = mapping_pool.get(value, [value])
        out.append(choices[int(RNG.integers(0, len(choices)))])
    return pd.Series(out)


def _messy_status(values: pd.Series) -> pd.Series:
    mapping_pool = {
        "RUNNING": ["RUNNING", "running", "Run", "ON"],
        "STOPPED": ["STOPPED", "stopped", "Stop", "OFF"],
        "IDLE": ["IDLE", "idle", "Idle", "wait"],
    }
    out = []
    for value in values:
        choices = mapping_pool.get(value, [value])
        out.append(choices[int(RNG.integers(0, len(choices)))])
    return pd.Series(out)


def _messy_result(values: pd.Series) -> pd.Series:
    mapping_pool = {
        "PASS": ["PASS", "Pass", "pass", "Y", "1", "OK"],
        "FAIL": ["FAIL", "Fail", "fail", "N", "0", "NOK"],
    }
    out = []
    for value in values:
        choices = mapping_pool.get(value, [value])
        out.append(choices[int(RNG.integers(0, len(choices)))])
    return pd.Series(out)


def _messy_unit(values: pd.Series) -> pd.Series:
    mapping_pool = {
        "PCS": ["PCS", "pcs", "Pieces", "pcs."],
        "KG": ["KG", "kg", "Kg", "kgs"],
        "L": ["L", "l", "Litre", "liter"],
    }
    out = []
    for value in values:
        choices = mapping_pool.get(value, [value])
        out.append(choices[int(RNG.integers(0, len(choices)))])
    return pd.Series(out)


def _messy_maint(values: pd.Series) -> pd.Series:
    mapping_pool = {
        "PREVENTIVE": ["PREVENTIVE", "preventive", "PM"],
        "CORRECTIVE": ["CORRECTIVE", "corrective", "breakdown"],
        "PREDICTIVE": ["PREDICTIVE", "predictive", "PdM"],
    }
    out = []
    for value in values:
        choices = mapping_pool.get(value, [value])
        out.append(choices[int(RNG.integers(0, len(choices)))])
    return pd.Series(out)


def _add_duplicates(df: pd.DataFrame, rate: float = 0.04) -> pd.DataFrame:
    n = max(1, int(len(df) * rate))
    dupes = df.sample(n=n, random_state=42)
    return pd.concat([df, dupes], ignore_index=True)


def _corrupt_numeric(series: pd.Series, rate: float = 0.015) -> pd.Series:
    out = series.astype("object").copy()
    mask = RNG.random(len(series)) < rate
    out.loc[mask] = "twelve"
    return out


def generate_production(n: int = 3000) -> pd.DataFrame:
    ts = _base_timestamps(n)
    quantity = RNG.integers(20, 480, size=n).astype(float)
    cycle = RNG.uniform(8, 120, size=n).round(2)
    invalid = RNG.random(n) < 0.03
    quantity[invalid] = RNG.choice([-18, 12500, 18000], size=int(invalid.sum()))
    cycle_invalid = RNG.random(n) < 0.02
    cycle[cycle_invalid] = RNG.choice([0.2, 900, 1200], size=cycle_invalid.sum())

    dirty_ts = [_dirty_timestamp(v) for v in ts]
    df = pd.DataFrame(
        {
            "record_id": _ids("PRD", n),
            "production_id": _ids("PO", n),
            "plant_id": PLANT_ID,
            "line_id": RNG.choice(LINES, n),
            "machine_id": RNG.choice(MACHINES, n),
            "product_code": RNG.choice(PRODUCTS, n),
            "shift": RNG.choice(SHIFTS, n),
            "operator_id": [f"OP-{i:03d}" for i in RNG.integers(1, 40, size=n)],
            "quantity": quantity,
            "cycle_time_sec": cycle,
            "status": RNG.choice(STATUSES, n, p=[0.8, 0.12, 0.08]),
            "event_ts": dirty_ts,
        }
    )
    df["shift"] = _messy_shift(df["shift"])
    df["status"] = _messy_status(df["status"])
    df["product_code"] = _inject_whitespace(df["product_code"].str.lower())
    df["quantity"] = _corrupt_numeric(_inject_missing(df["quantity"], 0.06))
    df["cycle_time_sec"] = _inject_missing(df["cycle_time_sec"], 0.04)
    df["operator_id"] = _inject_missing(df["operator_id"], 0.05)
    return _add_duplicates(df)


def generate_sensors(n: int = 5000) -> pd.DataFrame:
    ts = _base_timestamps(n)
    temp = RNG.normal(62, 8, n).round(2)
    vib = np.abs(RNG.normal(4.5, 1.8, n)).round(3)
    pressure = RNG.normal(6.2, 1.1, n).round(2)
    humidity = RNG.normal(48, 10, n).clip(10, 90).round(1)
    temp[RNG.random(n) < 0.06] = RNG.choice([-12, 165, 210])
    vib[RNG.random(n) < 0.05] = RNG.choice([75, 90, 120])
    pressure[RNG.random(n) < 0.04] = RNG.choice([-3, 260])
    humidity[RNG.random(n) < 0.04] = RNG.choice([-8, 140])
    dirty_ts = [_dirty_timestamp(v) for v in ts]
    df = pd.DataFrame(
        {
            "record_id": _ids("SEN", n),
            "sensor_id": _ids("S", n),
            "machine_id": RNG.choice(MACHINES, n),
            "temperature_c": temp,
            "vibration_mms": vib,
            "pressure_bar": pressure,
            "humidity_pct": humidity,
            "event_ts": dirty_ts,
        }
    )
    df["temperature_c"] = _inject_missing(df["temperature_c"], 0.12)
    df["vibration_mms"] = _inject_missing(df["vibration_mms"], 0.10)
    df["pressure_bar"] = _corrupt_numeric(_inject_missing(df["pressure_bar"], 0.08), 0.02)
    return _add_duplicates(df, 0.035)


def generate_inventory(n: int = 1500) -> pd.DataFrame:
    ts = _base_timestamps(n)
    qty = RNG.integers(0, 8000, size=n).astype(float)
    qty[RNG.random(n) < 0.03] = RNG.choice([-40, -12, 150000])
    dirty_ts = [_dirty_timestamp(v) for v in ts]
    df = pd.DataFrame(
        {
            "record_id": _ids("INV", n),
            "sku": RNG.choice(SKUS, n),
            "warehouse_id": RNG.choice(WAREHOUSES, n),
            "quantity": qty,
            "unit": RNG.choice(UNITS, n),
            "reorder_level": RNG.integers(50, 900, size=n).astype(float),
            "event_ts": dirty_ts,
        }
    )
    df["sku"] = _inject_whitespace(df["sku"].str.lower())
    df["unit"] = _messy_unit(df["unit"])
    df["quantity"] = _inject_missing(df["quantity"], 0.05)
    return _add_duplicates(df, 0.03)


def generate_maintenance(n: int = 800) -> pd.DataFrame:
    ts = _base_timestamps(n)
    downtime = np.abs(RNG.normal(2.4, 1.6, n)).round(2)
    downtime[RNG.random(n) < 0.04] = RNG.choice([28, 36, -2])
    dirty_ts = [_dirty_timestamp(v) for v in ts]
    df = pd.DataFrame(
        {
            "record_id": _ids("MNT", n),
            "ticket_id": _ids("TKT", n),
            "machine_id": RNG.choice(MACHINES, n),
            "maintenance_type": RNG.choice(MAINT_TYPES, n, p=[0.55, 0.3, 0.15]),
            "downtime_hours": downtime,
            "technician_id": [f"TECH-{i:02d}" for i in RNG.integers(1, 18, size=n)],
            "event_ts": dirty_ts,
        }
    )
    df["maintenance_type"] = _messy_maint(df["maintenance_type"])
    df["downtime_hours"] = _inject_missing(df["downtime_hours"], 0.06)
    df["technician_id"] = _inject_missing(df["technician_id"], 0.08)
    return _add_duplicates(df, 0.04)


def generate_quality(n: int = 1200) -> pd.DataFrame:
    ts = _base_timestamps(n)
    defects = RNG.integers(0, 12, size=n)
    result = np.where(defects > 0, "FAIL", "PASS")
    # inconsistent pass/fail vs defect_count
    flip = RNG.random(n) < 0.04
    result[flip] = np.where(result[flip] == "PASS", "FAIL", "PASS")
    defects = defects.astype(float)
    defects[RNG.random(n) < 0.02] = RNG.choice([-3, 900])
    dirty_ts = [_dirty_timestamp(v) for v in ts]
    df = pd.DataFrame(
        {
            "record_id": _ids("QTY", n),
            "inspection_id": _ids("INS", n),
            "batch_id": [f"B-{i:05d}" for i in RNG.integers(1, 400, size=n)],
            "product_code": RNG.choice(PRODUCTS, n),
            "defect_count": defects,
            "defect_type": RNG.choice(DEFECT_TYPES, n),
            "result": result,
            "inspector_id": [f"QC-{i:02d}" for i in RNG.integers(1, 12, size=n)],
            "event_ts": dirty_ts,
        }
    )
    df["result"] = _messy_result(df["result"])
    df["product_code"] = _inject_whitespace(df["product_code"])
    df["defect_count"] = _inject_missing(df["defect_count"], 0.05)
    return _add_duplicates(df, 0.035)


GENERATORS = {
    "production": generate_production,
    "sensors": generate_sensors,
    "inventory": generate_inventory,
    "maintenance": generate_maintenance,
    "quality": generate_quality,
}


def write_raw_datasets(raw_dir: Path | None = None) -> dict[str, Path]:
    settings = load_settings()
    target = raw_dir or settings.raw_dir
    target.mkdir(parents=True, exist_ok=True)
    written = {}
    for source, filename in settings.pipeline["sources"].items():
        df = GENERATORS[source]()
        df = df[SOURCE_COLUMNS[source]]
        path = target / filename
        df.to_csv(path, index=False)
        written[source] = path
    return written


def main() -> None:
    written = write_raw_datasets()
    print("Generated raw manufacturing files:")
    for source, path in written.items():
        print(f"  {source:12s} -> {path}")


if __name__ == "__main__":
    main()
