"""Draw two ultrasonic prediction trials as an SVG for the lab presentation.

The heading states whether the model was trained on real or simulated data;
the script never silently presents practice data as board measurements.
"""

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/simulated_1000.csv"
RESULTS = ROOT / "output/ml/results.json"
OUTPUT = ROOT / "output/ml/demo_comparison.svg"


def points(rows, model):
    history = []
    measured, forecast = [], []
    for row in rows:
        if row["valid"] != "1":
            history = []
            continue
        distance = float(row["distance_cm"])
        history.insert(0, distance)
        history = history[:5]
        t = int(row["time_ms"])
        measured.append((t, distance))
        if len(history) == 5:
            estimate = max(0.0, model["intercept"] + sum(
                weight * value for weight, value in zip(model["weights"], history)))
            forecast.append((t, estimate))
    return measured, forecast


def path(coords, top, max_time, max_distance):
    return " ".join(("M" if index == 0 else "L") +
                    f"{70 + time_ms * 672 / max_time:.1f},{top + 140 - min(distance, max_distance) * 120 / max_distance:.1f}"
                    for index, (time_ms, distance) in enumerate(coords))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DATA)
    parser.add_argument("--model", type=Path, default=RESULTS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--approach", default="approach_03")
    parser.add_argument("--pass-by", default="pass_by_04")
    args = parser.parse_args()
    summary = json.loads(args.model.read_text(encoding="utf-8"))
    if hashlib.sha256(args.input.read_bytes()).hexdigest() != summary.get("input_sha256"):
        raise SystemExit("The CSV does not match the file used to train this model")
    model = summary["models"][summary["chosen_model"]]
    rows = list(csv.DictReader(args.input.open(newline="", encoding="utf-8")))
    data_label = ("REAL LPC1768 READINGS" if summary["data_kind"] == "real"
                  else "SIMULATED DATA ONLY — not measurements from the LPC1768")
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="540" viewBox="0 0 800 540">',
        '<rect width="800" height="540" fill="#f9fbff"/>',
        '<text x="40" y="37" font-family="Arial" font-size="22" font-weight="bold">Ultrasonic near-miss forecast</text>',
        f'<text x="40" y="61" font-family="Arial" font-size="15" fill="#a33">{html.escape(data_label)}</text>',
        '<text x="575" y="90" font-family="Arial" font-size="13" fill="#1e57a8">■ measured distance</text>',
        '<text x="575" y="110" font-family="Arial" font-size="13" fill="#d27800">■ predicted +0.5 s</text>',
    ]
    for top, trial, label in ((105, args.approach, "Approaching object"),
                              (320, args.pass_by, "Passing outside the zone")):
        selected = [row for row in rows if row["trial_id"] == trial]
        if not selected:
            raise SystemExit(f"No trial {trial!r} in {args.input}")
        measured, forecast = points(selected, model)
        max_time = max(int(row["time_ms"]) for row in selected)
        max_distance = max(120.0, *(distance for _, distance in measured))
        zone_y = top + 140 - 30 * 120 / max_distance
        elements.extend([
            f'<text x="70" y="{top + 8}" font-family="Arial" font-size="17" font-weight="bold">{html.escape(label)}</text>',
            f'<rect x="70" y="{top + 20}" width="672" height="120" fill="white" stroke="#ccd4df"/>',
            f'<line x1="70" y1="{zone_y}" x2="742" y2="{zone_y}" stroke="#c33" stroke-width="1.5" stroke-dasharray="6,5"/>',
            f'<text x="575" y="{zone_y - 5}" font-family="Arial" font-size="12" fill="#a33">30 cm warning zone</text>',
            f'<path d="{path(measured, top, max_time, max_distance)}" fill="none" stroke="#1e57a8" stroke-width="2.5"/>',
            f'<path d="{path(forecast, top, max_time, max_distance)}" fill="none" stroke="#d27800" stroke-width="2.5"/>',
            f'<text x="70" y="{top + 161}" font-family="Arial" font-size="12" fill="#555">0 s</text>',
            f'<text x="710" y="{top + 161}" font-family="Arial" font-size="12" fill="#555">{max_time / 1000:.1f} s</text>',
        ])
    elements.append('</svg>')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(elements) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
