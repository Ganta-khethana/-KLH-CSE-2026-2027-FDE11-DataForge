"""Extract manufacturing files from the raw landing zone."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import Settings
from src.generate_data import write_raw_datasets


def extract_raw_sources(settings: Settings, generate_if_missing: bool = True) -> dict[str, pd.DataFrame]:
    missing = []
    frames: dict[str, pd.DataFrame] = {}
    for source, filename in settings.pipeline["sources"].items():
        path = settings.raw_dir / filename
        if not path.exists():
            missing.append(source)
            continue
        frames[source] = pd.read_csv(path, dtype="object")
    if missing and generate_if_missing:
        write_raw_datasets(settings.raw_dir)
        return extract_raw_sources(settings, generate_if_missing=False)
    if missing:
        raise FileNotFoundError(f"Raw files missing for sources: {', '.join(missing)}")
    return frames


def write_staging_files(frames: dict[str, pd.DataFrame], staging_dir: Path) -> dict[str, Path]:
    staging_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for source, df in frames.items():
        path = staging_dir / f"{source}.csv"
        df.to_csv(path, index=False)
        written[source] = path
    return written
