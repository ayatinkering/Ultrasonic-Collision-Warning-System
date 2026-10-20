# LPC1768 ALS Board: Pin and Wiring Reference

Board: Advanced Electronic Systems ALS-SDA-ARMCTXM3-01 (ARM Cortex-M3 evaluation board, LPC1768FBD100 on a piggyback module, 12 MHz crystal).

Sources: the ALS user manual (ALS-SDA-ARMCTXM3-01-UM1), the MIT Manipal guideline, connection and troubleshooting sheets, the placement diagram, and your lab photo.

How to read this: **⚠** marks a place where the manual contradicts itself or says nothing, so check it on the board. **Derived** means I worked it out from the manual's connector tables assuming a straight 1:1 ribbon cable (pin n to pin n). The manual does not print it.

## 1. How the board is wired

- The LPC1768 sits on a piggyback module plugged into CN1 to CN4 (piggyback CN1 to base CN1, and so on).
- Port lines come out on four 10-pin FRC headers: **CNA, CNB, CNC, CND**. Pin 9 is mostly NC (CNC pin 9 is P2.13) and pin 10 is GND.
- Most peripheral blocks have their own FRC header (CNA1, CNA2, CNB1 and so on). You connect a GPIO header to a block header with a 10-core ribbon cable.
- The manual warns that the GPIO headers and the block headers are mapped 1:1. Use only the header pair the manual specifies for a block, and only with the pins used as GPIO.
- **Ribbon-wired blocks:** LEDs, 7-segment, both LCDs, keypad, relay/buzzer/motors, PWM/EXINT/match, SPI/I2C/RS485, I2S.
- **Hardwired blocks (no ribbon):** UART0, UART3, the ADC pots, DAC, CLKOUT, CAN, USB, Ethernet, reset/ISP, JTAG/trace.
- Always power the kit OFF before making or changing connections (lab rule). This includes browsing for the hex file.
- Pins are plain GPIO at power-on. Alternate functions need PINSEL settings.

## 2. Wiring cheat sheet

| Block | Ribbon cable(s) | MCU pins | Jumpers / switches | Sample hex |
| --- | --- | --- | --- | --- |
| 8 LEDs (LD2 to LD9) | CNA to CNA1 | P0.4 to P0.11 | none | GP\_LED, PORT\_TEST |
| 4-digit 7-segment | CNA to CNA2 (data) and CNB to CNB2 (digit select) | data P0.4 to P0.11, select P1.23 to P1.26 (derived) | none | Seven\_seg |
| 16x2 LCD | CND to CNAD | D4 to D7 = P0.23 to P0.26, RS = P0.27, EN = P0.28 (derived) | JP16 short, JP5 short, POT3 contrast | AN\_LCD |
| 128x64 graphic LCD | CNA to CNAD and CND to CND1 | data P0.4 to P0.11, control P0.23 to P0.28 (derived) | JP16 open, JP17 (2,3), JP5 short, POT2 contrast | GLCD |
| 4x4 keypad | CNB to CNB3 | P1.23 to P1.26 and P2.10 to P2.13 | JP4 (1,2) | KEY\_LCD (plus LCD setup) |
| Relay, buzzer, DC motor, stepper | CNA to CNA5 | P0.4 to P0.11 | none | Buzzer, Relay, DCM, STPM |
| PWM, ext. interrupt, match/capture | CNB to CNB1 | P1.23, P1.25, P1.26 and an EINT line | JP14 | PWM, EXINT, COMP\_MAT |
| SPI EEPROM, I2C RTC, RS485 | CNC to CNC1 | P0.15 to P0.22 (+P2.13) | JP12, JP13, JP15, JP4 (2,3), JP10, JP11 | SPI\_Test, I2C\_RTC, RS485\_Tx / RS485\_Rx |
| I2S demo | CNA to CNA4, plus flying leads at CN17 | P0.4 to P0.9 (+P0.10 for LD16) | none | I2S |
| UART0 (flashing and PC serial) | hardwired, DB9 CN9 | P0.2, P0.3 | SW21, JP3 | UART0\_Test |
| UART3 | hardwired, RM1 | see 3.11 | JP7 (1,2), JP8 (1,2) | UART3\_Test |
| ADC pots | hardwired | AD0.5 = P1.31, AD0.4 = P1.30 | JP18 (2,3) for AD0.4 | Int\_ADC5, Int\_ADC4 |
| DAC | hardwired, TP8 | P0.26 | JP5 open | Int\_DAC |
| CLKOUT | hardwired, TP9 | P1.27 | JP19 open | CLK\_Test |
| CAN1 / CAN2 | hardwired, RM2 | P0.0, P0.1 (CAN1) | JP7 (2,3), JP8 (2,3), JP9 | CAN |
| USB device / host | hardwired, CN15 / CN14 | P0.29, P0.30 | SW19, SW20, JP18, JP19 | USBHID, USBHost |
| Ethernet | hardwired, CN13 | P1.0 to P1.17 (RMII) | JP18 (2,3) | EMAC |

