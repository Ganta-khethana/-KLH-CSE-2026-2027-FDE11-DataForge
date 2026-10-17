"""Streamlit dashboard for Review 3 data-quality results."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
QUARANTINE = PROCESSED / "quarantine"
STATUS_FILE = RESULTS / "pipeline_status.json"

RAW_FILES = {
    "production": "production.csv",
    "sensors": "sensors.csv",
    "inventory": "inventory.csv",
    "maintenance": "maintenance.csv",
    "quality": "quality_inspection.csv",
}


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _status() -> dict:
    return _load_json(STATUS_FILE) or {"state": "idle"}


def _write_status(state: str, pid: int | None = None) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = {"state": state}
    if pid is not None:
        payload["pid"] = pid
    STATUS_FILE.write_text(json.dumps(payload), encoding="utf-8")


def _pipeline_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        import psutil  # type: ignore

        return psutil.pid_exists(pid)
    except Exception:
        pass
    try:
        import os

        os.kill(pid, 0)
        return True
    except Exception:
        return False


def start_background_pipeline() -> None:
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    log_path = RESULTS / "dashboard_pipeline.log"
    handle = log_path.open("a", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "src.pipelines.run", "--mode", "all"],
        cwd=str(ROOT),
        stdout=handle,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    _write_status("running", process.pid)


st.set_page_config(page_title="DataForge Review 3", layout="wide")
st.title("DataForge – Manufacturing ETL & Data Quality")
st.caption("Review 3 dashboard | Team 11 | 24DEA3101R")

status = _status()
running = status.get("state") == "running" and _pipeline_running(status.get("pid"))
if status.get("state") == "running" and not running:
    _write_status("idle")
    status = _status()
    running = False

if "autostarted" not in st.session_state:
    st.session_state.autostarted = True
    has_results = (RESULTS / "pipeline_summary.json").exists()
    if not running and not has_results:
        start_background_pipeline()
        running = True

with st.sidebar:
    st.header("Pipeline")
    if st.button("Run in background", type="primary", disabled=running):
        start_background_pipeline()
        st.rerun()
    if running:
        st.info("Pipeline is running in the background.")
    else:
        st.success("Pipeline ready. Results are shown on the right.")

if running:
    st.info("ETL is running in the background. This page will refresh automatically.")
    time.sleep(2)
    st.rerun()

summary = _load_json(RESULTS / "pipeline_summary.json")
if summary is None:
    st.warning("Waiting for the first pipeline results...")
    time.sleep(2)
    st.rerun()

gain = summary["after"]["overall_score"] - summary["before"]["overall_score"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Quality before", f"{summary['before']['overall_score']:.1f}%")
c2.metric("Quality after", f"{summary['after']['overall_score']:.1f}%", f"+{gain:.1f}")
c3.metric("Valid records stored", f"{summary['records_out']:,}")
c4.metric("Quarantined", f"{summary['records_quarantined']:,}")

before_df = pd.DataFrame(summary["before"]["by_source"])
after_df = pd.DataFrame(summary["after"]["by_source"])
compare = before_df[["source_name", "row_count", "overall_score"]].merge(
    after_df[["source_name", "row_count", "overall_score"]],
    on="source_name",
    suffixes=("_before", "_after"),
)
compare["gain"] = compare["overall_score_after"] - compare["overall_score_before"]
st.subheader("Quality improvement by source")
st.dataframe(compare, use_container_width=True)

col_a, col_b = st.columns(2)
with col_a:
    chart_path = RESULTS / "quality_before_after.png"
    if chart_path.exists():
        st.image(str(chart_path), caption="Overall score before vs after ETL")
with col_b:
    dim_path = RESULTS / "quality_dimensions.png"
    if dim_path.exists():
        st.image(str(dim_path), caption="Clean data quality dimensions")

st.subheader("Raw vs cleaned manufacturing data")
source = st.selectbox("Source system", list(RAW_FILES.keys()))
left, right = st.columns(2)
with left:
    st.markdown("**Raw (dirty) records**")
    raw_path = RAW / RAW_FILES[source]
    if raw_path.exists():
        st.dataframe(pd.read_csv(raw_path).head(20), use_container_width=True)
with right:
    st.markdown("**Clean / validated records**")
    clean_path = PROCESSED / f"{source}_clean.csv"
    if clean_path.exists():
        st.dataframe(pd.read_csv(clean_path).head(20), use_container_width=True)

q_path = QUARANTINE / f"{source}_quarantine.csv"
st.subheader("Quarantine (rejected records)")
if q_path.exists():
    qdf = pd.read_csv(q_path)
    st.bar_chart(qdf["dq_reason"].value_counts())
    st.dataframe(qdf.head(25), use_container_width=True)
else:
    st.info("No quarantined rows for this source.")
