"""Streaming pipeline: consume Kafka/file-bus topics in micro-batches."""

from __future__ import annotations

import pandas as pd

from src.config import Settings
from src.kafka_io import records_to_dataframe
from src.transforms import clean_source


def run_stream_pipeline(bus, settings: Settings, logger) -> dict[str, pd.DataFrame]:
    logger.info("STREAM: consuming manufacturing topics")
    topics = settings.pipeline["kafka"]["topics"]
    consumed = {}
    for source, topic in topics.items():
        records = bus.consume(topic)
        df = records_to_dataframe(records)
        consumed[source] = df
        logger.info("STREAM: consumed %s records from %s", len(df), topic)
    return consumed


def stream_and_clean(bus, settings: Settings, logger) -> dict:
    consumed = run_stream_pipeline(bus, settings, logger)
    clean_frames = {}
    quarantine_frames = {}
    for source, df in consumed.items():
        if df.empty:
            clean_frames[source] = df
            quarantine_frames[source] = df
            continue
        cleaned, quarantined = clean_source(source, df, settings)
        clean_frames[source] = cleaned
        quarantine_frames[source] = quarantined
    return {"raw_frames": consumed, "clean_frames": clean_frames, "quarantine_frames": quarantine_frames}
