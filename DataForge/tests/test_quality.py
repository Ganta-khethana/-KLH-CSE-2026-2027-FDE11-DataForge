import unittest
from datetime import datetime

import pandas as pd

from src.config import load_settings
from src.quality import profile_dataset
from src.transforms import clean_production, clean_quality, map_labels, SHIFT_MAP, RESULT_MAP


class QualityTransformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()

    def test_shift_standardization(self):
        series = pd.Series(["a", "Shift A", "1", "night"])
        mapped = map_labels(series, SHIFT_MAP)
        self.assertEqual(list(mapped), ["A", "A", "A", "C"])

    def test_result_standardization(self):
        series = pd.Series(["pass", "Y", "NOK", "0"])
        mapped = map_labels(series, RESULT_MAP)
        self.assertEqual(list(mapped), ["PASS", "PASS", "FAIL", "FAIL"])

    def test_production_cleaning_removes_duplicates_and_invalid_qty(self):
        df = pd.DataFrame(
            {
                "record_id": ["1", "2", "3"],
                "production_id": ["PO-1", "PO-1", "PO-2"],
                "plant_id": ["PLANT-HYD-01"] * 3,
                "line_id": ["L1", "L1", "L2"],
                "machine_id": ["M-101"] * 3,
                "product_code": [" gear-a ", "GEAR-A", "shaft-b"],
                "shift": ["Shift A", "A", "b"],
                "operator_id": ["OP-1", "OP-1", None],
                "quantity": [120, 120, -15],
                "cycle_time_sec": [20, 20, 18],
                "status": ["running", "RUNNING", "idle"],
                "event_ts": ["01/09/2026 10:00", "2026-09-01 10:00:00", "02/09/2026 11:00"],
            }
        )
        clean, quarantine = clean_production(df, self.settings)
        self.assertTrue((clean["product_code"] == clean["product_code"].str.upper()).all())
        self.assertNotIn(-15, list(clean["quantity"]))
        self.assertGreaterEqual(len(quarantine), 1)
        self.assertLessEqual(len(clean), 2)

    def test_quality_repairs_pass_fail_consistency(self):
        df = pd.DataFrame(
            {
                "record_id": ["1"],
                "inspection_id": ["INS-1"],
                "batch_id": ["B-1"],
                "product_code": ["GEAR-A"],
                "defect_count": [3],
                "defect_type": ["CRACK"],
                "result": ["PASS"],
                "inspector_id": ["QC-01"],
                "event_ts": ["2026-09-02 09:00:00"],
            }
        )
        clean, _ = clean_quality(df, self.settings)
        self.assertEqual(clean.iloc[0]["result"], "FAIL")

    def test_clean_score_is_high(self):
        df = pd.DataFrame(
            {
                "production_id": ["PO-1"],
                "plant_id": ["PLANT-HYD-01"],
                "line_id": ["L1"],
                "machine_id": ["M-101"],
                "product_code": ["GEAR-A"],
                "shift": ["A"],
                "operator_id": ["OP-1"],
                "quantity": [100],
                "cycle_time_sec": [20],
                "status": ["RUNNING"],
                "event_ts": [datetime(2026, 9, 2, 10, 0, 0)],
            }
        )
        score = profile_dataset(df, "production", "clean", self.settings)
        self.assertGreaterEqual(score.overall_score, 95)


if __name__ == "__main__":
    unittest.main()
