"""Ingestion pipeline: extract raw departmental files and publish to Kafka/file bus."""

from __future__ import annotations

from src.config import Settings
from src.ingestion import extract_raw_sources, write_staging_files
from src.kafka_io import dataframe_to_records, get_bus


def run_ingest_pipeline(settings: Settings, run_id: str, logger) -> dict:
    logger.info("INGEST: reading manufacturing source files")
    raw_frames = extract_raw_sources(settings)
    write_staging_files(raw_frames, settings.staging_dir)

    bus = get_bus(settings)
    bus.reset()
    published = {}
    topics = settings.pipeline["kafka"]["topics"]
    if hasattr(bus, "ensure_topics"):
        bus.ensure_topics(list(topics.values()))
        logger.info("INGEST: using Apache Kafka at %s", settings.kafka_servers)
    else:
        logger.info("INGEST: using local file bus (Kafka disabled)")
    for source, df in raw_frames.items():
        topic = topics[source]
        count = bus.publish(topic, dataframe_to_records(df, source, run_id))
        published[source] = {"topic": topic, "records": count}
        logger.info("INGEST: published %s records to %s", count, topic)

    return {"raw_frames": raw_frames, "published": published, "bus": bus}
