#!/usr/bin/env python3
"""Swap shieldXL's CS4270 (U1, sheet 1) for a TI PCM3060, in place. Run once,
with the project closed:

    python3 tools/swap_codec_pcm3060.py

The CS4270 is end of life (Cirrus EOL-000081, last buy Dec 2023). The
PCM3060 is a current part with single-ended ADC inputs, DAC outputs that run
single-ended (register 64 S/E, the Linux driver's ti,out-single-ended), I2C
control and a mainline driver (ti,pcm3060).

U1 keeps its place, its uuid (so Update PCB swaps the footprint in place) and
every wire: the new symbol puts its pins where the CS4270's were.

  CS4270 pin   wire/net           PCM3060 pin
  1  SDIN      SDIN               12 DIN
  2  LRCK      LRCK               4 LRCK1 + 11 LRCK2 (stacked: ADC and DAC run together)
  3  MCLK      MCLK, 12.288 MHz   6 SCKI1 + 9 SCKI2 (256 fs at 48 kHz)
  4  SCLK      SCLK               5 BCK1 + 10 BCK2
  5  VD        +3V3               7 VDD
  6  DGND      GND                8 DGND
  7  SDOUT     SDOUT              3 DOUT
  8  VLC       +3V3               - (wire removed)
  9  CDOUT     SDA                2 MD/SDA
  10 CCLK      SCL                1 MC/SCL
  11 CS        GND                28 MODE: tied to DGND = I2C control
  12 CDIN      GND                27 MS/ADR: low = I2C address 0x46
  13 AD2       GND                - (wire and its ground symbol removed)
  14 RST       R-CODEC (GPIO17)   15 RST, active low; the overlay drives it high
  15 AINA      INB (left in)      25 VINL
  16 AINB      INA (right in)     26 VINR
  17 VQ        C4 / C5            21 VCOM (0.1u + 10u, as the datasheet asks)
  18 FILT+     C6 / C7            - (wire removed; C6 / C7 off the board)
  19 VA        A5V, 4.75 V        24 VCC
  20 AGND      AGND               23 AGND1 + 22 AGND2 + 16 SGND
  21 MUTEA     -                  14 ZEROL (no connect)
  22 AOUTA     OUTB (left out)    20 VOUTL+
  23 AOUTB     OUTA (right out)   18 VOUTR+
  24 MUTEB     -                  13 ZEROR (no connect)
  -                               19 VOUTL-, 17 VOUTR-: open in single-ended mode (no connect)

Levels at VCC = 4.75 V: ADC full scale 0.6 VCC = 2.85 Vpp into 10 kohm;
DAC 0.8 VCC = 3.8 Vpp single-ended. The input dividers (R7-R10) are re-set
here for the 10 kohm input; the output gain is in make_eurorack_sheet.py.
"""

import os
import re
import uuid

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET = os.path.join(HERE, "norns-shield-210330_1.kicad_sch")
LIB_ID = "Moirae:PCM3060"
FP = "Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm"
X0, Y0 = 236.22, 104.14     # U1's origin on the sheet
NS = uuid.UUID("3f6b1c2d-8e4a-4b5c-9d6e-7f8091a2b3c4")

