# Research basis and implementation notes

This project follows the supplied draft, **“Design and Implementation of a Velocity-Adaptive Ultrasonic Collision Warning System with Hysteresis-Based Risk Classification on ARM Cortex-M3.”** Its proposed experiments and expected improvements are not completed results.

## Processing model

- **Distance:** echo duration in microseconds divided by `58.3` gives distance in cm. Accepted measurements are 2–400 cm.
- **Filtering:** a rolling window of up to five valid distances is sorted to select the middle value. During warm-up, even-sized windows select the upper middle value.
- **Velocity:** `(previous_filtered − current_filtered) / elapsed_seconds` is positive for approach. The instantaneous estimate is clamped to ±300 cm/s and exponentially smoothed with α = 0.35.
- **Warning distance:** `clamp(50 + 0.5 × max(0, smoothed_velocity), 50, 150)` cm.
- **Critical detection:** the smaller of raw and filtered distance can trigger CRITICAL at 20 cm, once sensor recovery has completed.
- **Hysteresis:** CRITICAL is retained through 25 cm filtered distance; WARNING is retained through the current adaptive threshold plus 5 cm.
- **TTC:** filtered distance divided by closing velocity when closing velocity exceeds 1 cm/s; otherwise zero. TTC does not control the warning state.

## Timing and faults

Timer0 runs at a nominal 1 MHz. Unsigned timestamp subtraction handles counter wraparound. Accurate timing depends on the CMSIS clock configuration and a clock that permits the intended prescaler division.

The loop targets a 70 ms start-to-start period. Acquisition and peripheral work are blocking. Echo waits have individual 30 ms timeouts; a delayed pulse or serial output can make a cycle longer than 70 ms. The design uses polling rather than timer capture interrupts or an RTOS.

The system starts in SENSOR ERROR. Three consecutive valid readings permit classification. Three consecutive invalid readings latch SENSOR ERROR and reset filter and velocity history. One or two invalid readings retain the prior classification and displayed values, including the prior buzzer state. The fault state turns the buzzer off; it is not a fail-safe audible alarm.

UART emits a row every cycle, including invalid cycles. There is no per-sample validity field: raw data can be stale or rejected, and filtered distance, velocity, threshold, and TTC can retain earlier values. A non-error state does not prove that the current row contains a valid measurement. Exclude ambiguous rows from quantitative analysis or add a validity field before collecting research data.

## Evaluation still required

Use measured reference distances and repeatable target approaches to evaluate distance error, warning activation distance, warning lead time, state-transition stability, and execution timing. Compare fixed and adaptive thresholds on equivalent input data. Record trial counts, target geometry, and test conditions with results.

The supplied firmware has been preserved. The paper's literature review and bibliography have not been independently verified here. A single ultrasonic beam does not establish vehicle trajectory, and this lab prototype does not provide validated collision protection.
