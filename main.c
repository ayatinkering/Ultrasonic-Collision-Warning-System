/* LPC1768 adaptive ultrasonic proximity warning
 * ALS-SDA-ARMCTXM3-01: TRIG P2.0, protected ECHO P2.1,
 * LCD D4..D7 P0.23..26, RS P0.27, EN P0.28, buzzer P0.11.
 * Build with Keil LPC1768 CMSIS device pack (LPC17xx.h + startup/system).
 * IMPORTANT: bench prototype, NOT an automotive safety device.
 */
#include "LPC17xx.h"
#include <stdint.h>
#include <stdio.h>

#define TRIG (1UL<<0)
#define ECHO (1UL<<1)
#define BUZZ (1UL<<11)
#define LCD_DATA (15UL<<23)
#define LCD_RS (1UL<<27)
#define LCD_EN (1UL<<28)
#define SAMPLE_US 70000UL
#define ECHO_TIMEOUT_US 30000UL
#define MIN_CM 2.0f
#define MAX_CM 400.0f
#define BASE_WARN_CM 50.0f
#define MAX_WARN_CM 150.0f
#define CRITICAL_CM 20.0f
#define HYST_CM 5.0f
#define VELOCITY_GAIN_S 0.5f
#define FILTER_ALPHA 0.35f
#define INVALID_LIMIT 3U
#define RECOVERY_LIMIT 3U
/* Set to 0 if your board's buzzer is active LOW after testing. */
#define BUZZ_ACTIVE_HIGH 1
/* UART output requires UART0 cable, terminal, and SW21 run position. */
#define ENABLE_UART 0

typedef enum { SAFE, WARNING, CRITICAL, SENSOR_ERROR } State;
static State state = SENSOR_ERROR;
static float history[5], prev_filtered, smooth_velocity;
static uint8_t history_count=0, history_pos=0, have_previous=0;
static uint8_t invalid_count=0, valid_count=0;
static uint32_t prev_sample_us=0;