## 3. Block by block

### 3.1 General purpose LEDs (LD2 to LD9)

- CNA1 pins 1 to 8 go to the anodes of LD2 to LD9 in order. Active high (a high level turns the LED on). Cathodes go to ground through resistors. Pin 9 NC, pin 10 GND.
- With CNA to CNA1: LD2 = P0.4, LD3 = P0.5, LD4 = P0.6, LD5 = P0.7, LD6 = P0.8, LD7 = P0.9, LD8 = P0.10, LD9 = P0.11 (derived).
- Port line test: connect any one of CNA, CNB, CNC or CND to CNA1 (short JP4 (1,2) and JP5) and the LEDs toggle for each.

### 3.2 Seven-segment display (U8 to U11)

- Four multiplexed common-cathode digits, so segments are active high. Segment inputs: SEG\_A to SEG\_H (H is the decimal point). Data goes through buffer U12.
- **CNA2** carries the 8 segment lines. With CNA to CNA2 the data is P0.4 to P0.11. ⚠ The manual does not say which CNA2 pin is which segment. Check with the Seven\_seg code.
- **CNB2** pins 1 to 4 are inputs A, B, C, D (BCD) to decoder U7, a 1-of-10 decoder/driver that enables the digit. Pins 5 to 9 are NC, pin 10 GND. With CNB to CNB2: A to D = P1.23 to P1.26 (derived).
- Seven\_seg test counts 0000 to 9999 after reset.

### 3.3 16x2 alphanumeric LCD

- LCD plugs into CN11 (16-pin single-row female header). It runs in 4-bit mode, so only the upper 4 data lines are used.
- CN11: 1 GND, 2 +5V, 3 contrast (POT3), 4 RS, 5/7/8/9/10 NC, 6 EN, 11 to 14 = D4 to D7, 15 backlight anode, 16 backlight cathode.
- CNAD: pin 1 = D4 (CN11 pin 11), 2 = D5 (12), 3 = D6 (13), 4 = D7 (14), 5 = RS (CN11 pin 4), 6 = EN (CN11 pin 6).
- Wiring CND to CNAD gives: **D4 = P0.23, D5 = P0.24, D6 = P0.25, D7 = P0.26, RS = P0.27, EN = P0.28.**
- Short JP16 and JP5 (JP5 brings P0.26 to CND pin 4).
- R/W (CN11 pin 5) is not connected to the MCU, so the LCD is write-only. Use delays, not the busy flag.
- Use either this LCD or the graphic LCD, never both.

### 3.4 128x64 graphic LCD

- Plugs into CN10 (20x2 female header). The two rows are shorted pin to pin, so use either row.
- CN10: 1 GND, 2 +5V, 3 contrast (POT2), 4 RS, 5 R/W, 6 EN, 7 to 14 = BD0 to BD7, 15 CS1, 16 CS2, 17 reset, 18 negative voltage out (-5V), 19 backlight +, 20 backlight -.
- CNAD pins 1 to 8 = BD0 to BD7. CND1 pins 1 to 6 = RS, R/W, EN, CS1, CS2, reset.
- Wiring CNA to CNAD and CND to CND1 gives (derived): BD0 to BD7 = P0.4 to P0.11, RS = P0.23, R/W = P0.24, EN = P0.25, CS1 = P0.26, CS2 = P0.27, RST = P0.28.
- Jumpers: JP16 open, JP17 (2,3), JP5 short. Contrast is POT2.

### 3.5 4x4 keypad (SW3 to SW18)

- Switches are arranged as 4 rows by 4 columns. Rows are always outputs from the MCU. Columns are pulled to ground. A high level sent on a row appears on a column when the key is pressed.
- Connector CNB3. Wire CNB to CNB3 and short JP4 (1,2). That gives P1.23 to P1.26 on pins 1 to 4 and P2.10 to P2.13 on pins 5 to 8.
- ⚠ The manual does not say which CNB3 pins are rows and which are columns. Check with the KEY\_LCD code. It also needs the 16x2 LCD wiring. Watch P2.10 (ISP pin) and P2.13 (shared with JP4).

