# Corone

crow on a daughterboard for Moirae (shieldXL-euro). It runs monome's own
[crow firmware](https://github.com/monome/crow) unmodified, so the hardware
follows what that firmware drives. crow's hardware is closed: everything
below is read from the firmware source (`ll/`, `usbd/`, `Makefile`) or
worked out from it. Each item says which.

Corone plugs into the main board on one 2 x 10 header. The jacks are on the
main board, under the panel's CORONE outline; Corone carries the processor,
converters, analog stages and power.

## What the firmware fixes (read from source)

| | firmware | pins |
|---|---|---|
| MCU | STM32F722 (`-DSTM32F722xx`), 8 MHz HSE (`HSE_VALUE`), PLL to 216 MHz | |
| ADC | TI ADS131A0x, 2 channels enabled (`ADS_ADC_ENA 0x03`), 16-bit words, SPI1, MCLK from TIM2 CH4 | PA3 MCLK, PA4 NSS, PA5 SCK, PA6 MISO, PA7 MOSI, PC4 nRESET |
| DAC | TI DAC8565, quad 16-bit, on SPI2 run as I2S (24-bit frames, 48 kHz x 4 channels) | PB12 SYNC (I2S WS), PB13 SCLK, PB15 DIN, PB14 nRESET; I2S MCK out on PC6, unused |
| calibration mux | 3 select lines, 6 sources for input 1: outputs 4, 3, 2, 1, a 2.5 V reference, ground (codes 0-5). Ground at start-up | PC7 (A0), PC9 (A1), PC8 (A2) |
| ii | I2C1 | PB6 SCL, PB7 SDA |
| ii pull-ups | driven high from GPIO to switch them on, high-Z for off | PB3 (SCL pull-up), PB4 (SDA pull-up) |
| USB | OTG FS device, CDC serial, VBUS sensing on | PA11 D-, PA12 D+, PA9 VBUS |
| status LED | | PA15 |
| debug | USART3 | PC10 TX, PC11 RX; debug pin PB9 |

All of these fit the 64-pin STM32F722RET6 (LQFP-64), which is the part to use.

## Scaling (worked out from the firmware's conversions)

**Outputs.** `dac8565.c` writes `code = (2/3)·65535 − V·65535/15`. With the
DAC8565's internal 2.5 V reference, `Vdac = 5/3 − V/6`, so the output stage
must be

    Vout = 10 − 6·Vdac        (code 0 → +10 V, code 65535 → −5 V)

An inverting stage: Rin 20k, Rf 120k (gain −6), the + input at 10/7 V from
the 2.5 V reference through 30k / 40k (2.5 · 40/70 = 1.4286 V). Then 1k to
the jack. Precision quad op-amp on ±12 V (OPA4171 class).

**Inputs.** `ads131.c` reads `V = code·15/65535 + 2.5`, signed codes: full
scale ±32767 spans −5 V to +10 V around +2.5 V, and the comment confirms −5 V
reaches 0x8000. So the converter must see

    AINP − AINN = (Vin − 2.5) / 3      (±2.5 V full scale)

The firmware leaves A_SYS_CFG at reset, which selects an external reference:
REFP = 2.5 V (the DAC8565's reference output, buffered), REFN = GND. ADC on a
unipolar 5 V AVDD. One inverting stage per input, + input at 2.5 V, Rin 100k,
Rf 33.2k: its output `Vo = 2.5 − (Vin − 2.5)/3`, 0-5 V over −5…+10 V, goes to
AINN; AINP sits at the buffered 2.5 V. The inversion is undone by the choice
of pins, so the firmware's default scale (1.0) is right in sign. Series 1k
and clamps to AVDD / GND protect the converter when a jack is overdriven.
The exact gain is left to calibration.

**Calibration.** `calibrate.lua`: "cal.source(n) - set input[1] source to
output n", also `'gnd'` and `'2v5'`. Input 1's jack is normalled to the mux:
unpatched, it reads the selected source (ground, by default). So:

- The IN 1 jack's switch contact comes to Corone as its own header pin.
- The mux is an 8:1 on ±12 V with 3.3 V logic (ADG1208 / DG408 class).
- Sources 0-3 tap each output op-amp's output, before the 1k; source 4 is
  the 2.5 V reference; source 5 is ground; 6 and 7 are unused.
- Calibrating needs IN 1 unpatched, as on crow.

## Power

crow runs from the rack only ("60mA @ +12v, -15mA @ -12V, no 5V"); so does
Corone. +12 V → 5 V LDO (ADC AVDD, DAC) → 3.3 V LDO (MCU, ADC IOVDD). The
op-amps and mux on ±12 V. VBUS from the Pi is sensed, not used for power.

## Header to the main board (2 x 10, 2.54 mm)

| pin | signal | pin | signal |
|---|---|---|---|
| 1 | +12 V | 2 | −12 V |
| 3 | GND | 4 | GND |
| 5 | IN 1 tip | 6 | IN 1 normal (to the cal mux) |
| 7 | IN 2 tip | 8 | GND |
| 9 | OUT 1 | 10 | OUT 2 |
| 11 | OUT 3 | 12 | OUT 4 |
| 13 | GND | 14 | GND |
| 15 | USB D+ | 16 | USB D− |
| 17 | VBUS (sense) | 18 | GND |
| 19 | ii SCL | 20 | ii SDA |

The main board takes ii to a 3-pin header at its back edge, as crow has, and
USB from the Pi's fourth port, through J113 (see ../usb-adapter).

## Programming

- SWD pads (SWDIO, SWCLK, NRST, 3V3, GND) for the first flash.
- BOOT0 to a pad / button: the STM32 ROM DFU loader, for recovery.
- After that, crow's own bootloader (`submodules/dfu-stm32f7`) and its usual
  update path over USB.

## Placement

On the back of the main board, lower half, below the Pi (User.4 on the main
board marks about 60 x 45 mm of room). Stands about as tall as its header.

## Files

    corone.kicad_sch      the schematic - generated, do not edit by hand
    corone.kicad_sym      the ADS131A02 symbol (not in KiCad's library), from TI SBAS590E
    tools/make_corone.py  writes both; the part list and every pin's net are in it

`python3 tools/make_corone.py` rewrites them. ERC (`kicad-cli sch erc`): three
warnings, no errors - the GND power flag meets the mux's grounded spare
inputs, which KiCad types as bidirectional.

## Choices the firmware doesn't settle

- **ADC mode.** M0 open (synchronous slave): the firmware never reads DRDY
  and notes that pulling NSS low resyncs the filter. M1 open (16-bit words,
  as its comment says), M2 low (no Hamming code).
- **DAC reset.** RSTSEL high: the DAC8565 resets to mid-scale, so the jacks
  sit at +2.5 V until the firmware runs. Reset to zero would put +10 V on
  every output.
- **ii.** Pull-ups 2.2k from PB3 / PB4. The main board's ii header (J122)
  reads GND, SCL, SDA, the common order. There is no standard: monome's i2c
  guide says the order may be reversed between modules and to connect by
  name, finding GND by its marking - so J122's silkscreen should name all
  three pins and mark GND.
- **Power.** AMS1117-5.0 from +12 V carries the whole digital load (about
  0.5 W at 70 mA); give its tab copper.
- **VBUS.** Straight to PA9, as the firmware senses it there. With the rack
  off and the Pi on, 5 V sits on an unpowered pin; real crow on a norns
  sees the same.

## Open

- The input clamp, filter and exact resistor values: values above are the
  ideal; pick E96 and let calibration take up the rest.
- Output series resistor: 1k assumed.
- The ADS131A02 package (TQFP-32) and its CLK1/CLK2 settings match the
  firmware's 630 µs block; confirm the MCLK frequency from TIM2's period.
