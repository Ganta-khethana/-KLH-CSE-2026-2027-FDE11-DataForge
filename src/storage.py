"""Load validated datasets into SQLite or MySQL."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, text

from src.config import Settings

TABLES = {
    "production": "fact_production",
    "sensors": "fact_sensors",
    "inventory": "fact_inventory",
    "maintenance": "fact_maintenance",
    "quality": "fact_quality",
}

SQLITE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS pipeline_runs (
        run_id TEXT PRIMARY KEY,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        engine TEXT NOT NULL,
        storage_backend TEXT NOT NULL,
        status TEXT NOT NULL,
        records_in INTEGER DEFAULT 0,
        records_out INTEGER DEFAULT 0,
        records_quarantined INTEGER DEFAULT 0,
        overall_score_before REAL,
        overall_score_after REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dq_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        source_name TEXT NOT NULL,
        stage TEXT NOT NULL,
        completeness REAL NOT NULL,
        uniqueness REAL NOT NULL,
        validity REAL NOT NULL,
        consistency REAL NOT NULL,
        timeliness REAL NOT NULL,
        overall_score REAL NOT NULL,
        row_count INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fact_production (
        production_id TEXT NOT NULL,
        plant_id TEXT NOT NULL,
        line_id TEXT NOT NULL,
        machine_id TEXT NOT NULL,
        product_code TEXT NOT NULL,
        shift TEXT NOT NULL,
        operator_id TEXT,
        quantity REAL NOT NULL,
        cycle_time_sec REAL NOT NULL,
        status TEXT NOT NULL,
        event_ts TEXT NOT NULL,
        run_id TEXT NOT NULL,
        PRIMARY KEY (production_id, event_ts)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fact_sensors (
        sensor_id TEXT NOT NULL,
        machine_id TEXT NOT NULL,
        temperature_c REAL NOT NULL,
        vibration_mms REAL NOT NULL,
        pressure_bar REAL NOT NULL,
        humidity_pct REAL NOT NULL,
        event_ts TEXT NOT NULL,
        run_id TEXT NOT NULL,
        PRIMARY KEY (sensor_id, event_ts)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fact_inventory (
        sku TEXT NOT NULL,
        warehouse_id TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT NOT NULL,
        reorder_level REAL NOT NULL,
        event_ts TEXT NOT NULL,
        run_id TEXT NOT NULL,
        PRIMARY KEY (sku, warehouse_id, event_ts)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fact_maintenance (
        ticket_id TEXT PRIMARY KEY,
        machine_id TEXT NOT NULL,
        maintenance_type TEXT NOT NULL,
        downtime_hours REAL NOT NULL,
        technician_id TEXT,
        event_ts TEXT NOT NULL,
        run_id TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fact_quality (
        inspection_id TEXT PRIMARY KEY,
        batch_id TEXT NOT NULL,
        product_code TEXT NOT NULL,
        defect_count INTEGER NOT NULL,
        defect_type TEXT,
        result TEXT NOT NULL,
        inspector_id TEXT,
        event_ts TEXT NOT NULL,
        run_id TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quarantine_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        source_name TEXT NOT NULL,
        dq_reason TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
]


def make_engine(settings: Settings):
    if settings.storage_backend == "mysql":
        return create_engine(settings.mysql_url, future=True, pool_pre_ping=True)
    return create_engine(f"sqlite:///{settings.sqlite_path}", future=True)


def init_schema(engine, settings: Settings) -> None:
    if settings.storage_backend == "mysql":
        sql_path = settings.root / "sql" / "schema.sql"
        script = sql_path.read_text(encoding="utf-8")
        statements = [part.strip() for part in script.split(";") if part.strip() and not part.strip().startswith("CREATE DATABASE") and not part.strip().upper().startswith("USE ")]
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))
        return
    with engine.begin() as conn:
        for ddl in SQLITE_DDL:
            conn.execute(text(ddl))


def load_clean_tables(engine, clean_frames: dict[str, pd.DataFrame], run_id: str) -> dict[str, int]:
    counts = {}
    for source, df in clean_frames.items():
        table = TABLES[source]
        payload = df.copy()
        payload["run_id"] = run_id
        if "event_ts" in payload.columns:
            payload["event_ts"] = pd.to_datetime(payload["event_ts"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        payload.to_sql(table, engine, if_exists="replace", index=False)
        counts[source] = int(len(payload))
    return counts


def load_quarantine(engine, quarantine_frames: dict[str, pd.DataFrame], run_id: str) -> int:
    rows = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    for source, df in quarantine_frames.items():
        if df.empty:
            continue
        for record in df.to_dict(orient="records"):
            reason = record.pop("dq_reason", "UNKNOWN")
            rows.append(
                {
                    "run_id": run_id,
                    "source_name": source,
                    "dq_reason": reason,
                    "payload_json": pd.Series(record).to_json(),
                    "created_at": now,
                }
            )
    if not rows:
        return 0
    pd.DataFrame(rows).to_sql("quarantine_records", engine, if_exists="replace", index=False)
    return len(rows)


def load_metrics(engine, before: list[dict], after: list[dict], run_id: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for stage, scores in (("raw", before), ("clean", after)):
        for item in scores:
            rows.append(
                {
                    "run_id": run_id,
                    "source_name": item["source_name"],
                    "stage": stage,
                    "completeness": item["completeness"],
                    "uniqueness": item["uniqueness"],
                    "validity": item["validity"],
                    "consistency": item["consistency"],
                    "timeliness": item["timeliness"],
                    "overall_score": item["overall_score"],
                    "row_count": item["row_count"],
                    "created_at": now,
                }
            )
    pd.DataFrame(rows).to_sql("dq_metrics", engine, if_exists="replace", index=False)


def record_pipeline_run(engine, payload: dict) -> None:
    df = pd.DataFrame([payload])
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM pipeline_runs WHERE run_id = :run_id"), {"run_id": payload["run_id"]})
    df.to_sql("pipeline_runs", engine, if_exists="append", index=False)
