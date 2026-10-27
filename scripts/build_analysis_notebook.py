"""Build the reproducible Jupyter analysis notebook from editable source cells."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "notebooks" / "distance_analysis.ipynb"


def markdown(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": source.splitlines(keepends=True)}


cells = [
    markdown("""# Ultrasonic distance: data quality and prediction analysis

**Data source: software-generated synthetic readings.** This notebook does not contain measurements from the LPC1768. Every data row has `source = SIMULATED`. The same analysis can be rerun on a genuine CN9 capture later, but any such result must use the real CSV and real model output.

The aim is to inspect the 1,000-row practice dataset, identify missing echoes, compare scenarios, and evaluate a model that forecasts distance 0.5 seconds ahead. The model itself was trained by `scripts/train_model.py` using whole-trial train/validation/test splits. This notebook reads the held-out predictions; it does not refit on test data.

Run from the repository or `notebooks/` folder after installing `pandas`, `numpy`, `matplotlib`, and Jupyter.
"""),
    code("""from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path.cwd()
if not (ROOT / 'data' / 'simulated_1000.csv').exists():
    ROOT = ROOT.parent
DATA = ROOT / 'data' / 'simulated_1000.csv'
PREDICTIONS = ROOT / 'output' / 'ml' / 'test_predictions.csv'
RESULTS = ROOT / 'output' / 'ml' / 'results.json'
FIGURES = ROOT / 'output' / 'ml' / 'notebook_figures'
FIGURES.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA)
results = json.loads(RESULTS.read_text(encoding='utf-8'))
assert len(df) == 1000 and df['source'].eq('SIMULATED').all()
assert results['data_kind'] == 'simulated'
assert df.groupby('trial_id').size().eq(50).all()
print(f\"Source: {df['source'].iloc[0]} | rows: {len(df)} | trials: {df['trial_id'].nunique()}\")
display(df.head(8))
"""),
    markdown("""## 1. Clean and check the readings

Convert numeric fields, keep echo failures as missing values, and check for duplicate trial/time combinations. We **do not fill in missing distances** for training: inventing them would make the model look more certain than it is. A valid ultrasonic reading must have status code 0 and a distance from 2 to 400 cm.
"""),
    code("""numeric = ['time_ms', 'distance_cm', 'valid', 'status_code', 'servo_pulse_us']
for column in numeric:
    df[column] = pd.to_numeric(df[column], errors='coerce')
df['usable'] = (df['valid'].eq(1) & df['status_code'].eq(0)
                & df['distance_cm'].between(2, 400))
df.loc[~df['usable'], 'distance_cm'] = np.nan
assert not df.duplicated(['trial_id', 'time_ms']).any()
assert df['time_ms'].between(0, 4900).all()

quality = df.groupby('scenario').agg(
    rows=('usable', 'size'), usable=('usable', 'sum'),
    missing_echoes=('usable', lambda x: (~x).sum()),
    minimum_cm=('distance_cm', 'min'),
    median_cm=('distance_cm', 'median'),
    maximum_cm=('distance_cm', 'max'))
quality['inside_30cm_zone'] = df.groupby('scenario')['distance_cm'].apply(
    lambda x: (x <= 30).sum())
print(f\"Usable readings: {int(df['usable'].sum())}/1000; missing echoes: {int((~df['usable']).sum())}\")
display(quality.round(1))
"""),
    code("""# Plot valid versus missing echoes by scenario; missing data is visible.
counts = pd.DataFrame({'valid': quality['usable'], 'missing': quality['missing_echoes']})
fig, ax = plt.subplots(figsize=(9, 4))
counts.plot.bar(stacked=True, ax=ax, color=['#2563a6', '#dc6b4a'])
ax.set(title='Data quality by scenario (synthetic)', ylabel='Readings', xlabel='')
ax.legend(title='Echo result')
ax.tick_params(axis='x', rotation=15)
fig.tight_layout()
fig.savefig(FIGURES / '01_data_quality.png', dpi=160)
plt.show()
"""),
    markdown("""## 2. Understand the four movement scenarios

The distribution plot shows why a single range threshold does not describe motion. Approach trials tend to enter the 30 cm zone; pass-by and stop-before-zone trials remain outside it. The servo pulse column records a command trace only; it is not a measured angle and is **not** a model input.
"""),
    code("""order = ['approach', 'move_away', 'stop_before_zone', 'pass_by']
groups = [df.loc[df['scenario'].eq(name), 'distance_cm'].dropna() for name in order]
fig, ax = plt.subplots(figsize=(9, 4))
ax.boxplot(groups, tick_labels=order, showfliers=True)
ax.axhline(30, color='#b72222', linestyle='--', label='30 cm warning zone')
ax.set(title='Distance distribution by scenario (synthetic)', ylabel='Distance (cm)')
ax.tick_params(axis='x', rotation=15)
ax.legend()
fig.tight_layout()
fig.savefig(FIGURES / '02_distance_distribution.png', dpi=160)
plt.show()
"""),
    code("""# These two walks are held-out TEST trials, not training examples.
fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
for ax, trial_id, title in zip(axes,
                               ['approach_03', 'pass_by_04'],
                               ['Approaching target', 'Safe pass-by']):
    trial = df.loc[df['trial_id'].eq(trial_id)].sort_values('time_ms')
    ax.plot(trial['time_ms'] / 1000, trial['distance_cm'], marker='.',
            linewidth=1.8, color='#2563a6', label='Measured-style distance')
    ax.axhline(30, color='#b72222', linestyle='--', label='30 cm zone')
    ax.set(title=f'{title}: {trial_id}', xlabel='Time (s)', ylabel='Distance (cm)')
    ax.grid(alpha=0.25)
axes[0].legend()
fig.suptitle('Held-out synthetic trajectories')
fig.tight_layout()
fig.savefig(FIGURES / '03_held_out_trajectories.png', dpi=160)
plt.show()
"""),
    markdown("""## 3. Evaluate the half-second forecast

The table below contains only **held-out test windows**. `actual_0p5s_cm` is the future distance, while the other two columns are predictions made from earlier readings. Mean absolute error measures average distance difference; warning misses and false alarms matter separately for a safety use case.
"""),
    code("""pred = pd.read_csv(PREDICTIONS)
pred['baseline_abs_error'] = (pred['constant_velocity_cm'] - pred['actual_0p5s_cm']).abs()
pred['ml_abs_error'] = (pred['ultrasonic_ml_cm'] - pred['actual_0p5s_cm']).abs()
pred['actual_zone'] = pred['actual_0p5s_cm'].le(30)
pred['ml_zone'] = pred['ultrasonic_ml_cm'].le(30)
pred['ml_false_warning'] = pred['ml_zone'] & ~pred['actual_zone']
pred['ml_missed_zone'] = ~pred['ml_zone'] & pred['actual_zone']
per_scenario = pred.groupby('scenario').agg(
    windows=('trial_id', 'size'),
    baseline_mae_cm=('baseline_abs_error', 'mean'),
    ml_mae_cm=('ml_abs_error', 'mean'),
    ml_false_warnings=('ml_false_warning', 'sum'),
    ml_missed_zone=('ml_missed_zone', 'sum'))
display(per_scenario.round(2))
display(pd.DataFrame(results['test_metrics']).T)
"""),
    code("""fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].hist(pred['baseline_abs_error'], bins=14, alpha=0.65,
             label='Constant-speed', color='#64748b')
axes[0].hist(pred['ml_abs_error'], bins=14, alpha=0.65,
             label='Five-reading ML', color='#e09320')
axes[0].set(title='Absolute forecast error on held-out trials',
            xlabel='Absolute error (cm)', ylabel='Prediction windows')
axes[0].legend()
axes[1].scatter(pred['actual_0p5s_cm'], pred['ultrasonic_ml_cm'],
                s=16, alpha=0.55, color='#2563a6')
limit = max(pred['actual_0p5s_cm'].max(), pred['ultrasonic_ml_cm'].max())
axes[1].plot([0, limit], [0, limit], '--', color='#444', label='Perfect prediction')
axes[1].axvline(30, color='#b72222', alpha=0.5)
axes[1].axhline(30, color='#b72222', alpha=0.5)
axes[1].set(title='ML prediction versus future distance',
            xlabel='Actual future distance (cm)', ylabel='Predicted distance (cm)')
axes[1].legend()
fig.suptitle('Prediction quality on unseen synthetic walks')
fig.tight_layout()
fig.savefig(FIGURES / '04_prediction_errors.png', dpi=160)
plt.show()
"""),
    markdown("""## What the analysis means

The saved [`results.json`](../output/ml/results.json) reports a slightly smaller average distance error for the five-reading model than for the constant-speed calculation on these generated test windows. However, the model misses more future 30 cm warning-zone windows. This does **not** demonstrate a safer warning system. The `approach_03` and `pass_by_04` plots are useful for explaining the method, but the model has not been validated with actual board measurements.

To repeat this analysis with real data, collect an authentic CSV through CN9, train with `--data-kind real`, and update the notebook's `DATA`, `PREDICTIONS`, and `RESULTS` paths. Do not change a generated file's label to “real.”
"""),
]


def main():
    for index, cell in enumerate(cells):
        cell["id"] = f"cell-{index:02d}"
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {TARGET}")


if __name__ == "__main__":
    main()
