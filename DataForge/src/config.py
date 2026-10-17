"""Load project configuration from YAML and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def _read_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@dataclass(frozen=True)
class Settings:
    root: Path
    engine: str
    storage_backend: str
    kafka_enabled: bool
    kafka_servers: str
    spark_master: str
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str
    pipeline: dict
    quality_rules: dict

    @property
    def raw_dir(self) -> Path:
        return self.root / self.pipeline["paths"]["raw_dir"]

    @property
    def staging_dir(self) -> Path:
        return self.root / self.pipeline["paths"]["staging_dir"]

    @property
    def processed_dir(self) -> Path:
        return self.root / self.pipeline["paths"]["processed_dir"]

    @property
    def quarantine_dir(self) -> Path:
        return self.root / self.pipeline["paths"]["quarantine_dir"]

    @property
    def results_dir(self) -> Path:
        return self.root / self.pipeline["paths"]["results_dir"]

    @property
    def reports_dir(self) -> Path:
        return self.root / self.pipeline["paths"]["reports_dir"]

    @property
    def sqlite_path(self) -> Path:
        return self.results_dir / "dataforge.db"

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    def ensure_directories(self) -> None:
        for path in [
            self.raw_dir,
            self.staging_dir / "topics",
            self.processed_dir,
            self.quarantine_dir,
            self.results_dir,
            self.reports_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    pipeline = _read_yaml(ROOT / "config" / "pipeline.yaml")
    quality_rules = _read_yaml(ROOT / "config" / "quality_rules.yaml")
    settings = Settings(
        root=ROOT,
        engine=os.getenv("PIPELINE_ENGINE", "pandas").strip().lower(),
        storage_backend=os.getenv("STORAGE_BACKEND", "sqlite").strip().lower(),
        kafka_enabled=os.getenv("KAFKA_ENABLED", "false").strip().lower() in {"1", "true", "yes"},
        kafka_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        spark_master=os.getenv("SPARK_MASTER", "local[*]"),
        mysql_host=os.getenv("MYSQL_HOST", "localhost"),
        mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
        mysql_user=os.getenv("MYSQL_USER", "dataforge"),
        mysql_password=os.getenv("MYSQL_PASSWORD", "change_me"),
        mysql_database=os.getenv("MYSQL_DATABASE", "dataforge"),
        pipeline=pipeline,
        quality_rules=quality_rules,
    )
    settings.ensure_directories()
    return settings
