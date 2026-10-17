"""Write Review 3 quality reports, JSON metrics, and comparison charts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.config import Settings


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_processed_files(
    clean_frames: dict[str, pd.DataFrame],
    quarantine_frames: dict[str, pd.DataFrame],
    settings: Settings,
) -> None:
    for source, df in clean_frames.items():
        df.to_csv(settings.processed_dir / f"{source}_clean.csv", index=False)
    for source, df in quarantine_frames.items():
        if not df.empty:
            df.to_csv(settings.quarantine_dir / f"{source}_quarantine.csv", index=False)

    analytics_parts = []
    if "production" in clean_frames:
        prod = clean_frames["production"].copy()
        analytics_parts.append(prod)
    if analytics_parts:
        analytics = analytics_parts[0]
        analytics.to_csv(settings.processed_dir / "analytics_ready_production.csv", index=False)
    if "quality" in clean_frames:
        clean_frames["quality"].to_csv(settings.processed_dir / "analytics_ready_quality.csv", index=False)


def plot_quality_comparison(before: list[dict], after: list[dict], output_path: Path) -> None:
    sources = [item["source_name"] for item in before]
    before_scores = [item["overall_score"] for item in before]
    after_map = {item["source_name"]: item["overall_score"] for item in after}
    after_scores = [after_map.get(name, 0) for name in sources]
    x = range(len(sources))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - width / 2 for i in x], before_scores, width=width, label="Before ETL", color="#c44e52")
    ax.bar([i + width / 2 for i in x], after_scores, width=width, label="After ETL", color="#4c72b0")
    ax.set_xticks(list(x))
    ax.set_xticklabels(sources)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Data-quality score (%)")
    ax.set_title("DataForge – Data Quality Score Before vs After ETL")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(output_path, dpi=140)
    plt.close(fig)


def plot_dimension_heatmap(after: list[dict], output_path: Path) -> None:
    dims = ["completeness", "uniqueness", "validity", "consistency", "timeliness"]
    df = pd.DataFrame(after).set_index("source_name")[dims]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    image = ax.imshow(df.values, cmap="Blues", vmin=70, vmax=100)
    ax.set_xticks(range(len(dims)))
    ax.set_xticklabels(dims, rotation=20)
    ax.set_yticks(range(len(df.index)))
    ax.set_yticklabels(df.index)
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            ax.text(j, i, f"{df.values[i, j]:.1f}", ha="center", va="center", color="black", fontsize=8)
    fig.colorbar(image, ax=ax, label="Score (%)")
    ax.set_title("Clean-data quality dimensions by source")
    fig.tight_layout()
    fig.savefig(output_path, dpi=140)
    plt.close(fig)


def write_markdown_report(summary: dict, settings: Settings) -> Path:
    before = summary["before"]["by_source"]
    after = summary["after"]["by_source"]
    after_map = {item["source_name"]: item for item in after}
    lines = [
        "# DataForge Review 3 – Pipeline Results",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Engine: `{summary['engine']}`",
        f"- Storage: `{summary['storage_backend']}`",
        f"- Started: {summary['started_at']}",
        f"- Finished: {summary['finished_at']}",
        "",
        "## Overall data-quality improvement",
        "",
        f"- Raw overall score: **{summary['before']['overall_score']:.2f}%**",
        f"- Clean overall score: **{summary['after']['overall_score']:.2f}%**",
        f"- Improvement: **{summary['after']['overall_score'] - summary['before']['overall_score']:.2f} points**",
        f"- Records in: **{summary['records_in']}**",
        f"- Valid records stored: **{summary['records_out']}**",
        f"- Quarantined records: **{summary['records_quarantined']}**",
        "",
        "## Source-level scores",
        "",
        "| Source | Raw rows | Clean rows | Score before | Score after | Gain |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for raw in before:
        clean = after_map[raw["source_name"]]
        gain = clean["overall_score"] - raw["overall_score"]
        lines.append(
            f"| {raw['source_name']} | {raw['row_count']} | {clean['row_count']} | "
            f"{raw['overall_score']:.2f} | {clean['overall_score']:.2f} | {gain:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Quality checks applied",
            "",
            "- Missing values: imputed where statistically safe, otherwise rejected",
            "- Duplicate business keys: first record kept, extras quarantined",
            "- Invalid ranges: rejected into quarantine with a reason code",
            "- Inconsistent formats: timestamps, units, shifts, pass/fail labels standardized",
            "- Incorrect types: coerced to numeric/datetime; unparseable values rejected",
            "- Out-of-range manufacturing measurements: temperature, vibration, pressure, downtime",
            "",
            "## Output locations",
            "",
            "- Clean CSV files: `data/processed/`",
            "- Quarantine files: `data/processed/quarantine/`",
            "- Analytics-ready extracts: `data/processed/analytics_ready_*.csv`",
            "- Charts: `results/quality_before_after.png`, `results/quality_dimensions.png`",
            "",
            "These clean extracts can be loaded into Power BI or any reporting tool.",
            "",
        ]
    )
    report_path = settings.reports_dir / "quality_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    (settings.results_dir / "quality_report.md").write_text("\n".join(lines), encoding="utf-8")
    return report_path


def export_run_artifacts(summary: dict, settings: Settings, before: list[dict], after: list[dict]) -> None:
    stamp = datetime.now(timezone.utc).isoformat()
    save_json(settings.results_dir / "quality_before.json", {"generated_at": stamp, "scores": before})
    save_json(settings.results_dir / "quality_after.json", {"generated_at": stamp, "scores": after})
    save_json(settings.results_dir / "pipeline_summary.json", summary)
    plot_quality_comparison(before, after, settings.results_dir / "quality_before_after.png")
    plot_dimension_heatmap(after, settings.results_dir / "quality_dimensions.png")
    write_markdown_report(summary, settings)