# number, name, x, y (symbol units, y up), angle, electrical type, hidden (stacked twin).
# Stacked twins are passive: a hidden power pin would name a global net of its own.
PINS = [
    (12, "DIN", -22.86, 12.7, 0, "input", False),
    (4, "LRCK1", -22.86, 10.16, 0, "bidirectional", False),
    (11, "LRCK2", -22.86, 10.16, 0, "bidirectional", True),
    (6, "SCKI1", -22.86, 7.62, 0, "input", False),
    (9, "SCKI2", -22.86, 7.62, 0, "input", True),
    (5, "BCK1", -22.86, 5.08, 0, "bidirectional", False),
    (10, "BCK2", -22.86, 5.08, 0, "bidirectional", True),
    (7, "VDD", -22.86, 2.54, 0, "power_in", False),
    (8, "DGND", -22.86, 0, 0, "power_in", False),
    (3, "DOUT", -22.86, -2.54, 0, "output", False),
    (2, "MD/SDA", -22.86, -7.62, 0, "bidirectional", False),
    (1, "MC/SCL", -22.86, -10.16, 0, "input", False),
    (28, "MODE", -22.86, -12.7, 0, "input", False),
    (27, "MS/ADR", -22.86, -15.24, 0, "input", False),
    (15, "~{RST}", 22.86, -12.7, 180, "input", False),
    (25, "VINL", 22.86, -10.16, 180, "input", False),
    (26, "VINR", 22.86, -7.62, 180, "input", False),
    (21, "VCOM", 22.86, -5.08, 180, "passive", False),
    (24, "VCC", 22.86, 0, 180, "passive", False)   # A5V's regulator pin is not a typed power output,
    (23, "AGND1", 22.86, 2.54, 180, "power_in", False),
    (22, "AGND2", 22.86, 2.54, 180, "passive", True),
    (16, "SGND", 22.86, 2.54, 180, "passive", True),
    (14, "ZEROL", 22.86, 5.08, 180, "output", False),
    (20, "VOUTL+", 22.86, 7.62, 180, "output", False),
    (18, "VOUTR+", 22.86, 10.16, 180, "output", False),
    (13, "ZEROR", 22.86, 12.7, 180, "output", False),
    (19, "VOUTL-", 12.7, 22.86, 270, "output", False),
    (17, "VOUTR-", 15.24, 22.86, 270, "output", False),
]
NC = [(22.86, 5.08), (22.86, 12.7), (12.7, 22.86), (15.24, 22.86)]
DROP_WIRES = [((213.36, 109.22), (182.88, 109.22)), ((182.88, 109.22), (182.88, 101.6)),   # VLC
              ((259.08, 121.92), (259.08, 119.38)),                                      # AD2
              ((259.08, 106.68), (279.4, 106.68)), ((279.4, 106.68), (279.4, 119.38))]   # FILT+
DROP_SYMBOL_AT = (259.08, 124.46)    # AD2's ground symbol
OFF_BOARD = ("C6", "C7")            # FILT+ caps
VALUES = {"R7": "1.27k", "R9": "1.27k", "R8": "4.53k", "R10": "4.53k"}

_n = [0]


def uid():
    _n[0] += 1
    return str(uuid.uuid5(NS, str(_n[0])))


def balanced(s, j):
    d = 0
    for k in range(j, len(s)):
        if s[k] == "(":
            d += 1
        elif s[k] == ")":
            d -= 1
            if d == 0:
                return k + 1


def lib_symbol():
    pins = []
    for num, name, x, y, a, et, hidden in PINS:
        h = "\n\t\t\t\t\t(hide yes)" if hidden else ""
        pins.append(f'''				(pin {et} line
					(at {x:g} {y:g} {a})
					(length 5.08){h}
					(name "{name}"
						(effects
							(font
								(size 1.27 1.27)
							)
						)
					)
					(number "{num}"
						(effects
							(font
								(size 1.27 1.27)
							)
						)
					)
				)''')
    return f'''		(symbol "{LIB_ID}"
			(exclude_from_sim no)
			(in_bom yes)
			(on_board yes)
			(property "Reference" "U"
				(at -17.78 20.32 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(justify left bottom)
				)
			)
			(property "Value" "PCM3060"
				(at 2.54 -20.32 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(justify left bottom)
				)
			)
			(property "Footprint" "{FP}"
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(property "Datasheet" "https://www.ti.com/lit/ds/symlink/pcm3060.pdf"
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(property "Description" "24-bit 96/192 kHz stereo codec, single-ended ADC in, single-ended or differential DAC out, I2C/SPI, TSSOP-28"
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(symbol "PCM3060_0_1"
				(rectangle
					(start -17.78 17.78)
					(end 17.78 -17.78)
					(stroke
						(width 0.254)
						(type default)
					)
					(fill
						(type background)
					)
				)
			)
			(symbol "PCM3060_1_1"
{chr(10).join(pins)}
			)
			(embedded_fonts no)
		)'''


