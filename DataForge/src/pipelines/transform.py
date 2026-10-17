"""Transform pipeline: PySpark or pandas cleaning and standardization."""

from __future__ import annotations

from src.config import Settings
from src.spark_etl import run_spark_clean, spark_available
from src.transforms import clean_source


def run_transform_pipeline(raw_frames: dict, settings: Settings, logger) -> dict:
    engine = settings.engine
    spark = None
    if engine == "spark":
        if not spark_available():
            logger.warning("TRANSFORM: PySpark is not installed; falling back to pandas")
            engine = "pandas"
        else:
            try:
                logger.info("TRANSFORM: running PySpark ETL")
                clean_frames, quarantine_frames, spark = run_spark_clean(raw_frames, settings)
                return {
                    "engine": "spark",
                    "clean_frames": clean_frames,
                    "quarantine_frames": quarantine_frames,
                    "spark": spark,
                }
            except Exception as exc:
                logger.warning("TRANSFORM: Spark failed (%s); falling back to pandas", exc)
                engine = "pandas"

    logger.info("TRANSFORM: running pandas ETL")
    clean_frames = {}
    quarantine_frames = {}
    for source, df in raw_frames.items():
        cleaned, quarantined = clean_source(source, df, settings)
        clean_frames[source] = cleaned
        quarantine_frames[source] = quarantined
        logger.info(
            "TRANSFORM: %s raw=%s clean=%s quarantined=%s",
            source,
            len(df),
            len(cleaned),
            len(quarantined),
        )
    return {
        "engine": engine,
        "clean_frames": clean_frames,
        "quarantine_frames": quarantine_frames,
        "spark": spark,
    }
