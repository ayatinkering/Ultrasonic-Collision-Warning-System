"""Train a tiny 0.5-second range predictor; no ML packages required.

Training uses complete walking trials as independent groups. The target is
the distance reading five 100-ms samples later. Never use future readings
as input features. The model is ridge-regularized linear regression.
"""

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path


HISTORY = 5
HORIZON = 5
ZONE_CM = 30.0
SEED = 1768


def validate_real_capture(path: Path) -> dict:
    """Require the sidecar written by the real UART capture, not a renamed CSV.

    A 0.5-second distance forecast assumes consecutive samples view the same
    area. When the ultrasonic sensor is physically swept by the servo, that
    assumption fails even if the CSV has exactly 1,000 genuine board rows.
    """
    sidecar = path.with_suffix(".capture.json")
    if not sidecar.exists():
        raise ValueError(f"Real-data run needs capture details: {sidecar}")
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    if metadata.get("source") != "LPC1768-UART0-CN9":
        raise ValueError("Capture details do not identify the LPC1768 CN9 serial source")
    if metadata.get("sensor_mode") != "fixed":
        raise ValueError("This 0.5-second model requires a fixed ultrasonic viewing direction")
    if metadata.get("readings") != 1000 or metadata.get("trials") != 20:
        raise ValueError("Expected 1,000 readings in 20 separate captured trials")
    if hashlib.sha256(path.read_bytes()).hexdigest() != metadata.get("csv_sha256"):
        raise ValueError("CSV differs from the file recorded by the capture script")
    return metadata


def read_samples(path: Path) -> list[dict]:
    """Build training examples from five PAST distances and one FUTURE label.

    All samples from a trial are kept together for splitting. Invalid echo
    readings remain in the CSV for audit but cannot form usable examples.
    """
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {"trial_id", "scenario", "time_ms", "distance_cm", "valid"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"CSV must have columns: {', '.join(sorted(required))}")
    by_trial = defaultdict(list)
    for row in rows:
        by_trial[row["trial_id"]].append(row)
    samples = []
    for trial_id, trial in by_trial.items():
        trial.sort(key=lambda row: int(row["time_ms"]))
        for index in range(HISTORY - 1, len(trial) - HORIZON):
            past = trial[index - HISTORY + 1:index + 1]
            future = trial[index + HORIZON]
            if any(row["valid"] != "1" or row["distance_cm"] == "" for row in past):
                continue
            if future["valid"] != "1" or future["distance_cm"] == "":
                continue
            current_time = int(trial[index]["time_ms"])
            if abs(int(future["time_ms"]) - current_time - 500) > 50:
                continue
            if abs(int(past[0]["time_ms"]) - current_time + 400) > 50:
                continue
            distances = [float(row["distance_cm"]) for row in reversed(past)]
            samples.append({
                "trial_id": trial_id,
                "scenario": trial[index]["scenario"],
                "time_ms": current_time,
                "x": distances,
                "y": float(future["distance_cm"]),
            })
    if len(samples) < 30:
        raise ValueError("Too few complete 5-reading histories with a 0.5-second future label")
    return samples


def split_trials(samples: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Keep every walk wholly in train, validation, or test to avoid leakage."""
    groups = defaultdict(list)
    for sample in samples:
        groups[sample["scenario"]].append(sample["trial_id"])
    rng = random.Random(SEED)
    train_ids, val_ids, test_ids = set(), set(), set()
    for scenario, ids in groups.items():
        ids = sorted(set(ids))
        if len(ids) < 5:
            raise ValueError(f"Need at least 5 separate trials for scenario {scenario!r}")
        rng.shuffle(ids)
        n_test = max(1, round(len(ids) * 0.2))
        n_val = max(1, round(len(ids) * 0.2))
        test_ids.update(ids[:n_test])
        val_ids.update(ids[n_test:n_test + n_val])
        train_ids.update(ids[n_test + n_val:])
    assert not (train_ids & val_ids or train_ids & test_ids or val_ids & test_ids)
    return ([s for s in samples if s["trial_id"] in train_ids],
            [s for s in samples if s["trial_id"] in val_ids],
            [s for s in samples if s["trial_id"] in test_ids])


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Small Gaussian elimination with pivoting for five distance features."""
    n = len(vector)
    augmented = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda i: abs(augmented[i][column]))
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        if abs(augmented[column][column]) < 1e-12:
            raise ValueError("Training matrix is singular")
        scale = augmented[column][column]
        for j in range(column, n + 1):
            augmented[column][j] /= scale
        for i in range(n):
            if i == column:
                continue
            factor = augmented[i][column]
            for j in range(column, n + 1):
                augmented[i][j] -= factor * augmented[column][j]
    return [row[n] for row in augmented]


