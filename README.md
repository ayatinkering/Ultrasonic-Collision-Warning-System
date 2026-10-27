# LPC1768 ultrasonic warning + real-data ML experiment

**Current ML results are from a simulated rehearsal. No 1,000-row real board capture has been collected in this workspace.** See the [simulation results summary](output/ml/simulation_summary.md).

This project uses the team's existing LPC1768 ultrasonic warning circuit and firmware. The only change to [`main.c`](main.c) is **serial logging of each ultrasonic measurement** through the board's existing CN9 connector. The servo still sweeps exactly as before; the LCD, buzzer, LEDs, seven-segment display and PIR display still behave as before. PIR is **not** used by the ML model.

The small ML experiment asks: **From the last five ultrasonic distances, can we predict the distance 0.5 seconds later better than a simple constant-speed calculation?** The model trains on the laptop from **1,000 real board readings** that you collect. The board continues its existing alarm; the ML result is a separate laptop demonstration.

## What you need

- Your current LPC1768 board, ultrasonic sensor and project wiring.
- The **same CN9 RS232-to-PC/USB-serial cable** already used with Flash Magic. CN9 is hardwired to UART0, so no extra jumper from the breadboard is needed. Do not connect a TTL USB-serial wire to CN9.
- Keil, Flash Magic and Python 3 on the laptop.
- The Python serial package: `python -m pip install pyserial`.

## Part 1 — Flash the logging firmware

1. In your existing Keil project, use this repository's [`main.c`](main.c) as the application source. Add only one copy of it to the Keil source group, with the normal startup and system files. Enable **Create HEX File**, then build.
2. Flash the new HEX using Flash Magic exactly as in your previous successful lab run. Keep your sensor and output wires in place. Flash Magic uses the CN9 serial cable and the same COM number you used previously.
3. **Close Flash Magic completely** after programming. Put SW21 in its **run/OFF** position; make sure JP3 is not forcing ISP mode. Reset the board so the new program runs.
4. At 9600 baud, 8 data bits, no parity, 1 stop bit and no flow control, the PC should receive a line roughly every 100 ms. A good line looks like `DATA,42,4200,63,1,1500,0`. An echo failure looks like `DATA,43,4300,,0,1510,2`. The empty distance field is intentional. If you use a serial terminal to check this, **close the terminal before running the capture script**, because only one program can own the COM port.

The fields are sequence number, board time in milliseconds, distance in cm, whether the echo was valid, commanded servo pulse width in microseconds, and sensor status. Status 0 is good; 1–4 identify echo errors. The pulse is **not** a measured physical angle. The firmware comments explain every added UART function.

## Part 2 — Collect exactly 1,000 real readings

For this **0.5-second prediction experiment**, keep the ultrasonic sensor pointed at the **same area** throughout each five-second walk. If it is mounted on the sweeping servo, temporarily place the ultrasonic sensor on a stationary support facing forward; the servo code and its wiring do not change. The servo can sweep unloaded. Readings taken while the sensor itself turns see different directions and cannot validly represent one object's approach speed.

From the repository folder, run:

```text
python scripts/capture_1000.py --port COM4 --sensor-mode fixed
```

Replace `COM4` with your actual port. The script prompts for **20 separate trials**, each with **50 consecutive readings**: five approaches, five walks away, five approaches that stop before the 30 cm zone, and five pass-bys outside that zone. Move during the five seconds after pressing Enter. Start each approach roughly 1 m from the sensor and walk slowly enough to see several readings; for a pass-by, walk across the view while remaining farther than 30 cm. You may use a moving cardboard target instead of a person if it gives steadier echoes.

The script rejects a trial if a serial sample is lost, then asks you to repeat it. It writes the CSV **only after all 1,000 real rows are captured**. The output is [`data/real_1000.csv`](data/real_1000.csv) plus `data/real_1000.capture.json`, which records the source, capture time and file checksum. Invalid echoes stay in the CSV as blank distances; the trainer skips unusable histories rather than inventing values. If you keep the sensor rotating, you may record with `--sensor-mode sweeping`, but the 0.5-second trainer will reject that file for the fixed-view model.

