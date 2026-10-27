"""Save exactly 1,000 REAL ultrasonic samples from the existing LPC1768 firmware.

The board sends one ASCII line per sensor cycle through UART0/CN9:
    DATA,sequence,board_time_ms,distance_cm,valid,servo_pulse_us,status

This script never invents a reading. It waits for 20 deliberate five-second
trials, each containing 50 consecutive board samples. The first 5 samples
are enough to start a history; a later sample supplies the 0.5-second label.
PIR is deliberately absent because it is not used for the ML experiment.

Install once on the laptop: python -m pip install pyserial
Typical Windows command: python scripts/capture_1000.py --port COM4 --sensor-mode fixed
"""

import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path


SCENARIOS = ("approach", "move_away", "stop_before_zone", "pass_by")
TRIALS_PER_SCENARIO = 5
ROWS_PER_TRIAL = 50
FIELDS = ("trial_id", "scenario", "time_ms", "distance_cm", "valid",
          "servo_pulse_us", "status_code", "board_seq", "board_time_ms")


def parse_board_line(raw: bytes):
    """Return one validated DATA record, or None for startup/noise lines.

    An empty distance is expected when the ultrasonic echo fails. The status
    number is preserved, so missing readings are visible in the CSV rather
    than silently replaced by made-up distances.
    """
    parts = raw.decode("ascii", errors="ignore").strip().split(",")
    if len(parts) != 7 or parts[0] != "DATA":
        return None
    try:
        sequence = int(parts[1])
        board_ms = int(parts[2])
        distance = parts[3]
        valid = int(parts[4])
        pulse = int(parts[5])
        status = int(parts[6])
        if not (0 <= sequence <= 0xFFFFFFFF and 0 <= board_ms <= 0xFFFFFFFF):
            return None
        if valid not in (0, 1) or status not in range(5):
            return None
        if not 1000 <= pulse <= 2000:
            return None
        if valid:
            if status != 0 or not distance.isdigit() or not 2 <= int(distance) <= 400:
                return None
        elif status == 0 or distance:
            return None
        return sequence, board_ms, distance, valid, pulse, status
    except ValueError:
        return None


def read_trial(board, trial_id: str, scenario: str):
    """Read one uninterrupted 50-row trial; reject missing serial packets."""
    rows = []
    previous_sequence = None
    first_ms = None
    last_good_line = time.monotonic()
    while len(rows) < ROWS_PER_TRIAL:
        packet = parse_board_line(board.readline())
        if packet is None:
            if time.monotonic() - last_good_line > 5:
                raise RuntimeError("No valid DATA lines for 5 seconds; check COM port, CN9, SW21 and board power")
            continue
        last_good_line = time.monotonic()
        sequence, board_ms, distance, valid, pulse, status = packet
        if previous_sequence is not None and sequence != previous_sequence + 1:
            raise ValueError("A serial sample was lost; repeat this trial")
        previous_sequence = sequence
        if first_ms is None:
            first_ms = board_ms
        elapsed = board_ms - first_ms
        if elapsed < 0 or (rows and not 70 <= elapsed - int(rows[-1]["time_ms"]) <= 170):
            raise ValueError("Sample timing was interrupted; repeat this trial")
        rows.append({
            "trial_id": trial_id, "scenario": scenario, "time_ms": elapsed,
            "distance_cm": distance, "valid": valid, "servo_pulse_us": pulse,
            "status_code": status, "board_seq": sequence, "board_time_ms": board_ms,
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="COM port used by Flash Magic, e.g. COM4")
    parser.add_argument("--sensor-mode", required=True, choices=("fixed", "sweeping"),
                        help="Choose fixed only when the ultrasonic sensor stays pointed in one direction")
    parser.add_argument("--output", type=Path, default=Path("data/real_1000.csv"))
    args = parser.parse_args()
    try:
        import serial
    except ImportError as error:
        raise SystemExit("Install pyserial first: python -m pip install pyserial") from error

    # Open the existing RS232/USB-serial port, never a TTL wire to the MCU.
    # SW21 must be in run position so PC handshake lines cannot force ISP.
    all_rows = []
    failed_attempts = 0
    with serial.Serial(args.port, 9600, timeout=1, rtscts=False, dsrdtr=False) as board:
        board.dtr = False
        board.rts = False
        time.sleep(1)
        board.reset_input_buffer()
        print("Connected. The board should already be running main.c and sending DATA lines.")
        if args.sensor_mode == "sweeping":
            print("Recording the scan is fine, but the 0.5-second ML trainer will not treat it as one target's motion.")
        for round_number in range(1, TRIALS_PER_SCENARIO + 1):
            for scenario in SCENARIOS:
                trial_id = f"{scenario}_{round_number:02d}"
                while True:
                    input(f"{trial_id}: set up a NEW {scenario} walk; press Enter, then move for 5 seconds. ")
                    board.reset_input_buffer()
                    try:
                        rows = read_trial(board, trial_id, scenario)
                    except ValueError as error:
                        failed_attempts += 1
                        print(f"{error}. No rows from this attempt were saved.")
                        continue
                    all_rows.extend(rows)
                    print(f"Captured {len(rows)} rows; total {len(all_rows)}/1000")
                    break

    # Write only after all trials succeeded, so a partial file cannot be
    # mistaken for a complete 1,000-reading experiment.
    if len(all_rows) != 1000:
        raise RuntimeError("Internal error: capture did not produce exactly 1,000 rows")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(all_rows)
    temporary.replace(args.output)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    metadata = {
        "source": "LPC1768-UART0-CN9", "sensor_mode": args.sensor_mode,
        "readings": len(all_rows), "trials": 20, "samples_per_trial": 50,
        "invalid_readings": sum(row["valid"] == 0 for row in all_rows),
        "restarted_trials": failed_attempts, "baud": 9600,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "csv_sha256": digest,
    }
    sidecar = args.output.with_suffix(".capture.json")
    sidecar.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(all_rows)} REAL serial readings to {args.output}")
    print(f"Capture details saved to {sidecar}")


if __name__ == "__main__":
    main()
