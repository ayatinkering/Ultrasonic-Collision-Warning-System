# Ultrasonic Collision Warning System

An embedded systems lab project using an **NXP LPC1768 (ARM Cortex-M3)** and **HC-SR04 ultrasonic sensor**. It measures obstacle distance and increases the warning distance when an object approaches faster. A **16×2 LCD** shows live readings; the **buzzer** sounds in the critical state.

**Status:** supplied firmware added; Keil compilation and testing on the physical ALS board are pending. This is a bench prototype, not an automotive safety device.

## Files

| File | Purpose |
| --- | --- |
| [main.c](main.c) | Complete single-file firmware: sensor, filtering, warning logic, LCD, buzzer, and optional serial logging |
| [docs/design-notes.md](docs/design-notes.md) | Research basis, algorithm details, and implementation limitations |
| [LICENSE](LICENSE) | Repository license |

A Keil project, CMSIS headers, startup files, and board clock configuration must be supplied through your development environment.

## How it works

1. Trigger the sensor and measure echo duration with Timer0 at nominal 1 µs resolution.
2. Convert echo width into distance; reject missing or out-of-range echoes.
3. Apply a five-sample median filter and estimate velocity from successive filtered distances.
4. Smooth velocity and adjust the warning boundary.
5. Update the LCD, buzzer, and optional UART log.

```text
warning distance (cm) = clamp(50 + 0.5 × closing velocity (cm/s), 50, 150)
```

For example, 50 cm/s closing velocity gives a 75 cm warning distance. This is an algorithm example, not a measured result.

| State | Behavior |
| --- | --- |
| SAFE | Filtered distance is outside the warning boundary |
| WARNING | Filtered distance reaches the adaptive warning boundary; LCD indicates warning |
| CRITICAL | Raw or filtered distance is at or below 20 cm; buzzer sounds |
| SENSOR ERROR | Startup state, or three consecutive invalid readings; LCD requests a sensor check, buzzer is off |

Hysteresis prevents repeated switching near a boundary: CRITICAL clears above 25 cm filtered distance, and WARNING clears above the current warning threshold plus 5 cm. Three consecutive valid readings are required to leave SENSOR ERROR, including at startup. Critical classification is also held off during recovery.

## Hardware and wiring

Required: ALS-SDA-ARMCTXM3-01 LPC1768 trainer board, HC-SR04, 16×2 LCD, onboard buzzer, jumper/ribbon connections, echo-divider resistors, and the lab's programming interface.

These connections come from the supplied project notes. Confirm physical connector orientation and jumper settings against your kit manual before powering the board.

| Connection | Board pin / setup |
| --- | --- |
| HC-SR04 TRIG | CN6 pin 1 → P2.0 |
| HC-SR04 ECHO | Divider output → CN6 pin 2 / P2.1 |
| Sensor +5 V | CN6 pin 25, JP1 shorted |
| Common GND | CN6 pin 26 |
| LCD D4–D7 | P0.23–P0.26 |
| LCD RS / EN | P0.27 / P0.28 |
| LCD ribbon / jumpers | CND → CNAD; JP5 and JP16 shorted |
| Buzzer | P0.11; CNA → CNA5 |

**Protect the echo input:** do not connect the sensor's 5 V ECHO directly to P2.1. Use the supplied divider:

```text
HC-SR04 ECHO ── 1 kΩ ── 1 kΩ ──┬── P2.1
                               │
                             2.2 kΩ
                               │
                              GND
```

This gives approximately 2.62 V for a 5 V input. Verify the divider output before connecting P2.1. Make wiring changes with power off.

The LCD is write-only; its R/W line must be held low by the board wiring. The buzzer shares CNA with other peripherals: do not connect the LED-bank or seven-segment ribbon to CNA at the same time.

## Build and flash

1. In **Keil µVision**, create a project targeting **NXP LPC1768**.
2. Install/select LPC1700 CMSIS device support. Include the device startup and system initialization files; confirm that `LPC17xx.h` resolves.
3. Add [`main.c`](main.c) to the source group. Use the board's correct clock configuration: `SystemCoreClock` must match the actual clock for accurate timing.
4. Open **Options for Target → Output**, enable **Create HEX File**, and build.
5. Check wiring and buzzer polarity. If the buzzer is active low, set `BUZZ_ACTIVE_HIGH` to `0` and rebuild.
6. Flash the HEX file using **Flash Magic** and the lab's UART0/RS232 connection. Follow the kit's ISP, jumper, and reset procedure; exit ISP mode before running.

## LCD output

```text
D: 75cm V: 50
WARNING  W: 75
```

`D` is filtered distance in cm, `V` is closing velocity in cm/s, and `W` is the adaptive warning distance in cm. Receding motion is displayed as zero closing velocity.

## Optional serial logging

Set `ENABLE_UART` to `1` and rebuild. Connect the lab's UART0 serial interface and use **9600 baud, 8N1, no flow control**, with SW21 in the kit's run position.

```csv
raw_cm,filtered_cm,closing_cm_s,threshold_cm,ttc_ms,state
```

Data is transmitted as integers. Time to collision (TTC) is diagnostic only and is logged in **milliseconds**. Zero means no estimate at the configured low-velocity cutoff. Invalid cycles can retain previous values; see the [fault and telemetry limitations](docs/design-notes.md).

## Parameters

Settings are near the top of `main.c`. These are initial values for lab evaluation.

| Setting | Default |
| --- | --- |
| Sample interval / echo timeout | 70 ms / 30 ms per wait phase |
| Valid range | 2–400 cm |
| Median window / velocity smoothing | 5 samples / α = 0.35 |
| Instantaneous velocity clamp | −300 to +300 cm/s |
| Baseline / maximum warning distance | 50 cm / 150 cm |
| Velocity gain | 0.5 s |
| Critical distance / hysteresis | 20 cm / 5 cm |
| Consecutive invalid / recovery samples | 3 / 3 |
| Buzzer polarity / UART | Active high / disabled |

## Lab validation checklist

- [ ] Confirm connector orientation, supplies, echo divider, and buzzer polarity.
- [ ] Build in Keil and flash successfully.
- [ ] Compare distance with a ruler at 10, 20, 50, 100, 150, and 200 cm.
- [ ] Move a flat target slowly and quickly; record velocity and warning activation distance.
- [ ] Hold the target near the warning boundary and check hysteresis.
- [ ] Verify the critical buzzer at or below 20 cm and clearance above 25 cm filtered distance.
- [ ] Disconnect echo with power off, then run a fault test. Restore with power off and verify recovery after three valid readings.
- [ ] Measure sampling timing and response latency, including with UART enabled.
- [ ] Compare adaptive warnings with a fixed 50 cm baseline using equivalent recorded data.

Record actual results before claiming accuracy, earlier warnings, or improved stability. A single ultrasonic beam measures range; velocity and TTC assume a consistent target moving approximately along that beam.