def main():
    s = open(SHEET, encoding="utf-8").read()
    assert LIB_ID not in s, "already swapped"
    # the library symbol
    i = s.index("\t(lib_symbols\n") + len("\t(lib_symbols\n")
    s = s[:i] + lib_symbol() + "\n" + s[i:]

    # U1's instance
    m = re.search(r'\(property "Reference" "U1"', s)
    a = s.rfind("\n\t(symbol\n", 0, m.start()) + 1
    b = balanced(s, a + 1)
    blk = s[a:b]
    blk = blk.replace('(lib_id "norns-shield-210330-eagle-import:CS4270")', f'(lib_id "{LIB_ID}")', 1)
    blk = re.sub(r'(\(property "Value" )"CS4270"', r'\1"PCM3060PW"', blk, count=1)
    blk = re.sub(r'(\(property "Footprint" )"[^"]*"', rf'\1"{FP}"', blk, count=1)
    blk = re.sub(r'(\(property "Datasheet" )""', r'\1"https://www.ti.com/lit/ds/symlink/pcm3060.pdf"', blk, count=1)
    # the per-pin uuid list: drop the CS4270's, write the PCM3060's
    blk = re.sub(r'\n\t\t\(pin "[^"]*"\n\t\t\t\(uuid "[^"]*"\)\n\t\t\)', "", blk)
    pins = "".join(f'\n\t\t(pin "{n}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for n, *_ in PINS)
    j = blk.index("\n\t\t(instances")
    blk = blk[:j] + pins + blk[j:]
    s = s[:a] + blk + s[b:]

    # wires the PCM3060 has no pin for
    for (x1, y1), (x2, y2) in DROP_WIRES:
        pat = (rf'\n\t\(wire\n\t\t\(pts\n\t\t\t\(xy (?:{x1:g} {y1:g}\) \(xy {x2:g} {y2:g}|{x2:g} {y2:g}\) \(xy {x1:g} {y1:g})\)'
               rf'\n\t\t\)[\s\S]*?\n\t\)')
        s, n = re.subn(pat, "", s, count=1)
        assert n == 1, ((x1, y1), (x2, y2))
    # AD2's ground symbol
    x, y = DROP_SYMBOL_AT
    m = re.search(rf'\n\t\(symbol\n\t\t\(lib_id "[^"]*:GND"\)\n\t\t\(at {x:g} {y:g} ', s)
    a = m.start() + 1
    s = s[:a] + s[balanced(s, a + 1):].lstrip("\n")
    # FILT+ caps off the board and out of the BOM
    for ref in OFF_BOARD:
        m = re.search(rf'\(property "Reference" "{ref}"', s)
        a = s.rfind("\n\t(symbol\n", 0, m.start()) + 1
        b = balanced(s, a + 1)
        blk = s[a:b].replace("(in_bom yes)", "(in_bom no)", 1).replace("(on_board yes)", "(on_board no)", 1).replace("(dnp no)", "(dnp yes)", 1)
        s = s[:a] + blk + s[b:]
    # input dividers for the PCM3060's 10 kohm input
    for ref, val in VALUES.items():
        m = re.search(rf'\(property "Reference" "{ref}"', s)
        a = s.rfind("\n\t(symbol\n", 0, m.start()) + 1
        b = balanced(s, a + 1)
        blk = re.sub(r'(\(property "Value" )"[^"]*"', rf'\1"{val}"', s[a:b], count=1)
        s = s[:a] + blk + s[b:]
    # no-connect flags on the open pins
    ncs = "".join(f'\t(no_connect\n\t\t(at {X0 + x:g} {Y0 - y:g})\n\t\t(uuid "{uid()}")\n\t)\n' for x, y in NC)
    i = s.index("\t(wire\n")
    s = s[:i] + ncs + s[i:]
    open(SHEET, "w", encoding="utf-8", newline="\n").write(s)
    print("U1 is a PCM3060PW; C6/C7 off the board; R7/R9 1.27k, R8/R10 4.53k")


if __name__ == "__main__":
    main()
