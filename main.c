/* ALS-SDA-ARMCTXM3-01: ultrasonic, PIR, LCD, buzzer, LEDs, seven segment.
 * EXACT prior wiring preserved: TRIG CN6-7/P0.10, ECHO divider CN6-8/P0.11,
 * PIR OUT CN6-23/P2.2 OR CN6-24/P2.3, LCD CND->CNAD,
 * buzzer CNB-1->CNA5-8,
 * LD2 CNB-2->CNA1-1, board +5V CN6-25 and GND CN6-26.
 * ADD: CNC->CNA2 ten-pin ribbon; four individual digit-select jumpers:
 * CN6-2/P2.1 -> CNB2-1 A, CN6-11/P0.6 -> CNB2-2 B,
 * CN6-9/P0.8 -> CNB2-3 C, CN6-10/P0.9 -> CNB2-4 D.
 * ADD: CNB-3/P1.25 -> CNA1-2 LD3. Do NOT connect CNB->CNB2 ribbon.
 * SERVO SIGNAL: P2.0/CN6-1 (must be physically connected).
 * Servo power: regulated external 5V supply, common GND with LPC1768.
 * LCD row 1 counts intrusion events (OFF -> ALARM), not individual beeps.
 * LCD row 2 shows PIR status. 7-segment shows cm, or ---- if invalid.
 * Alarm: 15..30 cm continuous; below 15 cm = 80ms on, 120ms off;
 * more than 30cm or invalid echo = off. LED LD2+LD3 mirror buzzer.
 * Lab startup must call SystemInit() before main. Only one main.c in Keil.
 * Segment mapping assumes CNA2 pins1..8 correspond to segments A..H.
 * Default SEGMENT_ACTIVE_LOW=1 for common-anode segment driver.
 * If all segments remain dark, see polarity and hardware checks below.
 * DATA EXPORT: UART0 on the board's existing RS232 CN9 connector sends one
 * DATA line per ultrasonic reading at 9600 baud, 8N1. Close Flash Magic,
 * set SW21 to run, and open the same COM port in the PC capture script.
 * Format: DATA,sequence,board_time_ms,distance_cm,valid,servo_pulse_us,status
 * A failed echo has an EMPTY distance field and valid=0. No PIR value is used
 * for machine learning. The pulse is a commanded PWM width, not a measured
 * physical angle. The servo sweep and all alarm/display behavior stay as-is.
 */
#include "LPC17xx.h"
#include <stdint.h>

#define TRIG      (1UL << 10)
#define ECHO      (1UL << 11)
#define PIR       ((1UL << 2) | (1UL << 3)) /* accept CN6-23 or CN6-24 */
#define BUZZER    (1UL << 23) /* P1.23, CNB pin 1 */
#define ALERT_LEDS ((1UL << 24) | (1UL << 25)) /* P1.24 LD2 + P1.25 LD3 */
#define SEGMENT_ACTIVE_LOW 1U /* Set 0 if display is common-cathode */
#define DIGIT_REVERSE 0U /* Set 1 if displayed digits are reversed */
#define SEG_MASK   (0xFFUL << 15) /* P0.15..P0.22 via CNC->CNA2 */
#define SELECT2_MASK (1UL << 1) /* P2.1 digit A */
#define SELECT0_MASK ((1UL << 6) | (1UL << 8) | (1UL << 9)) /* P0.6 B, P0.8 C, P0.9 D */
#define ALARM_OFF 0U
#define ALARM_STEADY 1U
#define ALARM_FAST 2U
#define FAST_PERIOD_MS 200U
#define SERVO_MIN_US 1000U
#define SERVO_MAX_US 2000U
#define SERVO_STEP_US 10U
#define SERVO_STEP_INTERVAL_US 20000U
#define FAST_ON_MS 80U
static volatile unsigned int alarm_mode = ALARM_OFF;
static volatile uint32_t alarm_count = 0U;
static volatile uint32_t shown_distance = 0U;
static volatile unsigned int shown_valid = 0U;
/* Last commanded servo pulse, for recording scan position alongside distance.
 * This variable is observational: it does not alter servo_update() timing.
 */
