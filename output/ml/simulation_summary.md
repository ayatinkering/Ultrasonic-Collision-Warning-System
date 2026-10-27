# Prediction results — simulated rehearsal

**These are software-generated readings, not measurements collected from the LPC1768.** The file [`data/simulated_1000.csv`](../../data/simulated_1000.csv) labels every row `SIMULATED`. It has 1,000 rows: 20 separate five-second trials with 50 readings each. There are five trials for each scenario: approach, move away, stop before the warning zone, and pass by. The generator adds ordinary distance noise, occasional larger echo errors, and 18 missing readings. The servo pulse column is a simulated command trace; it is not a measured angle. The predictor uses only distance.

The model uses the current ultrasonic distance and the previous four distances to forecast the distance **0.5 seconds later**. We trained a small ridge-regression model and compared it with a constant-speed calculation. Whole trials were separated into 12 training, 4 validation and 4 test trials, so the test walks were unseen during fitting and model selection. Invalid readings were retained in the CSV but excluded from training windows. This left 730 usable windows overall and 158 test windows.

| Method on held-out simulated trials | Mean distance error | False warning windows | Missed warning-zone windows |
| --- | ---: | ---: | ---: |
| Constant-speed calculation | 5.049 cm | 0 | 0 |
| Five-reading ML model | 4.771 cm | 0 | 3 |

The ML model reduced average distance error by **0.278 cm** on these synthetic test windows. It also **missed three 30 cm warning-zone windows that the constant-speed calculation did not miss**. Thus this experiment does **not** show that ML is safer. A “window” is one prediction at a 100 ms sample, not one separate accident or person.

In the unseen `approach_03` replay, the object is measured at **36 cm** at **3.3 s**. The model predicts **23.9 cm** half a second ahead and marks `WARN`. The measured distance first reaches the 30 cm zone at **3.5 s**, giving a **0.2 s warning lead** in this one simulated example. The unseen `pass_by_04` stays at least **58 cm** away in its valid readings and produces no warning in its replay.

Use [`results.json`](results.json) for exact metrics, [`test_predictions.csv`](test_predictions.csv) for each held-out forecast, the two replay text files for the examples, and [`demo_comparison.svg`](demo_comparison.svg) for a presentation chart. To report actual lab performance, first collect 1,000 board readings through CN9 and rerun the same training code with `--data-kind real`. No real-data accuracy result has been obtained here.

The [Jupyter notebook](../../notebooks/distance_analysis.ipynb) adds preprocessing and four Matplotlib figures. It found **982 usable readings and 18 missing echoes**. The approach trials contain 63 readings inside the 30 cm zone; the pass-by and stop-before-zone trials contain none. On the held-out approach trial, the ML model's average error is **4.40 cm**, slightly **worse** than the constant-speed baseline's **4.15 cm**. The overall lower ML error comes from the other scenarios. This is another reason to show the per-scenario table, not only the single overall MAE.