/* Timer0 runs continuously at 1 MHz; unsigned subtraction handles wrap. */
static uint32_t micros(void) { return LPC_TIM0->TC; }
static void wait_us(uint32_t us) {
    uint32_t start=micros();
    while ((uint32_t)(micros()-start)<us) { }
}
static void timer_init(void) {
    SystemCoreClockUpdate();
    LPC_SC->PCONP |= (1UL<<1);           /* Power Timer0 */
    LPC_SC->PCLKSEL0 = (LPC_SC->PCLKSEL0 & ~(3UL<<2)) | (1UL<<2);
    LPC_TIM0->TCR=2;                    /* Reset timer */
    LPC_TIM0->PR=(SystemCoreClock/1000000UL)-1UL;
    LPC_TIM0->TCR=1;                    /* Start timer */
}
static void gpio_init(void) {
    LPC_PINCON->PINSEL4 &= ~((3UL<<0)|(3UL<<2)); /* P2.0/1 GPIO */
    LPC_GPIO2->FIODIR = (LPC_GPIO2->FIODIR | TRIG) & ~ECHO;
    LPC_GPIO2->FIOCLR=TRIG;
    LPC_PINCON->PINSEL0 &= ~(3UL<<22); /* P0.11 GPIO */
    LPC_GPIO0->FIODIR |= BUZZ;
    LPC_PINCON->PINSEL1 &= ~((3UL<<14)|(3UL<<16)|(3UL<<18)|
                             (3UL<<20)|(3UL<<22)|(3UL<<24));
    LPC_GPIO0->FIODIR |= LCD_DATA|LCD_RS|LCD_EN;
}
static void buzzer(uint8_t on) {
#if BUZZ_ACTIVE_HIGH
    if(on) LPC_GPIO0->FIOSET=BUZZ; else LPC_GPIO0->FIOCLR=BUZZ;
#else
    if(on) LPC_GPIO0->FIOCLR=BUZZ; else LPC_GPIO0->FIOSET=BUZZ;
#endif
}
/* HD44780 LCD: 4-bit bus, write-only, no R/W connection. */
static void lcd_nibble(uint8_t nibble) {
    LPC_GPIO0->FIOCLR=LCD_DATA;
    LPC_GPIO0->FIOSET=((uint32_t)(nibble&15U)<<23);
    LPC_GPIO0->FIOSET=LCD_EN;
    wait_us(2);
    LPC_GPIO0->FIOCLR=LCD_EN;
    wait_us(50);
}
static void lcd_write(uint8_t value, uint8_t data) {
    if(data) LPC_GPIO0->FIOSET=LCD_RS;
    else LPC_GPIO0->FIOCLR=LCD_RS;
    lcd_nibble(value>>4);
    lcd_nibble(value);
    if(value==1 || value==2) wait_us(2000);
}
static void lcd_cmd(uint8_t x) { lcd_write(x,0); }
static void lcd_text(const char *s) { while(*s) lcd_write((uint8_t)*s++,1); }
static void lcd_init(void) {
    wait_us(40000);
    LPC_GPIO0->FIOCLR=LCD_RS|LCD_EN;
    lcd_nibble(3); wait_us(5000);
    lcd_nibble(3); wait_us(200);
    lcd_nibble(3); lcd_nibble(2);
    lcd_cmd(0x28); /* 4-bit, 2-line */
    lcd_cmd(0x0C); /* Display on */
    lcd_cmd(0x06); /* Increment cursor */
    lcd_cmd(0x01); /* Clear */
}
/* Returns 1 for valid distance, 0 for missing/out-of-range echo. */
static uint8_t ultrasonic_read(float *cm) {
    uint32_t start, rise, width;
    /* Wait for prior echo to become low; avoid stale pulse. */
    start=micros();
    while(LPC_GPIO2->FIOPIN&ECHO)
        if((uint32_t)(micros()-start)>ECHO_TIMEOUT_US) return 0;
    LPC_GPIO2->FIOCLR=TRIG;
    wait_us(3);
    LPC_GPIO2->FIOSET=TRIG;
    wait_us(12);
    LPC_GPIO2->FIOCLR=TRIG;
    start=micros();
    while(!(LPC_GPIO2->FIOPIN&ECHO))
        if((uint32_t)(micros()-start)>ECHO_TIMEOUT_US) return 0;
    rise=micros();
    while(LPC_GPIO2->FIOPIN&ECHO)
        if((uint32_t)(micros()-rise)>ECHO_TIMEOUT_US) return 0;
    width=(uint32_t)(micros()-rise);
    *cm=(float)width/58.3f;
    return (*cm>=MIN_CM && *cm<=MAX_CM);
}
static float median_distance(float x) {
    float a[5], tmp;
    uint8_t i,j,n;
    history[history_pos]=x;
    history_pos=(history_pos+1U)%5U;
    if(history_count<5) history_count++;
    n=history_count;
    for(i=0;i<n;i++) a[i]=history[i];
    for(i=1;i<n;i++) {
        tmp=a[i]; j=i;
        while(j>0 && a[j-1]>tmp) { a[j]=a[j-1]; j--; }
        a[j]=tmp;
    }
    return a[n/2];
}
static float clampf(float x,float lo,float hi) {
    return x<lo?lo:(x>hi?hi:x);
}
static const char *state_name(State s) {
    switch(s) {
        case SAFE: return "SAFE";
        case WARNING: return "WARNING";
        case CRITICAL: return "CRITICAL";
        default: return "SENSOR ERROR";
    }
}
/* No single valid reading clears a latched sensor error. */
static void classify(float filtered,float raw,float threshold) {
    float critical_observed=(raw<filtered)?raw:filtered;
    if(state==SENSOR_ERROR && valid_count<RECOVERY_LIMIT) return;
    if(critical_observed<=CRITICAL_CM) { state=CRITICAL; return; }
    if(state==CRITICAL && filtered<=CRITICAL_CM+HYST_CM) return;
    if(state==WARNING && filtered<=threshold+HYST_CM) return;
    state=(filtered<=threshold)?WARNING:SAFE;
}
static void display(float d,float v,float warn) {
    char line[17];
    int dist=(int)(d+0.5f), vel=(int)(v+0.5f);
    lcd_cmd(0x80);
    if(state==SENSOR_ERROR) {
        lcd_text("SENSOR ERROR    ");
        lcd_cmd(0xC0); lcd_text("CHECK HC-SR04  ");
        return;
    }
    snprintf(line,sizeof(line),"D:%3dcm V:%3d   ",dist,vel);
    lcd_text(line);
    lcd_cmd(0xC0);
    snprintf(line,sizeof(line),"%-8s W:%3d  ",state_name(state),(int)(warn+0.5f));
    lcd_text(line);
}
#if ENABLE_UART
static void uart_init(void) {
    LPC_SC->PCONP|=(1UL<<3);
    LPC_PINCON->PINSEL0=(LPC_PINCON->PINSEL0&~((3UL<<4)|(3UL<<6)))|
                          (1UL<<4)|(1UL<<6);
    LPC_SC->PCLKSEL0 &= ~(3UL<<6); /* UART0 PCLK = CCLK/4 */
    LPC_UART0->LCR=0x83;
    { uint32_t divisor=(SystemCoreClock/4UL)/(16UL*9600UL);
      LPC_UART0->DLL=(uint8_t)divisor;
      LPC_UART0->DLM=(uint8_t)(divisor>>8); }
    LPC_UART0->FDR=0x10;
    LPC_UART0->LCR=0x03;
    LPC_UART0->FCR=0x07;
}
static void uart_puts(const char *s) {
    while(*s) { while(!(LPC_UART0->LSR&(1UL<<5))) { }
                LPC_UART0->THR=(uint8_t)*s++; }
}
#endif
int main(void) {
    uint32_t cycle,dt_us;
    float raw=0, filtered=0, instantaneous=0, closing=0, warn=BASE_WARN_CM;
    float ttc=0;
#if ENABLE_UART
    char logline[120];
#endif
    timer_init(); gpio_init(); buzzer(0); lcd_init();
#if ENABLE_UART
    uart_init(); uart_puts("raw_cm,filtered_cm,closing_cm_s,threshold_cm,ttc_ms,state\r\n");
#endif
    while(1) {
        cycle=micros();
        if(ultrasonic_read(&raw)) {
            invalid_count=0;
            if(valid_count<RECOVERY_LIMIT) valid_count++;
            filtered=median_distance(raw);
            if(have_previous) {
                dt_us=(uint32_t)(cycle-prev_sample_us);
                if(dt_us>0) {
                    instantaneous=(prev_filtered-filtered)*1000000.0f/(float)dt_us;
                    instantaneous=clampf(instantaneous,-300.0f,300.0f);
                    smooth_velocity=FILTER_ALPHA*instantaneous+
                                    (1.0f-FILTER_ALPHA)*smooth_velocity;
                }
            } else { smooth_velocity=0; have_previous=1; }
            prev_filtered=filtered;
            prev_sample_us=cycle;
            closing=clampf(smooth_velocity,0.0f,300.0f);
            warn=clampf(BASE_WARN_CM+VELOCITY_GAIN_S*closing,
                        BASE_WARN_CM,MAX_WARN_CM);
            ttc=(closing>1.0f)?filtered/closing:0;
            classify(filtered,raw,warn);
        } else {
            valid_count=0;
            if(invalid_count<INVALID_LIMIT) invalid_count++;
            if(invalid_count>=INVALID_LIMIT) {
                state=SENSOR_ERROR;
                history_count=0; history_pos=0;
                have_previous=0; smooth_velocity=0;
            }
        }
        buzzer(state==CRITICAL);
        display(filtered,closing,warn);
#if ENABLE_UART
        snprintf(logline,sizeof(logline),"%d,%d,%d,%d,%d,%s\r\n",
          (int)raw,(int)filtered,(int)closing,(int)warn,(int)(ttc*1000),
          state_name(state));
        uart_puts(logline); /* TTC field is milliseconds, not seconds */
#endif
        /* Hold start-to-start period where possible; a timeout can overrun. */
        while((uint32_t)(micros()-cycle)<SAMPLE_US) { }
    }
}