static volatile uint32_t servo_pulse_us = SERVO_MIN_US;
static const uint8_t seg_digits[10] = {
    0x3FU, 0x06U, 0x5BU, 0x4FU, 0x66U,
    0x6DU, 0x7DU, 0x07U, 0x7FU, 0x6FU
};
#define PIR_WARMUP_US 60000000UL
#define LCD_DATA  (15UL << 23)
#define LCD_RS    (1UL << 27)
#define LCD_EN    (1UL << 28)
#define TIMEOUT_US 30000UL
#define SAMPLE_US  100000UL
#define DIST_OK      0U
#define ECHO_HIGH    1U
#define NO_RISE      2U
#define NO_FALL      3U
#define OUT_OF_RANGE 4U

static uint32_t now_us(void)
{
    return LPC_TIM0->TC;
}

static void wait_us(uint32_t duration)
{
    uint32_t start = now_us();
    while ((uint32_t)(now_us() - start) < duration) { }
}

static void timer_init(void)
{
    LPC_SC->PCONP |= (1UL << 1); /* Timer0 power */
    LPC_SC->PCLKSEL0 = (LPC_SC->PCLKSEL0 & ~(3UL << 2)) | (1UL << 2);
    LPC_TIM0->TCR = 2U; /* reset timer */
    LPC_TIM0->CTCR = 0U; /* timer mode */
    LPC_TIM0->MCR = 0U;  /* free-running: no match reset/stop */
    LPC_TIM0->CCR = 0U;  /* no capture interrupts */
    LPC_TIM0->IR = 0x3FU;
    LPC_TIM0->PR = SystemCoreClock / 1000000UL - 1UL; /* 1 tick = 1 us */
    LPC_TIM0->TCR = 1U;
}

/* Hardware PWM1.1 on P2.0: 50 Hz servo pulses independent of delays. */
static void servo_init(void)
{
    LPC_SC->PCONP |= (1UL << 6); /* PWM1 peripheral power */
    LPC_SC->PCLKSEL0 = (LPC_SC->PCLKSEL0 & ~(3UL << 12)) | (1UL << 12);
    LPC_PINCON->PINSEL4 = (LPC_PINCON->PINSEL4 & ~3UL) | 1UL; /* P2.0 PWM1.1 */
    LPC_PINCON->PINMODE_OD2 &= ~(1UL << 0);
    LPC_PWM1->TCR = 2U;
    LPC_PWM1->PR = SystemCoreClock / 1000000UL - 1UL;
    LPC_PWM1->MCR = (1UL << 1); /* reset on MR0 */
    LPC_PWM1->MR0 = 20000U; /* 20 ms = 50 Hz */
    LPC_PWM1->MR1 = SERVO_MIN_US;
    LPC_PWM1->LER = (1UL << 0) | (1UL << 1);
    LPC_PWM1->PCR |= (1UL << 9); /* enable PWM1.1 output */
    LPC_PWM1->TCR = (1UL << 0) | (1UL << 3);
}

static void servo_update(void)
{
    static uint32_t last_step = 0U;
    static uint32_t pulse = SERVO_MIN_US;
    static int direction = 1;
    uint32_t t = now_us();
    if ((uint32_t)(t - last_step) < SERVO_STEP_INTERVAL_US) return;
    last_step = t;
    if (direction > 0) {
        if (pulse + SERVO_STEP_US >= SERVO_MAX_US) {
            pulse = SERVO_MAX_US;
            direction = -1;
        } else pulse += SERVO_STEP_US;
    } else {
        if (pulse <= SERVO_MIN_US + SERVO_STEP_US) {
            pulse = SERVO_MIN_US;
            direction = 1;
        } else pulse -= SERVO_STEP_US;
    }
    LPC_PWM1->MR1 = pulse;
    LPC_PWM1->LER = (1UL << 1);
    servo_pulse_us = pulse;
}

