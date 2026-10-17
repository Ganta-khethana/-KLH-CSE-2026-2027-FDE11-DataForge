"""Load pipeline: persist validated data and metrics."""

from __future__ import annotations

import time

from src.config import Settings
from src.storage import (
    init_schema,
    load_clean_tables,
    load_metrics,
    load_quarantine,
    make_engine,
    record_pipeline_run,
)


def _connect_storage(settings: Settings, logger):
    last_error = None
    attempts = 12 if settings.storage_backend == "mysql" else 1
    for attempt in range(1, attempts + 1):
        try:
            engine = make_engine(settings)
            init_schema(engine, settings)
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            return engine, settings
        except Exception as exc:
            last_error = exc
            logger.warning("LOAD: %s not ready (attempt %s/%s): %s", settings.storage_backend, attempt, attempts, exc)
            time.sleep(5)
    raise RuntimeError(f"Could not connect to {settings.storage_backend}: {last_error}")


def run_load_pipeline(
    settings: Settings,
    clean_frames: dict,
    quarantine_frames: dict,
    quality_result: dict,
    run_meta: dict,
    logger,
) -> dict:
    logger.info("LOAD: initializing %s storage", settings.storage_backend)
    engine, active_settings = _connect_storage(settings, logger)

    stored = load_clean_tables(engine, clean_frames, run_meta["run_id"])
    quarantined = load_quarantine(engine, quarantine_frames, run_meta["run_id"])
    load_metrics(
        engine,
        quality_result["before_scores"],
        quality_result["after_scores"],
        run_meta["run_id"],
    )
    record_pipeline_run(
        engine,
        {
            "run_id": run_meta["run_id"],
            "started_at": run_meta["started_at"],
            "finished_at": run_meta["finished_at"],
            "engine": run_meta["engine"],
            "storage_backend": active_settings.storage_backend,
            "status": "SUCCESS",
            "records_in": run_meta["records_in"],
            "records_out": run_meta["records_out"],
            "records_quarantined": run_meta["records_quarantined"],
            "overall_score_before": quality_result["before"]["overall_score"],
            "overall_score_after": quality_result["after"]["overall_score"],
        },
    )
    logger.info("LOAD: stored clean tables %s; quarantined=%s", stored, quarantined)
    target = (
        str(active_settings.sqlite_path)
        if active_settings.storage_backend == "sqlite"
        else active_settings.mysql_database
    )
    return {
        "engine": engine,
        "stored": stored,
        "quarantined": quarantined,
        "target": target,
        "settings": active_settings,
    }
