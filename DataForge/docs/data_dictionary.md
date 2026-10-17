# Data dictionary

Synthetic manufacturing data for plant `PLANT-HYD-01`.

## production

| Column | Meaning | Valid range / values |
|---|---|---|
| production_id | Production order identifier | unique with event_ts |
| plant_id | Plant code | PLANT-HYD-01 |
| line_id | Line | L1–L4 |
| machine_id | Machine | M-101–M-120 |
| product_code | Finished component | GEAR-A, SHAFT-B, BOLT-C, HOUSING-D, BEARING-E |
| shift | Shift | A, B, C |
| quantity | Units produced | 0–10000 |
| cycle_time_sec | Cycle time | 1–600 |
| status | Line status | RUNNING, STOPPED, IDLE |
| event_ts | Event time | 2026-08-01 to 2026-09-30 |

## sensors

Machine IoT readings: `temperature_c` 0–120, `vibration_mms` 0–50, `pressure_bar` 0–200, `humidity_pct` 0–100.

## inventory

SKU stock by warehouse. Units standardized to PCS, KG, L. Quantity cannot be negative.

## maintenance

Tickets with type PREVENTIVE, CORRECTIVE, PREDICTIVE. `downtime_hours` 0–24.

## quality_inspection

Inspection results PASS/FAIL. If `defect_count > 0`, result is repaired to FAIL.