/* UART0 is hardwired through the board's RS232 converter to DB9 CN9.
 * P0.2 is TXD0 and P0.3 is RXD0; no new breadboard connection is needed.
 * Set its peripheral clock to SystemCoreClock and choose the nearest integer
 * baud divisor. At 9600 baud, each short line finishes within one 100 ms
 * sensor cycle. During transmission we keep calling servo_update() so the
 * existing back-and-forth sweep remains smooth.
 */
static void uart0_init(void)
{
    uint32_t divisor;
    LPC_SC->PCONP |= (1UL << 3); /* power UART0 */
    LPC_SC->PCLKSEL0 = (LPC_SC->PCLKSEL0 & ~(3UL << 6)) | (1UL << 6);
    LPC_PINCON->PINSEL0 =
        (LPC_PINCON->PINSEL0 & ~((3UL << 4) | (3UL << 6))) |
        (1UL << 4) | (1UL << 6); /* TXD0 / RXD0 */
    divisor = (SystemCoreClock + 76800UL) / 153600UL; /* rounded CCLK/(16*9600) */
    if (divisor == 0U) divisor = 1U;
    LPC_UART0->LCR = 0x83U; /* 8 data bits, no parity, 1 stop bit, DLAB=1 */
    LPC_UART0->DLM = (divisor >> 8) & 0xFFU;
    LPC_UART0->DLL = divisor & 0xFFU;
    LPC_UART0->FDR = 0x10U; /* multiplier 1, fractional add 0 */
    LPC_UART0->LCR = 0x03U; /* DLAB=0, keep 8N1 */
    LPC_UART0->FCR = 0x07U; /* enable and clear transmit/receive FIFOs */
}

static void uart0_char(char ch)
{
    while ((LPC_UART0->LSR & (1UL << 5)) == 0U) servo_update();
    LPC_UART0->THR = (uint32_t)(uint8_t)ch;
}

static void uart0_text(const char *message)
{
    while (*message != '\0') uart0_char(*message++);
}

/* Print nonnegative integers without printf or a large C library dependency. */
static void uart0_uint(uint32_t value)
{
    char digits[10];
    unsigned int count = 0U;
    do {
        digits[count++] = (char)('0' + value % 10U);
        value /= 10U;
    } while (value != 0U);
    while (count != 0U) uart0_char(digits[--count]);
}

static void uart0_sample(uint32_t sequence, uint32_t time_us,
                         unsigned int distance, unsigned int status,
                         uint32_t pulse_us)
{
    /* One line is easy for the laptop to identify and save as a CSV row. */
    uart0_text("DATA,");
    uart0_uint(sequence);
    uart0_char(',');
    uart0_uint(time_us / 1000U);
    uart0_char(',');
    if (status == DIST_OK) uart0_uint(distance);
    uart0_char(',');
    uart0_uint(status == DIST_OK ? 1U : 0U);
    uart0_char(',');
    uart0_uint(pulse_us);
    uart0_char(',');
    uart0_uint(status); /* 0=good; 1=stuck high; 2=no rise; 3=no fall; 4=range */
    uart0_text("\r\n");
}

static void sensor_pins_init(void)
{
    LPC_PINCON->PINSEL0 &= ~((3UL << 20) | (3UL << 22)); /* GPIO P0.10/11 */
    LPC_PINCON->PINSEL4 &= ~((3UL << 4) | (3UL << 6)); /* P2.2/2.3 GPIO */
    /* Pull-downs keep disconnected inputs from floating HIGH. */
    LPC_PINCON->PINMODE0 =
        (LPC_PINCON->PINMODE0 & ~(3UL << 22)) | (3UL << 22);
    LPC_PINCON->PINMODE4 =
        (LPC_PINCON->PINMODE4 & ~((3UL << 4) | (3UL << 6))) |
        (3UL << 4) | (3UL << 6);
    LPC_PINCON->PINMODE_OD0 &= ~TRIG;
    LPC_GPIO0->FIOMASK &= ~(TRIG | ECHO);
    LPC_GPIO2->FIOMASK &= ~PIR;
    LPC_GPIO0->FIOCLR = TRIG;
    LPC_GPIO0->FIODIR = (LPC_GPIO0->FIODIR | TRIG) & ~ECHO;
    LPC_GPIO2->FIODIR &= ~PIR;

    /* LCD pins and the seven-segment data pins share GPIO0, not bits. */
}