### 3.6 Relay, buzzer, DC motor, stepper motor

- Driven through the ULN2803 (U13). The manual quotes up to 300 mA at about 0.7 V.
- CNA5 pins: 1 to 4 = stepper phases (buffered by U13), 5 = relay K2 coil, 6 = linked to inputs 1 and 2 of U13 and from there to the NO/NC of relay K1, 7 = one end of K1 coil, 8 = buzzer.
- Wiring CNA to CNA5 (derived): stepper A to D = P0.4 to P0.7, relay K2 = P0.8, K1 pins = P0.9 and P0.10, buzzer = P0.11. ⚠ The manual does not clearly say which of pins 6 and 7 is run and which is direction. Check DCM.hex source.
- Stepper motor: PM1 (5-pin power mate): 1 +5V, 2 Phase A, 3 Phase B, 4 Phase C, 5 Phase D.
- DC motor: connect to RM5 (2-pin reliamate on the K1 contacts). Direction is controlled in software.
- Relay K2 output: CN12 (2-pin): pin 1 COM, pin 2 NO. An LED toggles with the relay (the manual calls it L12 in one place and LD11 in the test section).

### 3.7 PWM, external interrupt, compare/match, capture

- LD10 brightness shows the PWM duty. TP5 shows pulses and TP6 shows the voltage level. TP4 shows the match output.
- CNB1: pin 1 = PWM output, pin 3 = match output, pin 4 = capture input, plus an external-interrupt line. ⚠ The manual's table lists "2, 5, 6, 8, 9 no connection" and also "9 external interrupt", which conflict.
- Wiring CNB to CNB1: PWM = P1.23 (PWM1.4), match = P1.25 (MAT1.1), capture = P1.26 (CAP0.0). The sample changes MR1 of timer 1, which fits MAT1.1. CNB pin 9 is NC, so the EINT line must come on CNB pins 5 to 8 (EINT0 to EINT3). Check EXINT source.
- JP14 short feeds the match output back as the capture input. Open JP14 to feed an external signal into RM4 pin 1.
- SW2 is the external interrupt switch (edge or low-level sensitive). EXINT test toggles LD10 on each press.

### 3.8 SPI EEPROM, I2C RTC, RS485 (header CNC1)

- U5 = 256 Kbit serial EEPROM (SPI). U6 = MAX485 (RS485). U16 = PCF8563 RTC with a 32.768 kHz crystal and CR2032 backup. LD15 is a general purpose LED in this block.
- CNC1 pins: 1 SCK / TXD1 (U5 or U6), 2 SSEL / RXD1 (U5 or U6), 3 MISO (U5), 4 MOSI (U5), 5 SDA (U16), 6 SCL (U16), 7 NC, 8 RTS1 (U6 direction), 9 interrupt of U16, 10 GND.
- Wiring CNC to CNC1: pin 1 = P0.15, 2 = P0.16, 3 = P0.17, 4 = P0.18, 5 = P0.19 (SDA1), 6 = P0.20 (SCL1), 8 = P0.22, 9 = P2.13 (needs JP4 (2,3)).
- SPI mode: JP12 (2,3) and JP13 (2,3). RS485 mode: JP12 (1,2) and JP13 (1,2).
- RS485: JP11 always short. JP10 short enables the receiver and open disables it. RTS1 enables or disables transmission.
- RS485 external lines at RM3: 1 TX+ (non-inverting), 2 TX- (inverting), 3 GND.
- RTC interrupt: short JP15. I2C RTC test: JP15 (1,2) and JP4 (2,3), keep CN18 free, and set up UART0 for the terminal.
- RS485 test needs two boards. Master runs RS485\_Tx with JP10 open and slave runs RS485\_Rx with JP10 short. JP11, JP12 (1,2) and JP13 (1,2) are set on both. Connect RM3 to RM3 1:1.

### 3.9 I2S demo

- CNA4: 1 RX clock, 2 RX word select, 3 RX SDA, 4 TX clock, 5 TX word select, 6 TX SDA, 7 LED anode (LD16), 10 GND.
- Wiring CNA to CNA4: P0.4 (I2SRX\_CLK), P0.5 (I2SRX\_WS), P0.6 (I2SRX\_SDA), P0.7 (I2STX\_CLK), P0.8 (I2STX\_WS), P0.9 (I2STX\_SDA), P0.10 (LD16).
- At CN17 (7-pin, pin 1 on the CNA4 side) add flying leads 1 to 4, 2 to 5, 3 to 6. LD16 glows on success.

