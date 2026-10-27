"""Replay a trial on the laptop to preview the fixed-angle warning logic."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/simulated_1000.csv"))
    parser.add_argument("--model", type=Path, default=Path("output/ml/results.json"))
    parser.add_argument("--trial-id", default="approach_03")
    args = parser.parse_args()
    result = json.loads(args.model.read_text(encoding="utf-8"))
    if hashlib.sha256(args.input.read_bytes()).hexdigest() != result.get("input_sha256"):
        raise SystemExit("The CSV does not match the file used to train this model")
    model = result["models"][result["chosen_model"]]
    rows = [row for row in csv.DictReader(args.input.open(newline="", encoding="utf-8"))
            if row["trial_id"] == args.trial_id]
    if not rows:
        raise SystemExit(f"No trial {args.trial_id!r} in {args.input}")
    history = []
    previous_alarm = False
    print(f"REPLAY ONLY — {result['data_kind'].upper()} DATA; {args.trial_id}")
    print("time_ms  measured_cm  predicted_0.5s_cm  replay_warning")
    for row in rows:
        if row["valid"] != "1":
            history = []
            previous_alarm = False
            print(f"{row['time_ms']:>7}  {'ERROR':>11}  {'--':>17}  SENSOR ERROR")
            continue
        distance = float(row["distance_cm"])
        history.insert(0, distance)
        history = history[:5]
        if len(history) == 5:
            x = history
            predicted = max(0.0, model["intercept"] +
                            sum(weight * value for weight, value in zip(model["weights"], x)))
        else:
            predicted = distance
        warning = ("FAST" if distance < 15 else
                   "WARN" if distance <= 30 or (len(history) == 5 and predicted <= 30)
                   else "WARN" if previous_alarm and
                   (distance <= 35 or predicted <= 35) else "SAFE")
        previous_alarm = warning != "SAFE"
        print(f"{row['time_ms']:>7}  {distance:>11.1f}  "
              f"{predicted:>17.1f}  {warning}")


if __name__ == "__main__":
    main()
