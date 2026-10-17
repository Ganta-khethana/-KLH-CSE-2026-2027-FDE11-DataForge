CREATE DATABASE IF NOT EXISTS dataforge;
USE dataforge;

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    started_at DATETIME NOT NULL,
    finished_at DATETIME NULL,
    engine VARCHAR(32) NOT NULL,
    storage_backend VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    records_in INT DEFAULT 0,
    records_out INT DEFAULT 0,
    records_quarantined INT DEFAULT 0,
    overall_score_before DOUBLE NULL,
    overall_score_after DOUBLE NULL
);

CREATE TABLE IF NOT EXISTS dq_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    source_name VARCHAR(64) NOT NULL,
    stage VARCHAR(16) NOT NULL,
    completeness DOUBLE NOT NULL,
    uniqueness DOUBLE NOT NULL,
    validity DOUBLE NOT NULL,
    consistency DOUBLE NOT NULL,
    timeliness DOUBLE NOT NULL,
    overall_score DOUBLE NOT NULL,
    row_count INT NOT NULL,
    created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_production (
    production_id VARCHAR(64) NOT NULL,
    plant_id VARCHAR(32) NOT NULL,
    line_id VARCHAR(32) NOT NULL,
    machine_id VARCHAR(32) NOT NULL,
    product_code VARCHAR(64) NOT NULL,
    shift VARCHAR(8) NOT NULL,
    operator_id VARCHAR(32) NULL,
    quantity DOUBLE NOT NULL,
    cycle_time_sec DOUBLE NOT NULL,
    status VARCHAR(16) NOT NULL,
    event_ts DATETIME NOT NULL,
    run_id VARCHAR(64) NOT NULL,
    PRIMARY KEY (production_id, event_ts)
);

CREATE TABLE IF NOT EXISTS fact_sensors (
    sensor_id VARCHAR(64) NOT NULL,
    machine_id VARCHAR(32) NOT NULL,
    temperature_c DOUBLE NOT NULL,
    vibration_mms DOUBLE NOT NULL,
    pressure_bar DOUBLE NOT NULL,
    humidity_pct DOUBLE NOT NULL,
    event_ts DATETIME NOT NULL,
    run_id VARCHAR(64) NOT NULL,
    PRIMARY KEY (sensor_id, event_ts)
);

CREATE TABLE IF NOT EXISTS fact_inventory (
    sku VARCHAR(64) NOT NULL,
    warehouse_id VARCHAR(32) NOT NULL,
    quantity DOUBLE NOT NULL,
    unit VARCHAR(16) NOT NULL,
    reorder_level DOUBLE NOT NULL,
    event_ts DATETIME NOT NULL,
    run_id VARCHAR(64) NOT NULL,
    PRIMARY KEY (sku, warehouse_id, event_ts)
);

CREATE TABLE IF NOT EXISTS fact_maintenance (
    ticket_id VARCHAR(64) PRIMARY KEY,
    machine_id VARCHAR(32) NOT NULL,
    maintenance_type VARCHAR(32) NOT NULL,
    downtime_hours DOUBLE NOT NULL,
    technician_id VARCHAR(32) NULL,
    event_ts DATETIME NOT NULL,
    run_id VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_quality (
    inspection_id VARCHAR(64) PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL,
    product_code VARCHAR(64) NOT NULL,
    defect_count INT NOT NULL,
    defect_type VARCHAR(64) NULL,
    result VARCHAR(8) NOT NULL,
    inspector_id VARCHAR(32) NULL,
    event_ts DATETIME NOT NULL,
    run_id VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS quarantine_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    source_name VARCHAR(64) NOT NULL,
    dq_reason VARCHAR(128) NOT NULL,
    payload_json JSON NOT NULL,
    created_at DATETIME NOT NULL
);