### 3.10 UART0 (flashing and PC serial)

- DB9 female **CN9** via a MAX3232, so the signals on the connector are RS232 levels. Do not connect TTL devices directly.
- CN9 pins: 2 = RXD0 (P0.3, MCU pin 99), 3 = TXD0 (P0.2, MCU pin 98), 5 = GND, 6 = DTR (to RESET, MCU pin 17), 8 = RTS (to P2.10, MCU pin 53), 1/4/7/9 NC.
- Use a serial cross cable. Typical terminal settings: 9600 baud (or what the code uses), 8 data bits, no parity, 1 stop bit, no flow control. USB host test uses 57600.
- SW21 (2-way DIP) must be ON to flash, and OFF when your code uses UART0 (or runs). The manual calls this switch SW1 in one paragraph. It means SW21.

### 3.11 UART3

- RM1 (3-pin reliamate): 1 TXD3, 2 RXD3, 3 GND. Also RS232 level via MAX3232. Short JP7 (1,2) and JP8 (1,2).
- ⚠ The manual does not name the MCU pins. From the jumper text and the LPC1768 alternate functions it is P0.0 (TXD3) and P0.1 (RXD3). These are the same pins as CAN1, so JP7/JP8 choose between them. Confirm against the LPC1768 datasheet.
- Test cabling to a DB9 female: RM1 pin 1 to DB9 pin 3, pin 2 to pin 2, pin 3 to pin 5.

### 3.12 ADC pots

- 12-bit ADC, 0 to 3.3 V in, result 0x000 to 0xFFF.
- **AD0.5 = P1.31**, driven by POT1. **AD0.4 = P1.30**, driven by POT4, and you must short JP18 (2,3).
- P1.30 is also USB VBUS (see conflicts). The Ethernet web page shows both channels. It calls the second pot POT5, which ⚠ is probably POT4.
- P0.23 to P0.26 also carry AD0.0 to AD0.3 on the CND header, but these are not wired to pots on the board.

### 3.13 DAC and CLKOUT

- DAC: AOUT = P0.26 appears at TP8. Open JP5 for this (JP5 short connects P0.26 to the LCD line).
- CLKOUT: P1.27 appears at TP9. Open JP19. Configure the clock output register as: select main oscillator, divider 1, enable.

### 3.14 CAN

- CAN1 = P0.0 (RD1) and P0.1 (TD1) through transceiver U3. CAN2 = P0.4 (RD2) and P0.5 (TD2) through transceiver U4 (both PCA82C250).
- For CAN1 short JP7 (2,3) and JP8 (2,3). JP7 pin 2 = P0.1 (TD1) and JP8 pin 2 = P0.0 (RD1).
- RM2 (6-pin): 1 CANL2, 2 CANH2, 3 GND, 4 GND, 5 CANL1, 6 CANH1.
- CAN test: CNA to CNA1, JP7 (2,3), JP8 (2,3), JP9 short, flying leads RM2 1 to 5 and 2 to 6. CAN1 transmits and CAN2 receives. LD2 to LD9 turn on if the message matches.
- ⚠ The manual does not describe how the CAN2 pins reach U4. It exposes P0.4/P0.5 on CNA, so those lines are shared with the CNA header.

### 3.15 USB (use only one of device, host, OTG at a time)

- Data lines: D+ = P0.29 and D- = P0.30. Other signals on the piggyback: P1.18 (CN2 pin 9, likely the link LED), P2.9 (CN3 pin 16), P1.30 (VBUS).
- **Device (CN15, B type):** pins 1 VBUS, 2 D-, 3 D+, 4 GND. SW20 pins 1 and 2 ON, SW19 OFF, JP18 (1,2), CN18 free. LD14 glows when the host is connected and LD13 toggles during communication.
- USBHID test: CNA to CNA1, CNB to CNB3, JP18 (1,2), JP4 (1,2). It appears as an HID device (use HIDClient.exe). Keys in row 1 map to input bits 0 to 3 and output bits map to LD2 to LD9.
- **Host (CN14, A type):** pins 1 power (via U15), 2 D-, 3 D+, 4 GND. SW19 pins 1 and 2 ON and JP19 short. Use a FAT16 pen drive of 4 GB or less with MSREAD.txt on it. UART0 at 57600 baud for the log. The code copies MSREAD.txt to MSWRITE.txt.
- **OTG (CN18, 8-pin male berg):** 1 3.3V (pin 1 at the D6 diode side), 2 D+, 3 D-, 4 P0.27 (USB\_SDA), 5 P0.28 (USB\_SCL), 6 EXT INT3, 7 RSTOUT, 8 GND. Keep SW19 and SW20 OFF, leave CND and CNC pin 9 unconnected, and short JP4 (2,3). CND pins 5 and 6 are not usable during OTG.

