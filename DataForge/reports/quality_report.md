# DataForge Review 3 – Pipeline Results

- Run ID: `20260926T052856-233bb2fe`
- Engine: `pandas`
- Storage: `sqlite`
- Started: 2026-09-26 05:28:56
- Finished: 2026-09-26 05:28:58

## Overall data-quality improvement

- Raw overall score: **91.34%**
- Clean overall score: **100.00%**
- Improvement: **8.66 points**
- Records in: **11914**
- Valid records stored: **10386**
- Quarantined records: **1528**

## Source-level scores

| Source | Raw rows | Clean rows | Score before | Score after | Gain |
|---|---:|---:|---:|---:|---:|
| production | 3120 | 2857 | 87.62 | 100.00 | 12.38 |
| sensors | 5175 | 4188 | 94.60 | 100.00 | 5.40 |
| inventory | 1545 | 1397 | 88.43 | 100.00 | 11.57 |
| maintenance | 832 | 772 | 91.46 | 100.00 | 8.54 |
| quality | 1242 | 1172 | 90.62 | 100.00 | 9.38 |

## Quality checks applied

- Missing values: imputed where statistically safe, otherwise rejected
- Duplicate business keys: first record kept, extras quarantined
- Invalid ranges: rejected into quarantine with a reason code
- Inconsistent formats: timestamps, units, shifts, pass/fail labels standardized
- Incorrect types: coerced to numeric/datetime; unparseable values rejected
- Out-of-range manufacturing measurements: temperature, vibration, pressure, downtime

## Output locations

- Clean CSV files: `data/processed/`
- Quarantine files: `data/processed/quarantine/`
- Analytics-ready extracts: `data/processed/analytics_ready_*.csv`
- Charts: `results/quality_before_after.png`, `results/quality_dimensions.png`

These clean extracts can be loaded into Power BI or any reporting tool.