static void select_blank(void)
{
    /* BCD 4: selects an unused decoder output, blanking all 4 digits. */
    LPC_GPIO2->FIOCLR = SELECT2_MASK;
    LPC_GPIO0->FIOCLR = SELECT0_MASK;
    LPC_GPIO0->FIOSET = (1UL << 8);
}

static void select_digit(unsigned int n)
{
    LPC_GPIO2->FIOCLR = SELECT2_MASK;
    LPC_GPIO0->FIOCLR = SELECT0_MASK;
    if (n & 1U) LPC_GPIO2->FIOSET = (1UL << 1); /* A */
    if (n & 2U) LPC_GPIO0->FIOSET = (1UL << 6); /* B */
    /* C and D remain LOW for 0..3, but have individual control wires. */
}

static void display_alarm_pins_init(void)
{
    /* CNC pins1..8 = P0.15..22: segment data, independent of LCD. */
    LPC_PINCON->PINSEL0 &= ~(3UL << 30);
    LPC_PINCON->PINSEL1 &= ~0x3FFFUL;
    LPC_GPIO0->FIOMASK &= ~SEG_MASK;
#if SEGMENT_ACTIVE_LOW
    LPC_GPIO0->FIOSET = SEG_MASK; /* All segments off before scanning */
#else
    LPC_GPIO0->FIOCLR = SEG_MASK;
#endif
    LPC_GPIO0->FIODIR |= SEG_MASK;

    /* Select A uses P2.1; B,C,D use P0.6,P0.8,P0.9. */
    LPC_PINCON->PINSEL4 &= ~(3UL << 2);
    LPC_PINCON->PINSEL0 &= ~((3UL << 12) | (3UL << 16) | (3UL << 18));
    LPC_PINCON->PINMODE_OD2 &= ~SELECT2_MASK;
    LPC_PINCON->PINMODE_OD0 &= ~(SELECT0_MASK | SEG_MASK);
    LPC_GPIO2->FIOMASK &= ~SELECT2_MASK;
    LPC_GPIO0->FIOMASK &= ~SELECT0_MASK;
    select_blank();
    LPC_GPIO2->FIODIR |= SELECT2_MASK;
    LPC_GPIO0->FIODIR |= SELECT0_MASK;

    /* Existing CNB1 P1.23 buzzer + CNB2 P1.24 LD2; add P1.25 LD3. */
    LPC_PINCON->PINSEL3 &= ~((3UL << 14) | (3UL << 16) | (3UL << 18));
    LPC_PINCON->PINMODE_OD1 &= ~(BUZZER | ALERT_LEDS);
    LPC_GPIO1->FIOMASK &= ~(BUZZER | ALERT_LEDS);
    LPC_GPIO1->FIOCLR = BUZZER | ALERT_LEDS;
    LPC_GPIO1->FIODIR |= BUZZER | ALERT_LEDS;
}

/* Timer1 runs at 1 MHz and interrupts every 1 ms. */
static void display_timer_init(void)
{
    LPC_SC->PCONP |= (1UL << 2);
    LPC_SC->PCLKSEL0 =
        (LPC_SC->PCLKSEL0 & ~(3UL << 4)) | (1UL << 4);
    LPC_TIM1->TCR = 2U;
    LPC_TIM1->CTCR = 0U;
    LPC_TIM1->PR = SystemCoreClock / 1000000UL - 1UL;
    LPC_TIM1->MCR = (1UL << 1) | (1UL << 0); /* reset and interrupt on MR0 */
    LPC_TIM1->MR0 = 1000U;
    LPC_TIM1->IR = 0x3FU;
    NVIC_EnableIRQ(TIMER1_IRQn);
    LPC_TIM1->TCR = 1U;
}