### 3.16 Ethernet

- PHY U14 (DP83848C), 50 MHz crystal X1, RJ45 CN13. Interface is RMII plus MDIO. On the piggyback CN4 the pins are P1.0, P1.1, P1.4, P1.8, P1.9, P1.10, P1.14, P1.15, P1.16, P1.17 (pins 20, 19, 18, 17, 16, 15, 14, 13, 12, 11). (Signal names per NXP UM10360: TXD0, TXD1, TX\_EN, CRS, RXD0, RXD1, RX\_ER, REF\_CLK, MDC, MDIO.)
- LEDs: LD12 is ON when the link is not working or at 10 Mbit/s, OFF at 100 Mbit/s. The left (yellow) RJ45 LED toggles on activity and the right (green) stays on while the cable is connected.
- Test: set MYIP\_1 to MYIP\_4 and SUBMASK\_1 to SUBMASK\_4 in tcpip.h to a free IP and your subnet mask (example in the manual: 90.0.0.70 and 255.255.255.0), rebuild, flash EMAC.hex, short JP18 (2,3), connect a 1:1 LAN cable to a hub. Browse to the IP. The page refreshes about every 5 s.

### 3.17 Reset, ISP, JTAG, trace

- RESET pin is on CN1 pin 17 and RSTOUT on CN1 pin 14. The reset push button is SW1 in the reset section of the manual. DTR from UART0 also drives reset.
- ⚠ The manual calls reset "active high" and then says a low level resets. It is active low on the LPC1768.
- ISP: a LOW on **P2.10** after reset starts the ISP loader (the pin is sampled up to 3 ms after reset). RTS from UART0 controls it. JP3 ties P2.10 to ground for Flash Magic.
- JTAG CN5 (20-pin ARM): 1 and 2 +3.3V, 3 TRST, 5 TDI, 7 TMS, 9 TCK, 11 RTCK, 13 TDO, 15 RESET, evens GND. ⚠ The manual's printed list has TMS on pin 6 and duplicate entries. Use the standard ARM 20-pin layout above. JP2 grounds RTCK through 10k.
- JTAG programming: short JP2, open JP3, SW21 both OFF. ISP programming: open JP2, short JP3, SW21 ON.
- Trace CN7 (20-pin): P2.6 is the trace clock (pin 12), pins 14, 16, 18, 20 are TDATA0 to TDATA3. The manual's printed table is garbled, so confirm before using it.

## 4. GPIO headers CNA, CNB, CNC, CND

Columns: header pin, LPC1768 package pin number, port pin, alternate functions.

**CNA**

| Pin | Pkg pin | Port | Alternate functions |
| --- | --- | --- | --- |
| 1 | 81 | P0.4 | I2SRX\_CLK, RD2, CAP2.0 |
| 2 | 80 | P0.5 | I2SRX\_WS, TD2, CAP2.1 |
| 3 | 79 | P0.6 | I2SRX\_SDA, SSEL1, MAT2.0 |
| 4 | 78 | P0.7 | I2STX\_CLK, SCK1, MAT2.1 |
| 5 | 77 | P0.8 | I2STX\_WS, MISO1, MAT2.2 |
| 6 | 76 | P0.9 | I2STX\_SDA, MOSI1, MAT2.3 |
| 7 | 48 | P0.10 | TXD2, SDA2, MAT3.0 |
| 8 | 49 | P0.11 | RXD2, SCL2, MAT3.1 |
| 9 / 10 |  | NC / GND |  |

**CNB**

