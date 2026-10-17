"""Data-quality pipeline: score raw and clean datasets."""

from __future__ import annotations

from src.config import Settings
from src.quality import profile_dataset, summarize_scores


def run_quality_pipeline(raw_frames: dict, clean_frames: dict, settings: Settings, logger) -> dict:
    logger.info("QUALITY: profiling raw and clean manufacturing datasets")
    before = [profile_dataset(df, source, "raw", settings) for source, df in raw_frames.items()]
    after = [profile_dataset(df, source, "clean", settings) for source, df in clean_frames.items()]
    before_summary = summarize_scores(before)
    after_summary = summarize_scores(after)
    logger.info(
        "QUALITY: overall score %.2f -> %.2f",
        before_summary["overall_score"],
        after_summary["overall_score"],
    )
    return {
        "before": before_summary,
        "after": after_summary,
        "before_scores": [item.as_dict() for item in before],
        "after_scores": [item.as_dict() for item in after],
    }