void TIMER1_IRQHandler(void)
{
    static uint32_t millis = 0U;
    static unsigned int active_digit = 0U;
    static unsigned int previous_mode = ALARM_OFF;

    static uint32_t phase_start = 0U;
    uint32_t value, divisor;
    unsigned int digit, sound, mode;
    uint8_t pattern;

    LPC_TIM1->IR = 1U; /* clear MR0 interrupt */
    ++millis;

    /* Show ---- when the ultrasonic measurement is invalid. */
    select_blank();
    if (!shown_valid) {
        pattern = 0x40U; /* G segment: dash */
    } else {
        value = shown_distance;
        if (value > 9999U) value = 9999U;
        divisor = (active_digit == 0U) ? 1000U :
                  (active_digit == 1U) ? 100U :
                  (active_digit == 2U) ? 10U : 1U;
        digit = (unsigned int)((value / divisor) % 10U);
        pattern = (value < divisor && active_digit < 3U) ?
                  0U : seg_digits[digit];
    }
    /* On common-anode displays a LOW turns a segment ON. */
#if SEGMENT_ACTIVE_LOW
    pattern = (uint8_t)~pattern;
#endif
    LPC_GPIO0->FIOCLR = SEG_MASK;
    LPC_GPIO0->FIOSET = (uint32_t)pattern << 15;
#if DIGIT_REVERSE
    select_digit(3U - active_digit);
#else
    select_digit(active_digit);
#endif
    active_digit = (active_digit + 1U) & 3U;

    mode = alarm_mode;
    if (mode != previous_mode) {
        if (previous_mode == ALARM_OFF && mode != ALARM_OFF) ++alarm_count;
        previous_mode = mode;
        phase_start = millis;
    }
    sound = (mode == ALARM_STEADY) ||
            (mode == ALARM_FAST &&
             ((uint32_t)(millis - phase_start) % FAST_PERIOD_MS) < FAST_ON_MS);
    if (sound) {
        LPC_GPIO1->FIOSET = BUZZER | ALERT_LEDS;

    } else {
        LPC_GPIO1->FIOCLR = BUZZER | ALERT_LEDS;
    }

}

static void alarm_update(unsigned int distance, unsigned int status)
{
    unsigned int mode = ALARM_OFF;
    if (status == DIST_OK) {
        if (distance < 15U) mode = ALARM_FAST;
        else if (distance <= 30U) mode = ALARM_STEADY;
    }
    alarm_mode = mode;
}

static unsigned int measure_cm(unsigned int *distance)
{
    uint32_t begin, rise, width;
    *distance = 0U;

    /* ECHO should be LOW before sending a new trigger. */
    begin = now_us();
    while (LPC_GPIO0->FIOPIN & ECHO) {
        if ((uint32_t)(now_us() - begin) >= TIMEOUT_US) return ECHO_HIGH;
    }

    LPC_GPIO0->FIOCLR = TRIG;
    wait_us(3U);
    LPC_GPIO0->FIOSET = TRIG;
    wait_us(12U);
    LPC_GPIO0->FIOCLR = TRIG;

    begin = now_us();
    while (!(LPC_GPIO0->FIOPIN & ECHO)) {
        if ((uint32_t)(now_us() - begin) >= TIMEOUT_US) return NO_RISE;
    }
    rise = now_us();
    while (LPC_GPIO0->FIOPIN & ECHO) {
        if ((uint32_t)(now_us() - rise) >= TIMEOUT_US) return NO_FALL;
    }
    width = (uint32_t)(now_us() - rise);
    if (width < 116UL || width > 23200UL) return OUT_OF_RANGE;
    *distance = (unsigned int)((width + 29UL) / 58UL);
    return DIST_OK;
}

static void lcd_nibble(unsigned int value)
{
    LPC_GPIO0->FIOCLR = LCD_DATA;
    LPC_GPIO0->FIOSET = (uint32_t)(value & 15U) << 23;
    LPC_GPIO0->FIOSET = LCD_EN;
    wait_us(2U);
    LPC_GPIO0->FIOCLR = LCD_EN;
    wait_us(50U);
}

static void lcd_write(unsigned int value, unsigned int data)
{
    if (data) LPC_GPIO0->FIOSET = LCD_RS;
    else LPC_GPIO0->FIOCLR = LCD_RS;
    lcd_nibble(value >> 4);
    lcd_nibble(value);
    if (value == 1U || value == 2U) wait_us(2000U);
}