| Pin | Pkg pin | Port | Alternate functions |
| --- | --- | --- | --- |
| 1 | 37 | P1.23 | MCI1, PWM1.4, MISO0 |
| 2 | 38 | P1.24 | MCI2, PWM1.5, MOSI0 |
| 3 | 39 | P1.25 | MCOA1, MAT1.1 |
| 4 | 40 | P1.26 | MCOB1, PWM1.6, CAP0.0 |
| 5 | 53 | P2.10 | EINT0, NMI (also ISP pin) |
| 6 | 52 | P2.11 | EINT1, I2STX\_CLK |
| 7 | 51 | P2.12 | EINT2, I2STX\_WS |
| 8 | 50 | P2.13 | EINT3, I2STX\_SDA (needs JP4 (1,2)) |
| 9 / 10 |  | NC / GND |  |

**CNC**

| Pin | Pkg pin | Port | Alternate functions |
| --- | --- | --- | --- |
| 1 | 62 | P0.15 | TXD1, SCK0, SCK |
| 2 | 63 | P0.16 | RXD1, SSEL0, SSEL |
| 3 | 61 | P0.17 | CTS1, MISO0, MISO |
| 4 | 60 | P0.18 | DCD1, MOSI0, MOSI |
| 5 | 59 | P0.19 | DSR1, SDA1 |
| 6 | 58 | P0.20 | DTR1, SCL1 |
| 7 | 57 | P0.21 | RI1, RD1 |
| 8 | 56 | P0.22 | RTS1, TD1 |
| 9 | 50 | P2.13 | I2STX\_SDA (needs JP4 (2,3)) |
| 10 |  | GND |  |

**CND**

| Pin | Pkg pin | Port | Alternate functions |
| --- | --- | --- | --- |
| 1 | 9 | P0.23 | AD0.0, I2SRX\_CLK, CAP3.0 |
| 2 | 8 | P0.24 | AD0.1, I2SRX\_WS, CAP3.1 |
| 3 | 7 | P0.25 | AD0.2, I2SRX\_SDA, TXD3 |
| 4 | 6 | P0.26 | AD0.3, AOUT, RXD3 (needs JP5 short) |
| 5 | 25 | P0.27 | SDA0, USB\_SDA |
| 6 | 24 | P0.28 | SCL0, USB\_SCL |
| 7 | 75 | P2.0 | PWM1.1, TXD1 |
| 8 | 74 | P2.1 | PWM1.2, RXD1 |
| 9 / 10 |  | NC / GND |  |

## 5. Other direct connectors

**CN6 NIFC (26-pin, direct, JP1 gives +5V on pin 25, JP5 short to use pin 4):** 1,2 = P2.0, P2.1; 3,4 = P0.25, P0.26; 5,6 = P0.23, P0.24; 7,8 = P0.10, P0.11; 9,10 = P0.8, P0.9; 11,12 = P0.6, P0.5 (⚠ pin 12 is probably P0.7); 13,14 = P0.4, P0.5; 15,16 = P0.21, P0.22; 17,18 = P0.19, P0.20; 19,20 = P0.17, P0.18; 21,22 = P0.15, P0.16; 23,24 = P2.2, P2.3; 25 = +5V; 26 = GND.

**CN16 spare (9-pin):** 1 P1.20, 2 P1.21, 3 P1.28, 4 P1.29, 5 P3.25, 6 P3.26, 7 P4.28, 8 P4.29, 9 VBAT (RTC battery backup). Pin 1 is on the JP17 side.

## 6. Piggyback connectors CN1 to CN4 (every MCU pin that is brought out)

**CN1:** 1 TDO, 2 TDI, 3 TMS, 4 TRST, 5 TCK, 6 P0.26, 7 P0.25, 8 P0.24, 9 P0.23, 10 and 12 3.3V, 11 and 15 GND, 14 RSTOUT, 16 RTCX1, 17 RESET, 18 RTCX2, 20 P1.31, 21 P1.30, 24 P0.28, 25 P0.27. NC: 13, 19, 22, 23, 26, 27, 28.

**CN2:** 3 P3.26, 4 P3.25, 5 and 19 3.3V, 6 P0.29, 7 P0.30, 8 and 18 GND, 9 P1.18, 10 P1.19, 11 P1.20, 12 P1.21, 13 P1.22, 14 P1.23, 15 P1.24, 16 P1.25, 17 P1.26, 20 P1.27, 21 P1.28, 22 P1.29, 23 P0.0, 24 P0.1, 25 P0.10, 26 P0.11, 27 P2.13. NC: 1, 2, 28.

