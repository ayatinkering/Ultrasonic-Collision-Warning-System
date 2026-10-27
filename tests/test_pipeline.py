"""Checks that the practice dataset and ML split preserve trial boundaries."""

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from make_simulated_data import make_rows  # noqa: E402
from train_model import read_samples, split_trials, fit_ridge, predict, validate_real_capture  # noqa: E402
from capture_1000 import parse_board_line, read_trial  # noqa: E402


class PipelineChecks(unittest.TestCase):
    def test_exactly_1000_and_no_zone_entry_on_safe_passes(self):
        rows = make_rows()
        self.assertEqual(len(rows), 1000)
        self.assertEqual(len({row["trial_id"] for row in rows}), 20)
        self.assertEqual({row["source"] for row in rows}, {"SIMULATED"})
        for row in rows:
            if row["scenario"] in ("pass_by", "stop_before_zone") and row["valid"]:
                self.assertGreater(float(row["distance_cm"]), 30.0)

    def test_whole_trial_split_and_future_label(self):
        samples = read_samples(ROOT / "data" / "simulated_1000.csv")
        train, val, test = split_trials(samples)
        ids = [{sample["trial_id"] for sample in part} for part in (train, val, test)]
        self.assertFalse(ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
        with (ROOT / "data" / "simulated_1000.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        by_trial_time = {(row["trial_id"], int(row["time_ms"])): row for row in rows}
        for sample in samples:
            future = by_trial_time[(sample["trial_id"], sample["time_ms"] + 500)]
            self.assertEqual(sample["y"], float(future["distance_cm"]))
            self.assertEqual(len(sample["x"]), 5)

    def test_learned_model_produces_finite_forecasts(self):
        train, _, test = split_trials(read_samples(ROOT / "data" / "simulated_1000.csv"))
        model = fit_ridge(train, 5, 1.0)
        self.assertEqual(len(model["weights"]), 5)
        for sample in test:
            self.assertLess(predict(model, sample), 1000.0)

    def test_uart_capture_parser_and_exact_trial(self):
        self.assertEqual(parse_board_line(b"DATA,7,1200,64,1,1500,0\r\n"),
                         (7, 1200, "64", 1, 1500, 0))
        self.assertEqual(parse_board_line(b"DATA,8,1300,,0,1510,2\r\n"),
                         (8, 1300, "", 0, 1510, 2))
        self.assertIsNone(parse_board_line(b"DATA,8,1300,64,1,1510,2\r\n"))

        class FakeBoard:
            def __init__(self):
                self.lines = iter(
                    f"DATA,{i},{1000 + 100 * i},64,1,1500,0\r\n".encode()
                    for i in range(50))

            def readline(self):
                return next(self.lines)

        rows = read_trial(FakeBoard(), "approach_01", "approach")
        self.assertEqual(len(rows), 50)
        self.assertEqual(rows[0]["time_ms"], 0)
        self.assertEqual(rows[-1]["time_ms"], 4900)

    def test_real_training_rejects_sweeping_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            csv_path = Path(folder) / "real_1000.csv"
            csv_path.write_text("trial_id,scenario,time_ms,distance_cm,valid\n", encoding="utf-8")
            sidecar = csv_path.with_suffix(".capture.json")
            sidecar.write_text(json.dumps({
                "source": "LPC1768-UART0-CN9", "sensor_mode": "sweeping",
                "readings": 1000, "trials": 20,
                "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fixed ultrasonic viewing direction"):
                validate_real_capture(csv_path)

    def test_fixed_capture_metadata_allows_training_split(self):
        # This is an in-memory-style TEST fixture, never a claimed lab capture.
        with tempfile.TemporaryDirectory() as folder:
            csv_path = Path(folder) / "real_1000.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(("trial_id", "scenario", "time_ms", "distance_cm", "valid"))
                for scenario in ("approach", "move_away", "stop_before_zone", "pass_by"):
                    for trial in range(1, 6):
                        for index in range(50):
                            distance = 120 - index if scenario == "approach" else 50 + index
                            writer.writerow((f"{scenario}_{trial:02d}", scenario,
                                             index * 100, distance, 1))
            csv_path.with_suffix(".capture.json").write_text(json.dumps({
                "source": "LPC1768-UART0-CN9", "sensor_mode": "fixed",
                "readings": 1000, "trials": 20,
                "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
            }), encoding="utf-8")
            self.assertEqual(validate_real_capture(csv_path)["readings"], 1000)
            train, validation, test = split_trials(read_samples(csv_path))
            self.assertTrue(train and validation and test)
            out_dir = Path(folder) / "trained"
            subprocess.run([
                sys.executable, str(ROOT / "scripts" / "train_model.py"),
                "--input", str(csv_path), "--data-kind", "real",
                "--out", str(out_dir),
            ], check=True, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(json.loads((out_dir / "results.json").read_text())["data_kind"], "real")

if __name__ == "__main__":
    unittest.main()
