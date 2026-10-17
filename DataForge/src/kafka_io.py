"""Kafka publisher/consumer with a file-based fallback bus.

When KAFKA_ENABLED=true the pipeline talks to a real Apache Kafka broker.
The file bus is used only when Kafka is explicitly disabled.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config import Settings


class FileBus:
    """Local JSONL topics used when Kafka is disabled."""

    def __init__(self, staging_dir: Path):
        self.base = staging_dir / "topics"
        self.base.mkdir(parents=True, exist_ok=True)

    def _topic_path(self, topic: str) -> Path:
        safe = topic.replace(".", "_")
        return self.base / f"{safe}.jsonl"

    def publish(self, topic: str, records: list[dict]) -> int:
        path = self._topic_path(topic)
        with path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, default=str) + "\n")
        return len(records)

    def consume(self, topic: str) -> list[dict]:
        path = self._topic_path(topic)
        if not path.exists():
            return []
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def reset(self) -> None:
        if self.base.exists():
            for path in self.base.glob("*.jsonl"):
                path.unlink()


class KafkaBus:
    def __init__(self, bootstrap_servers: str):
        from kafka import KafkaConsumer, KafkaProducer
        from kafka.admin import KafkaAdminClient, NewTopic
        from kafka.errors import TopicAlreadyExistsError

        self.bootstrap_servers = bootstrap_servers
        admin = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id="dataforge-admin",
            request_timeout_ms=20000,
        )
        admin.close()
        self._producer_cls = KafkaProducer
        self._consumer_cls = KafkaConsumer
        self._admin_cls = KafkaAdminClient
        self._topic_error = TopicAlreadyExistsError
        self._new_topic_cls = NewTopic

    def ensure_topics(self, topics: list[str]) -> None:
        admin = self._admin_cls(
            bootstrap_servers=self.bootstrap_servers,
            client_id="dataforge-admin",
            request_timeout_ms=20000,
        )
        existing = set(admin.list_topics())
        new_topics = [
            self._new_topic_cls(name=name, num_partitions=1, replication_factor=1)
            for name in topics
            if name not in existing
        ]
        if new_topics:
            try:
                admin.create_topics(new_topics)
            except self._topic_error:
                pass
        admin.close()

    def publish(self, topic: str, records: list[dict]) -> int:
        producer = self._producer_cls(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            acks="all",
            retries=3,
            linger_ms=5,
        )
        for record in records:
            producer.send(topic, record)
        producer.flush()
        producer.close()
        return len(records)

    def consume(self, topic: str, timeout_ms: int = 20000) -> list[dict]:
        consumer = self._consumer_cls(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=f"dataforge-{uuid.uuid4().hex}",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            consumer_timeout_ms=timeout_ms,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        rows = [message.value for message in consumer]
        consumer.close()
        return rows

    def reset(self) -> None:
        return None


def get_bus(settings: Settings):
    if not settings.kafka_enabled:
        return FileBus(settings.staging_dir)
    return KafkaBus(settings.kafka_servers)


def dataframe_to_records(df: pd.DataFrame, source_name: str, run_id: str) -> list[dict]:
    payload = df.where(pd.notna(df), None).to_dict(orient="records")
    ingested_at = datetime.now(timezone.utc).isoformat()
    for row in payload:
        row["_source"] = source_name
        row["_run_id"] = run_id
        row["_ingested_at"] = ingested_at
    return payload


def records_to_dataframe(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    return df.drop(columns=["_source", "_run_id", "_ingested_at"], errors="ignore")
