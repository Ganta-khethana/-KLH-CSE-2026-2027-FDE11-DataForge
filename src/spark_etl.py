"""Optional Apache Spark / PySpark ETL engine.

Used when PIPELINE_ENGINE=spark. Spark performs distributed standardization
(trim, upper, timestamp parse, deduplication). Domain range validation then
reuses the project cleaning rules so rejected records still get reason codes.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import Settings
from src.transforms import clean_source


def spark_available() -> bool:
    try:
        import pyspark  # noqa: F401

        return True
    except Exception:
        return False


def _build_session(settings: Settings):
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.appName("DataForgeETL")
        .master(settings.spark_master)
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def _trim_all(df):
    from pyspark.sql import functions as F

    for column, dtype in df.dtypes:
        if dtype == "string":
            df = df.withColumn(column, F.trim(F.col(column)))
            df = df.withColumn(
                column,
                F.when(F.col(column).isin("", "None", "nan", "NaN"), None).otherwise(F.col(column)),
            )
    return df


def standardize_with_spark(spark, source: str, pdf: pd.DataFrame) -> pd.DataFrame:
    from pyspark.sql import functions as F

    sdf = spark.createDataFrame(pdf.astype(str))
    sdf = _trim_all(sdf).dropna(how="all")
    if "product_code" in sdf.columns:
        sdf = sdf.withColumn("product_code", F.upper(F.col("product_code")))
    if "sku" in sdf.columns:
        sdf = sdf.withColumn("sku", F.upper(F.col("sku")))
    key_guess = {
        "production": ["production_id", "event_ts"],
        "sensors": ["sensor_id", "event_ts"],
        "inventory": ["sku", "warehouse_id", "event_ts"],
        "maintenance": ["ticket_id"],
        "quality": ["inspection_id"],
    }
    keys = [c for c in key_guess.get(source, []) if c in sdf.columns]
    if keys:
        sdf = sdf.dropDuplicates(keys)
    return sdf.toPandas()


def run_spark_clean(
    raw_frames: dict[str, pd.DataFrame], settings: Settings
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], Any]:
    spark = _build_session(settings)
    clean_frames: dict[str, pd.DataFrame] = {}
    quarantine_frames: dict[str, pd.DataFrame] = {}
    for source, pdf in raw_frames.items():
        spark_std = standardize_with_spark(spark, source, pdf)
        cleaned, quarantined = clean_source(source, spark_std, settings)
        clean_frames[source] = cleaned
        quarantine_frames[source] = quarantined
    return clean_frames, quarantine_frames, spark