def fit_ridge(samples: list[dict], feature_count: int, alpha: float) -> dict:
    """Fit a tiny regularized linear model using only Python's standard library."""
    xs = [sample["x"][:feature_count] for sample in samples]
    ys = [sample["y"] for sample in samples]
    n = len(xs)
    means = [sum(row[j] for row in xs) / n for j in range(feature_count)]
    scales = [max(1e-9, math.sqrt(sum((row[j] - means[j]) ** 2 for row in xs) / n))
              for j in range(feature_count)]
    ymean = sum(ys) / n
    a = [[0.0] * feature_count for _ in range(feature_count)]
    b = [0.0] * feature_count
    for row, target in zip(xs, ys):
        z = [(row[j] - means[j]) / scales[j] for j in range(feature_count)]
        for j in range(feature_count):
            b[j] += z[j] * (target - ymean)
            for k in range(feature_count):
                a[j][k] += z[j] * z[k]
    for j in range(feature_count):
        a[j][j] += alpha
    scaled_weights = solve(a, b)
    weights = [scaled_weights[j] / scales[j] for j in range(feature_count)]
    intercept = ymean - sum(w * m for w, m in zip(weights, means))
    return {"intercept": intercept, "weights": weights, "alpha": alpha,
            "feature_count": feature_count}


def predict(model: dict, sample: dict) -> float:
    return max(0.0, model["intercept"] + sum(w * x for w, x in
               zip(model["weights"], sample["x"])))


def baseline(sample: dict) -> float:
    # Five samples span 0.4 s; extrapolate their average closing speed 0.5 s.
    distances = sample["x"]
    return max(0.0, distances[0] + (distances[0] - distances[4]) * 1.25)


def metrics(samples: list[dict], estimator) -> dict:
    """Report distance error and 30 cm warning decisions on held-out trials."""
    errors, tp, fp, fn, tn = [], 0, 0, 0, 0
    for sample in samples:
        estimated = estimator(sample)
        errors.append(abs(estimated - sample["y"]))
        predicted_zone = estimated <= ZONE_CM
        actual_zone = sample["y"] <= ZONE_CM
        if predicted_zone and actual_zone:
            tp += 1
        elif predicted_zone:
            fp += 1
        elif actual_zone:
            fn += 1
        else:
            tn += 1
    return {"mae_cm": round(sum(errors) / len(errors), 3),
            "true_warning_windows": tp, "false_warning_windows": fp,
            "missed_zone_windows": fn, "correct_nonwarning_windows": tn}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/simulated_1000.csv"))
    parser.add_argument("--data-kind", choices=("simulated", "real"), default="simulated")
    parser.add_argument("--out", type=Path, default=Path("output/ml"))
    args = parser.parse_args()
    if args.data_kind == "real":
        try:
            validate_real_capture(args.input)
        except ValueError as error:
            raise SystemExit(str(error)) from error
    samples = read_samples(args.input)
    train, val, test = split_trials(samples)
    choices = [fit_ridge(train, HISTORY, alpha) for alpha in (0.1, 1.0, 10.0)]
    selected = min(choices, key=lambda model: metrics(val, lambda s: predict(model, s))["mae_cm"])
    val_mae = {"ultrasonic_only": metrics(val, lambda s: predict(selected, s))["mae_cm"]}
    chosen = "ultrasonic_only"
    # Refit with training + validation trials. The test trials stay untouched.
    final_models = {chosen: fit_ridge(train + val, HISTORY, selected["alpha"])}
    results = {"constant_velocity": metrics(test, baseline)}
    for label, model in final_models.items():
        results[label] = metrics(test, lambda s, m=model: predict(m, s))
    args.out.mkdir(parents=True, exist_ok=True)
    summary = {"data_kind": args.data_kind, "input": str(args.input),
               "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
               "total_readings": sum(1 for _ in csv.DictReader(args.input.open(newline="", encoding="utf-8"))),
               "usable_windows": len(samples),
               "trial_counts": {"train": len({s["trial_id"] for s in train}),
                                "validation": len({s["trial_id"] for s in val}),
                                "test": len({s["trial_id"] for s in test})},
               "chosen_model": chosen, "validation_mae_cm": val_mae,
               "test_metrics": results, "models": final_models}
    (args.out / "results.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (args.out / "test_predictions.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("trial_id", "scenario", "time_ms", "actual_0p5s_cm",
                         "constant_velocity_cm", "ultrasonic_ml_cm"))
        for sample in test:
            writer.writerow((sample["trial_id"], sample["scenario"], sample["time_ms"],
                             f"{sample['y']:.1f}", f"{baseline(sample):.1f}",
                             f"{predict(final_models['ultrasonic_only'], sample):.1f}"))
    print(f"DATA TYPE: {args.data_kind.upper()} — never present simulated scores as lab results")
    print(f"Readings: {summary['total_readings']}; usable histories: {len(samples)}")
    print(f"Whole-trial split: {summary['trial_counts']}")
    for label, result in results.items():
        print(f"{label}: MAE {result['mae_cm']:.3f} cm; "
              f"false warning windows {result['false_warning_windows']}; "
              f"missed zone windows {result['missed_zone_windows']}")
    print(f"Selected on validation data: {chosen}; saved results: {args.out / 'results.json'}")


if __name__ == "__main__":
    main()