**CN3:** 3 P2.12, 4 P2.11, 5 P2.10, 6 and 23 3.3V, 7 and 24 GND, 8 P0.22, 9 P0.21, 10 P0.20, 11 "P.19" (P0.19), 12 P0.15 (⚠ duplicate, likely P0.18), 13 P0.17, 14 P0.15, 15 P0.16, 16 P2.9, 17 P2.8, 18 P2.7, 19 P2.6, 20 P2.5, 21 P2.4, 22 P2.3, 25 P2.2, 26 P2.1, 27 P2.0. NC: 1, 2, 28.

**CN4:** 1 P0.9, 2 P0.8, 3 P0.7, 4 P0.6, 5 P0.5, 6 P0.4, 7 P4.28, 8 and 22 GND, 9 and 21 3.3V, 10 P4.29, 11 P1.17, 12 P1.16, 13 P1.15, 14 P1.14, 15 P1.10, 16 P1.9, 17 P1.8, 18 P1.4, 19 P1.1, 20 P1.0, 23 P0.2, 24 P0.3, 25 RTCK. NC: 26, 27, 28.

## 7. Jumpers, switches, pots, test points, LEDs

| Item | Function |
| --- | --- |
| JP1 | +5V to NIFC CN6 pin 25 |
| JP2 | RTCK to GND via 10k. Open for UART flashing, short for JTAG |
| JP3 | P2.10 (ISP) to GND. Short for ISP flashing, open for JTAG |
| JP4 | 1-2 gives CNB pin 8 (P2.13). 2-3 gives CNC pin 9 / OTG / RTC interrupt |
| JP5 | Short: P0.26 to CND pin 4 (LCD D7, GLCD CS1). Open: DAC output to TP8 |
| JP6 | 3.3V to the board. Keep shorted. Remove only to measure voltage or current |
| JP7, JP8 | 1-2 = UART3. 2-3 = CAN1 |
| JP9 | Short for the CAN test |
| JP10 | RS485 receiver: short enables, open disables |
| JP11 | Always short |
| JP12, JP13 | 2-3 = SPI. 1-2 = RS485 |
| JP14 | Short: match feeds capture. Open: external capture via RM4 pin 1 |
| JP15 | RTC clock-out to interrupt |
| JP16 | Short for 16x2 LCD. Open for graphic LCD |
| JP17 | 2-3 for graphic LCD |
| JP18 | 1-2 = USB device. 2-3 = AD0.4 (POT4) and Ethernet test |
| JP19 | Short for USB host power. Open to read CLKOUT at TP9 |
| SW1 | Reset button |
| SW2 | External interrupt button |
| SW3 to SW18 | Keypad |
| SW19 | USB host (pins 1 and 2 ON) |
| SW20 | USB device (pins 1 and 2 ON) |
| SW21 | UART0 DTR/RTS link. ON to flash, OFF to run UART0 code |
| POT1 | AD0.5 (P1.31) |
| POT2 | Graphic LCD contrast |
| POT3 | 16x2 LCD contrast |
| POT4 | AD0.4 (P1.30), needs JP18 (2,3) |
| TP1 / TP2 / TP3 | +5V / 3.3V / GND |
| TP4 / TP5 / TP6 | Match output / PWM pulses / PWM voltage |
| TP8 / TP9 | DAC output / CLKOUT |
| LD2 to LD9 | General purpose LEDs (CNA1) |
| LD10 | PWM LED |
| LD11 (L12 in one place) | Relay LED |
| LD12 | Ethernet speed LED |
| LD13 / LD14 | USB activity / USB connect |
| LD15 | SPI/I2C/RS485 block LED |
| LD16 | I2S LED |

Lab rule: POT1, POT3, POT4 need a screwdriver, turn 180 degrees at most, and use no pressure.

## 8. Power-up and flashing

**Connections (lab sheet):**

1. USB cable from the PC to the long gray RS232 cable (USB-serial adapter).
2. Male end of the RS232 cable into the female DB9 on the left of the kit (**CN9**, UART0).
3. Power supply gray cable into the male DB9 on the right (**CN8**: pins 4 and 5 GND, pin 9 +5V, others NC).
4. Make the FRC connections, then power ON.

**First-time check (manual):** before inserting the piggyback, remove JP6, power on, check TP1 (+5V) and TP2 (3.3V), check nothing runs warm, power off, insert the piggyback, short JP6, power on.

**Flash Magic settings:**

