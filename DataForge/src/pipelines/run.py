"""Review 3 orchestrator for the DataForge manufacturing ETL platform.

Execution flow:
Start -> Load raw manufacturing data -> Ingest (Kafka/file bus) ->
Transform (PySpark/pandas) -> Clean -> Data quality validation ->
Store clean data -> Generate results -> End
"""

from __future__ import annotations

import argparse
import uuid
from datetime import datetime, timezone

from src.config import load_settings
from src.logging_setup import setup_logging
from src.pipelines.ingest import run_ingest_pipeline
from src.pipelines.load import run_load_pipeline
from src.pipelines.quality import run_quality_pipeline
from src.pipelines.stream import stream_and_clean
from src.pipelines.transform import run_transform_pipeline
from src.reporting import export_run_artifacts, write_processed_files


def _count_rows(frames: dict) -> int:
    return int(sum(len(df) for df in frames.values()))


def run(mode: str = "all") -> dict:
    settings = load_settings()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    logger = setup_logging(settings.results_dir / "pipeline_run.log", run_id)
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    logger.info("Starting DataForge pipeline mode=%s run_id=%s", mode, run_id)

    ingest_result = run_ingest_pipeline(settings, run_id, logger)
    raw_frames = ingest_result["raw_frames"]

    if mode in {"stream", "all"}:
        stream_result = stream_and_clean(ingest_result["bus"], settings, logger)
        # Prefer consumed records so streaming ingestion is part of the run.
        if _count_rows(stream_result["raw_frames"]) > 0:
            raw_frames = stream_result["raw_frames"]

    transform_result = run_transform_pipeline(raw_frames, settings, logger)
    quality_result = run_quality_pipeline(
        raw_frames,
        transform_result["clean_frames"],
        settings,
        logger,
    )

    finished_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    run_meta = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "engine": transform_result["engine"],
        "records_in": _count_rows(raw_frames),
        "records_out": _count_rows(transform_result["clean_frames"]),
        "records_quarantined": _count_rows(transform_result["quarantine_frames"]),
    }
    load_result = run_load_pipeline(
        settings,
        transform_result["clean_frames"],
        transform_result["quarantine_frames"],
        quality_result,
        run_meta,
        logger,
    )
    active_settings = load_result["settings"]
    write_processed_files(
        transform_result["clean_frames"],
        transform_result["quarantine_frames"],
        active_settings,
    )
    summary = {
        **run_meta,
        "mode": mode,
        "storage_backend": active_settings.storage_backend,
        "storage_target": load_result["target"],
        "kafka_enabled": settings.kafka_enabled,
        "before": quality_result["before"],
        "after": quality_result["after"],
        "published": ingest_result["published"],
        "stored": load_result["stored"],
    }
    export_run_artifacts(
        summary,
        active_settings,
        quality_result["before_scores"],
        quality_result["after_scores"],
    )
    if transform_result.get("spark") is not None:
        transform_result["spark"].stop()
    logger.info("Pipeline finished successfully. Report: %s", active_settings.reports_dir / "quality_report.md")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DataForge Review 3 ETL pipelines")
    parser.add_argument(
        "--mode",
        choices=["batch", "stream", "all"],
        default="all",
        help="batch = files only, stream = consume bus, all = ingest + stream + ETL + load",
    )
    args = parser.parse_args()
    summary = run(mode=args.mode)
    print("\nDataForge pipeline completed")
    print(f"  Run ID:            {summary['run_id']}")
    print(f"  Engine:            {summary['engine']}")
    print(f"  Storage:           {summary['storage_backend']} ({summary['storage_target']})")
    print(f"  Records in/out:    {summary['records_in']} -> {summary['records_out']}")
    print(f"  Quarantined:       {summary['records_quarantined']}")
    print(f"  Quality before:    {summary['before']['overall_score']:.2f}%")
    print(f"  Quality after:     {summary['after']['overall_score']:.2f}%")


if __name__ == "__main__":
    main()