static void lcd_line(unsigned int row, const char *message)
{
    unsigned int column;
    lcd_write(row == 0U ? 0x80U : 0xC0U, 0U);
    for (column = 0U; column < 16U; ++column) {
        if (*message) lcd_write((unsigned int)(uint8_t)*message++, 1U);
        else lcd_write((unsigned int)' ', 1U);
    }
}

static void lcd_init(void)
{
    LPC_PINCON->PINSEL1 &= ~((3UL << 14) | (3UL << 16) | (3UL << 18) |
                              (3UL << 20) | (3UL << 22) | (3UL << 24));
    LPC_GPIO0->FIOMASK &= ~(LCD_DATA | LCD_RS | LCD_EN);
    LPC_GPIO0->FIOCLR = LCD_DATA | LCD_RS | LCD_EN;
    LPC_GPIO0->FIODIR |= LCD_DATA | LCD_RS | LCD_EN;
    wait_us(40000U);
    lcd_nibble(3U); wait_us(5000U);
    lcd_nibble(3U); wait_us(200U);
    lcd_nibble(3U); lcd_nibble(2U);
    lcd_write(0x28U, 0U);
    lcd_write(0x0CU, 0U);
    lcd_write(0x06U, 0U);
    lcd_write(0x01U, 0U);
}

static void show_alarm_count(uint32_t value)
{
    char line[17] = "INTRUSIONS:00000";
    unsigned int i;
    for (i = 0U; i < 5U; ++i) {
        line[15U - i] = (char)('0' + value % 10U);
        value /= 10U;
    }
    lcd_line(0U, line);
}

static void show_pir(unsigned int high, unsigned int seconds_left)
{
    char line[17] = "PIR WAIT 60s 0";
    if (seconds_left != 0U) {
        line[9] = (char)('0' + seconds_left / 10U);
        line[10] = (char)('0' + seconds_left % 10U);
        line[13] = high ? '1' : '0';
        lcd_line(1U, line);
    } else if (high) {
        lcd_line(1U, "PIR: MOTION");
    } else {
        lcd_line(1U, "PIR: NO MOTION");
    }
}

int main(void)
{
    uint32_t cycle, warmup_start, elapsed;
    uint32_t sample_sequence = 0U, sample_pulse;
    unsigned int distance, status, pir_high, seconds_left;
    unsigned int warming = 1U;

    /* The lab's CMSIS startup calls SystemInit() before main(). */
    SystemCoreClockUpdate();
    timer_init();
    uart0_init();
    sensor_pins_init();
    lcd_init();
    display_alarm_pins_init();
    servo_init();
    display_timer_init();
    uart0_text("LPC1768 LOGGER READY 9600 8N1\r\n");
    warmup_start = now_us();

    for (;;) {
        cycle = now_us();
        servo_update();
        sample_pulse = servo_pulse_us; /* pulse at start of this reading */
        status = measure_cm(&distance);
        shown_valid = 0U;
        shown_distance = distance;
        shown_valid = (status == DIST_OK) ? 1U : 0U;
        alarm_update(distance, status);
        show_alarm_count(alarm_count);

        pir_high = (LPC_GPIO2->FIOPIN & PIR) ? 1U : 0U;
        seconds_left = 0U;
        if (warming) {
            elapsed = (uint32_t)(now_us() - warmup_start);
            if (elapsed >= PIR_WARMUP_US) {
                warming = 0U;
            } else {
                seconds_left = (unsigned int)
                    ((PIR_WARMUP_US - elapsed + 999999UL) / 1000000UL);
            }
        }
        show_pir(pir_high, seconds_left);
        /* Log the SAME ultrasonic result shown by this unchanged alarm loop.
         * Invalid readings remain in the 1000-row CSV so missing data is
         * visible; the ML trainer will skip unusable history windows.
         */
        uart0_sample(sample_sequence++, cycle, distance, status, sample_pulse);
        while ((uint32_t)(now_us() - cycle) < SAMPLE_US) {
            servo_update();
        }
    }
}