- Device LPC1768, COM port from Device Manager, interface None (ISP), oscillator 12 MHz.
- Erase blocks used by hex file, verify after programming, pick the hex file.
- Options, Advanced Options, Hardware Config: use DTR and RTS to control RST and ISP pin, keep RTS asserted while COM port open, T1 = 50 ms, T2 = 100 ms.
- Baud: the manual says 9600 and 115200 without High Speed Communications. ⚠ The lab troubleshooting sheet says to mark High Speed Communications at 115200. Follow the lab sheet, and try lower baud rates if it fails.
- Before flashing: SW21 ON, JP3 and JP6 shorted. Clear the flash after every download.

**If "Failed to open COMx" or "Failed to autobaud" appears (lab sheet):** check SW21 ON and JP3/JP6 shorted. Power off, switch the USB port, find the new COM number in Device Manager and set it in Flash Magic. Set 115200 with High Speed Communications. Power on and click Start. Otherwise change the USB cable, then the RS232 cable, then the power supply, and only then the kit.

## 9. Keil and code notes

- Keil uVision4. Device NXP LPC1768. Add system\_LPC17xx.c to each project (copy it into the project folder). Include LPC17xx.h. Call SystemInit() and SystemCoreClockUpdate() at the top of main.
- Target options: Xtal 12.0 MHz, IROM1 start 0x0 size 0x8000, IRAM1 start 0x10000000 size 0x8000, create hex file, use memory layout from target dialog.
- Manual's clock setup: PLL0 and PLL1 disabled (PLL0\_SETUP and PLL1\_SETUP set to 0), main oscillator as source, CCLK divider 4 (12 MHz / 4 = 3 MHz), PCLK = CCLK. Add LPC\_SC->CLKSRCSEL = CLKSRCSEL\_Val; after the PCLKSEL lines in SystemInit. Use SystemCoreClock for baud and timer maths if your lab's startup file is different.
- Not from your manual (standard LPC17xx, verify in UM10360): GPIO registers LPC\_GPIOn->FIODIR, FIOSET, FIOCLR, FIOPIN. PINSEL0 = P0.0 to P0.15, PINSEL1 = P0.16 to P0.31, PINSEL2 = P1.0 to P1.15, PINSEL3 = P1.16 to P1.31, PINSEL4 = P2.0 to P2.15, 2 bits per pin (00 = GPIO). Examples: UART0 = PINSEL0 |= (1<<4)|(1<<6). AD0.4 = PINSEL3 |= (3<<28). AD0.5 = PINSEL3 |= (3u<<30). AOUT = PINSEL1 |= (2<<20). SDA0/SCL0 = PINSEL1 |= (1<<22)|(1<<24). CLKOUT = PINSEL3 |= (1<<22).

## 10. Pin conflicts to watch

- **P0.26:** LCD D7 (JP5 short) versus DAC AOUT at TP8 (JP5 open). Also AD0.3 and RXD3.
- **P0.27 and P0.28:** LCD RS and EN versus I2C0 and USB OTG I2C.
- **P1.30:** AD0.4 (JP18 2-3) versus USB VBUS (JP18 1-2).
- **P2.13:** CNB pin 8 (JP4 1-2) versus CNC pin 9 (JP4 2-3), also EINT3, RTC interrupt and OTG.
- **P2.10:** ISP/RTS line and EINT0. Keypad use on CNB pin 5 may disturb flashing.
- **P0.4 and P0.5:** LEDs, 7-seg data, graphic LCD data, I2S receive and CAN2 all share them.
- **P0.15 and P0.16:** SPI (SCK, SSEL) versus UART1/RS485 (JP12, JP13).
- **P0.0 and P0.1:** CAN1 (JP7/JP8 2-3) versus UART3 (JP7/JP8 1-2).
- **P1.27:** CLKOUT at TP9 and CN2 pin 20.
- 16x2 LCD and graphic LCD cannot both be used. USB device, host and OTG cannot be combined.

## 11. Where the manual is inconsistent

- Reset described as active high and then as low-level reset (it is active low).
- Reset/UART handshake switch called SW1 in one place and SW21 elsewhere.
- CN5 JTAG table has duplicate or conflicting pins. CN7 trace table is garbled.
- CN3 pin 12 duplicates P0.15 and CN6 pin 12 duplicates P0.5.
- CNB1 table says pin 9 is both NC and external interrupt.
- CNAD pins 5 and 6 are both labelled "L5".
- Relay LED is L12 in text and LD11 in the test.
- Flash Magic high-speed setting differs between the ALS manual and the lab sheet.
- U5 is called a flash NVROM in one place and an EEPROM in another (the block diagram says 25LC256, which is an EEPROM).