## Part 3 — Train and show the real-data result

After the capture succeeds, run:

```text
python scripts/train_model.py --input data/real_1000.csv --data-kind real --out output/ml/real
python scripts/replay_demo.py --input data/real_1000.csv --model output/ml/real/results.json --trial-id approach_03
python scripts/replay_demo.py --input data/real_1000.csv --model output/ml/real/results.json --trial-id pass_by_04
python scripts/plot_demo.py --input data/real_1000.csv --model output/ml/real/results.json --output output/ml/real/demo_comparison.svg
```

Open `output/ml/real/results.json` for the final comparison and `output/ml/real/demo_comparison.svg` for the presentation chart. Training uses five recent distances as inputs and the actual distance 0.5 seconds later as the label. The code separates **entire walks** into training, validation and test sets; it never uses future distance as an input. It compares the small ridge-regression model with a constant-speed forecast, reporting mean distance error and warning errors at 30 cm. A model that makes more missed warnings should **not** be claimed as safer, even if its average distance error is smaller.

You can explain the work to your teacher as: “We kept our physical LPC1768 warning circuit, logged 1,000 actual ultrasonic measurements, trained a lightweight half-second distance predictor, and compared it against a simple rule on unseen walks.” Show the live board output first, then the real CSV, result table and replay/plot. Do not say ML runs on the LPC1768; it currently runs on the laptop.

## Before the lab: software rehearsal

The repository also includes [`data/simulated_1000.csv`](data/simulated_1000.csv) so you can rehearse the commands without the board. The existing [`output/ml/results.json`](output/ml/results.json) and [practice chart](output/ml/demo_comparison.svg) are **simulated**, not lab measurements. They are kept separate from `output/ml/real/`. Generate them again with:

```text
python scripts/make_simulated_data.py
python scripts/train_model.py --input data/simulated_1000.csv --data-kind simulated
python scripts/replay_demo.py --trial-id approach_03
python scripts/plot_demo.py
```

The current simulated file has **20 trials × 50 readings**, matching the planned capture size. Every row is marked `SIMULATED`; 18 of the 1,000 rows represent missed echoes. On held-out simulated trials, the five-reading model has **4.771 cm** mean distance error versus **5.049 cm** for constant speed, but it has **3 missed warning windows versus 0**. Read the [plain-language result summary](output/ml/simulation_summary.md) before presenting these practice numbers.

## Jupyter notebook: preprocessing and visual analysis

Open [`notebooks/distance_analysis.ipynb`](notebooks/distance_analysis.ipynb) to inspect the full analysis. It checks the source and trial sizes, converts data types, leaves failed echoes missing, summarizes distances by scenario, and compares forecast errors on unseen trials. It uses Pandas and Matplotlib and saves four figures in [`output/ml/notebook_figures/`](output/ml/notebook_figures/).

If the packages are not installed on your computer, run `python -m pip install -r requirements-notebook.txt`, then `jupyter notebook notebooks/distance_analysis.ipynb` and choose **Run All**. The notebook and every chart identify the dataset as software-generated. The notebook was executed and its tables and four figures were checked locally.

## Limits and troubleshooting

- No data file can be called **real** until the laptop has actually received the 1,000 `DATA` lines. This workspace cannot access your lab board, so real capture and real model scores are pending your lab run.
- If no serial lines appear, check that Flash Magic is closed, the selected COM port is correct, the board is running rather than in ISP mode, CN9 cable is attached, and the terminal/capture baud is 9600. A blank distance with status 2 points to the ultrasonic sensor or its TRIG/VCC wiring, not the serial cable.
- The firmware sends one line per cycle. It still commands the original servo sweep; the new data export does not add or change motor movement.
- A 1000-row CSV is a small controlled lab dataset. It does not establish road safety or generalize to multiple people, changing angles or outdoor traffic.

The local software tests and a C syntax check pass. The modified firmware still needs to be built in Keil and tested on your actual board before the real capture can be claimed complete.
