#!/usr/bin/env python3
"""Write corone.kicad_sch: crow on a daughterboard, for monome's own firmware.

    python3 tools/make_corone.py

Every pin assignment follows what crow's firmware drives (see ../README.md):

  MCU        U8 STM32F722RET6, 8 MHz crystal Y1, SWD on a TC2030 (J2),
             BOOT0 button SW1, reset button SW2, status LED D1 on PA15,
             debug USART3 on J3.
  ADC        U3 ADS131A02 on SPI1, clocked from TIM2 CH4 (PA3), synchronous
             slave (M0 open), 16-bit words (M1 open), no Hamming (M2 low),
             external 2.5 V reference on REFEXT.
  DAC        U4 DAC8565 on SPI2 as I2S, internal 2.5 V reference, resets to
             mid-scale (RSTSEL high) - +2.5 V at the jacks until the firmware
             runs, where reset-to-zero would give +10 V.
  reference  U6D buffers the DAC's reference: REF_2V5, for the ADC, the input
             stages and the calibration mux.
  outputs    U5A-D, Vout = 10 - 6 Vdac: 20k in, 120k feedback, + input at
             10/7 V (REF_2V5 through 30k / 40k), 1k to the header.
  inputs     U6A-B, Vo = 2.5 - (Vin - 2.5) / 3: 100k in, 33.2k feedback, +
             input at REF_2V5; Vo through 1k and a clamp to AIN1N / AIN2N,
             AIN1P / AIN2P at REF_2V5.
  cal mux    U7 ADG1408 on +-12 V: code 0-3 = outputs 4-1 (taken before the
             1k), 4 = REF_2V5, 5-7 = ground, onto IN1_NORM - input 1's
             jack switch, so an unpatched input 1 reads the selected source.
  ii         I2C1 on PB6 / PB7, pull-ups 2.2k switched by driving PB3 / PB4.
  USB        PA11 / PA12 through a USBLC6, VBUS sensed on PA9.
  power      +12 V -> AMS1117-5.0 -> +5V; +5V -> ferrite -> +5VA (ADC, DAC);
             +5V -> AP2112K-3.3 -> +3V3. Op-amps and mux on +-12 V. The rails
             arrive reverse-protected from the main board.

J1, 2 x 10 to the main board: 1 +12V, 2 -12V, 3 / 4 / 8 / 13 / 14 / 18 GND,
5 IN1, 6 IN1_NORM, 7 IN2, 9-12 OUT1-4, 15 USB D+, 16 USB D-, 17 VBUS,
19 ii SCL, 20 ii SDA.
"""

import os
import re
import uuid

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "corone.kicad_sch")
LIB_OUT = os.path.join(HERE, "corone.kicad_sym")
KLIB = os.environ.get("KICAD_SYMBOLS", "/mnt/g/Program Files/KiCad/10.0/share/kicad/symbols")
NS = uuid.UUID("3b0f6c1e-8a2d-4f57-9c3e-0d1a2b3c4d5e")
ROOT_UUID = str(uuid.uuid5(NS, "file"))
PROJECT = "corone"
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
                return s[j:k + 1]


def lib_block(lib, name):
    s = open(os.path.join(KLIB, lib + ".kicad_sym"), encoding="utf-8").read()
    i = s.find(f'\n\t(symbol "{name}"')
    assert i >= 0, (lib, name)
    return balanced(s, i + 1)


def embed(lib, name):
    """A stock symbol embedded as lib:name; a derived symbol is flattened onto
    its parent with its own properties."""
    blk = lib_block(lib, name)
    m = re.search(r'\(extends "([^"]+)"\)', blk)
    if m:
        parent = lib_block(lib, m.group(1))
        for k, v in re.findall(r'\(property "(\w+)" "([^"]*)"', blk):
            parent = re.sub(rf'(\(property "{k}" )"[^"]*"', lambda mm: mm.group(1) + '"' + v.replace("\\", "\\\\") + '"', parent, count=1)
        blk = parent.replace(f'"{m.group(1)}_', f'"{name}_').replace(f'(symbol "{m.group(1)}"', f'(symbol "{name}"', 1)
    return blk.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)


# --- ADS131A02: not in KiCad's library. Pins from TI SBAS590E, "Pin Functions"
ADS_LEFT = [("power_in", "AVDD", "9"), ("power_in", "IOVDD", "15"), ("power_in", "IOVDD", "29"),
            ("input", "AIN1P", "2"), ("input", "AIN1N", "1"), ("input", "AIN2P", "4"), ("input", "AIN2N", "3"),
            ("input", "REFEXT", "14"), ("passive", "REFP", "12"), ("passive", "REFN", "13"),
            ("passive", "VNCP", "11"), ("passive", "CAP", "28"), ("power_in", "AVSS", "10"),
            ("power_in", "GND", "27"), ("no_connect", "NC", "5"), ("no_connect", "NC", "6")]
ADS_RIGHT = [("input", "~{CS}", "23"), ("bidirectional", "SCLK", "22"), ("input", "DIN", "20"),
             ("output", "DOUT", "21"), ("bidirectional", "~{DRDY}", "19"), ("output", "~{DONE}", "18"),
             ("input", "~{RESET}", "17"), ("input", "XTAL1/CLKIN", "25"), ("output", "XTAL2", "26"),
             ("input", "M0", "30"), ("input", "M1", "31"), ("input", "M2", "32"), ("input", "RESV", "16"),
             ("no_connect", "NC", "24"), ("no_connect", "NC", "7"), ("no_connect", "NC", "8")]


def ads131a02(name):
    def font():
        return "(effects (font (size 1.27 1.27)))"

    def pin(kind, pname, num, x, y, a):
        hide = " hide" if kind == "no_connect" else ""
        return (f'\t\t\t(pin {kind} line (at {x:g} {y:g} {a}) (length 5.08){hide}\n'
                f'\t\t\t\t(name "{pname}" {font()})\n\t\t\t\t(number "{num}" {font()})\n\t\t\t)\n')
    top = 19.05
    pins = "".join(pin(k, n, num, -17.78, round(top - 2.54 * i, 2), 0) for i, (k, n, num) in enumerate(ADS_LEFT))
    pins += "".join(pin(k, n, num, 17.78, round(top - 2.54 * i, 2), 180) for i, (k, n, num) in enumerate(ADS_RIGHT))
    return (f'(symbol "{name}"\n\t\t(pin_names (offset 1.016))\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n'
            f'\t\t(property "Reference" "U" (at -12.7 22.86 0) {font()})\n'
            f'\t\t(property "Value" "ADS131A02" (at 12.7 22.86 0) {font()})\n'
            f'\t\t(property "Footprint" "Package_QFP:TQFP-32_7x7mm_P0.8mm" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            f'\t\t(property "Datasheet" "https://www.ti.com/lit/ds/symlink/ads131a02.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            f'\t\t(property "Description" "2-channel 24-bit simultaneous-sampling delta-sigma ADC, TQFP-32" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            f'\t\t(symbol "ADS131A02_0_1"\n\t\t\t(rectangle (start -12.7 21.59) (end 12.7 -21.59)\n'
            '\t\t\t\t(stroke (width 0.254) (type default))\n\t\t\t\t(fill (type background))\n\t\t\t)\n\t\t)\n'
            f'\t\t(symbol "ADS131A02_1_1"\n{pins}\t\t)\n\t)')


def pins_of(block, unit):
    out = {}
    for m in re.finditer(r'\(symbol "[^"]*_(\d+)_(\d+)"', block):
        if int(m.group(1)) not in (0, unit):
            continue
        sub = balanced(block, m.start())
        for x, y, a, num in re.findall(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)[\s\S]*?\(number "([^"]*)"', sub):
            out[num] = (float(x), float(y), int(float(a)))
    return out


def prop(name, value, x, y, hide=False):
    h = "\n\t\t\t(hide yes)" if hide else ""
    return (f'\t\t(property "{name}" "{value}"\n\t\t\t(at {x:g} {y:g} 0){h}\n'
            "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n")


R6 = "Resistor_SMD:R_0603_1608Metric"
C6 = "Capacitor_SMD:C_0603_1608Metric"
C8 = "Capacitor_SMD:C_0805_2012Metric"
OPA = ("Amplifier_Operational", "OPA4197xPW", "OPA4197", "Package_SO:TSSOP-14_4.4x5mm_P0.65mm")
POWER = {"+12V", "-12V", "+5V", "+5VA", "+3V3", "GND"}


def R(ref, value, xy, a, b):
    return (ref, "Device", "R", 1, value, R6, xy, {"1": a, "2": b})


def C(ref, value, xy, a, b, fp=C6):
    return (ref, "Device", "C", 1, value, fp, xy, {"1": a, "2": b})


def amp(ref, unit, xy, conn):
    return (ref, OPA[0], OPA[1], unit, OPA[2], OPA[3], xy, conn)


# ref, lib, symbol, unit, value, footprint, (x, y), {pin: net or None}
PARTS = [
    # --- header to the main board, power --------------------------------------
    ("J1", "Connector_Generic", "Conn_02x10_Odd_Even", 1, "To main board", "Connector_PinSocket_2.54mm:PinSocket_2x10_P2.54mm_Vertical",
     (45.72, 63.5), {"1": "+12V", "2": "-12V", "3": "GND", "4": "GND", "5": "IN1", "6": "IN1_NORM", "7": "IN2",
                     "8": "GND", "9": "OUT1", "10": "OUT2", "11": "OUT3", "12": "OUT4", "13": "GND", "14": "GND",
                     "15": "USB_DP_EXT", "16": "USB_DM_EXT", "17": "VBUS", "18": "GND", "19": "II_SCL", "20": "II_SDA"}),
    C("C1", "10u 25V", (35.56, 109.22), "+12V", "GND", C8),
    C("C2", "10u 25V", (50.8, 109.22), "GND", "-12V", C8),
    ("U1", "Regulator_Linear", "AMS1117-5.0", 1, "AMS1117-5.0", "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
     (106.68, 40.64), {"3": "+12V", "2": "+5V", "1": "GND"}),
    C("C3", "1u 25V", (88.9, 48.26), "+12V", "GND"),
    C("C4", "10u", (124.46, 48.26), "+5V", "GND", C8),
    ("FB1", "Device", "FerriteBead_Small", 1, "600R@100MHz", "Inductor_SMD:L_0603_1608Metric",
     (144.78, 40.64), {"1": "+5V", "2": "+5VA"}),
    C("C5", "10u", (160.02, 48.26), "+5VA", "GND", C8),
    ("U2", "Regulator_Linear", "AP2112K-3.3", 1, "AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5",
     (106.68, 76.2), {"1": "+5V", "3": "+5V", "2": "GND", "4": None, "5": "+3V3"}),
    C("C6", "1u", (88.9, 83.82), "+5V", "GND"),
    C("C7", "10u", (124.46, 83.82), "+3V3", "GND", C8),

    # --- MCU -----------------------------------------------------------------
    ("U8", "MCU_ST_STM32F7", "STM32F722RETx", 1, "STM32F722RET6", "Package_QFP:LQFP-64_10x10mm_P0.5mm",
     (241.3, 101.6), {
        "1": "+3V3", "2": None, "3": None, "4": None, "5": "HSE_IN", "6": "HSE_OUT", "7": "NRST",
        "8": None, "9": None, "10": None, "11": None, "12": "GND", "13": "+3V3",
        "14": None, "15": None, "16": None, "17": "ADC_MCLK", "18": "GND", "19": "+3V3",
        "20": "ADC_CS", "21": "ADC_SCK", "22": "ADC_MISO", "23": "ADC_MOSI", "24": "ADC_NRST",
        "25": None, "26": None, "27": None, "28": None, "29": None, "30": "VCAP", "31": "GND", "32": "+3V3",
        "33": "DAC_SYNC", "34": "DAC_SCLK", "35": "DAC_NRST", "36": "DAC_DIN", "37": None,
        "38": "CAL_A0", "39": "CAL_A2", "40": "CAL_A1", "41": None, "42": "VBUS", "43": None,
        "44": "USB_DM", "45": "USB_DP", "46": "SWDIO", "47": "GND", "48": "+3V3", "49": "SWCLK",
        "50": "LED", "51": "DBG_TX", "52": "DBG_RX", "53": None, "54": None,
        "55": "II_PU_SCL", "56": "II_PU_SDA", "57": None, "58": "II_SCL", "59": "II_SDA",
        "60": "BOOT0", "61": None, "62": "DBG_PIN", "63": "GND", "64": "+3V3"}),
    C("C10", "100n", (195.58, 40.64), "+3V3", "GND"),
    C("C11", "100n", (205.74, 40.64), "+3V3", "GND"),
    C("C12", "100n", (215.9, 40.64), "+3V3", "GND"),
    C("C13", "100n", (226.06, 40.64), "+3V3", "GND"),
    C("C14", "4u7", (236.22, 40.64), "+3V3", "GND", C8),
    C("C15", "1u", (246.38, 40.64), "+3V3", "GND"),       # VDDA
    C("C16", "100n", (256.54, 40.64), "+3V3", "GND"),     # VDDA
    C("C17", "2u2", (266.7, 40.64), "VCAP", "GND"),       # VCAP_1, low ESR
    ("Y1", "Device", "Crystal_GND24", 1, "8MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
     (195.58, 160.02), {"1": "HSE_IN", "3": "HSE_OUT", "2": "GND", "4": "GND"}),
    C("C18", "12p", (185.42, 172.72), "HSE_IN", "GND"),
    C("C19", "12p", (205.74, 172.72), "HSE_OUT", "GND"),
    C("C20", "100n", (220.98, 172.72), "NRST", "GND"),
    ("SW2", "Switch", "SW_Push", 1, "RESET", "Button_Switch_SMD:SW_SPST_TL3342", (236.22, 172.72), {"1": "NRST", "2": "GND"}),
    R("R10", "10k", (254.0, 172.72), "BOOT0", "GND"),
    ("SW1", "Switch", "SW_Push", 1, "BOOT0", "Button_Switch_SMD:SW_SPST_TL3342", (269.24, 172.72), {"1": "+3V3", "2": "BOOT0"}),
    ("J2", "Connector", "Conn_ARM_SWD_TagConnect_TC2030", 1, "SWD", "Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical",
     (297.18, 63.5), {"1": "+3V3", "2": "SWDIO", "3": "NRST", "4": "SWCLK", "5": "GND", "6": None}),
    ("J3", "Connector_Generic", "Conn_01x03", 1, "Debug UART", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
     (297.18, 99.06), {"1": "DBG_TX", "2": "DBG_RX", "3": "GND"}),
    ("TP1", "Connector", "TestPoint", 1, "DBG_PIN", "TestPoint:TestPoint_Pad_D1.0mm", (297.18, 119.38), {"1": "DBG_PIN"}),
    R("R11", "1k", (297.18, 139.7), "LED", "LED_A"),
    ("D1", "Device", "LED", 1, "status", "LED_SMD:LED_0603_1608Metric", (312.42, 139.7), {"2": "LED_A", "1": "GND"}),

    # --- ii, USB ---------------------------------------------------------------
    R("R12", "2.2k", (297.18, 160.02), "II_PU_SCL", "II_SCL"),
    R("R13", "2.2k", (312.42, 160.02), "II_PU_SDA", "II_SDA"),
    ("U9", "Power_Protection", "USBLC6-2P6", 1, "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
     (342.9, 63.5), {"1": "USB_DP_EXT", "6": "USB_DP", "3": "USB_DM_EXT", "4": "USB_DM", "5": "VBUS", "2": "GND"}),

    # --- ADC -------------------------------------------------------------------
    ("U3", "corone", "ADS131A02", 1, "ADS131A02IPBS", "Package_QFP:TQFP-32_7x7mm_P0.8mm",
     (78.74, 205.74), {
        "9": "+5VA", "15": "+3V3", "29": "+3V3", "2": "REF_2V5", "1": "ADC_IN1", "4": "REF_2V5", "3": "ADC_IN2",
        "14": "REF_2V5", "12": "ADC_REFP", "13": "GND", "11": "GND", "28": "ADC_CAP", "10": "GND", "27": "GND",
        "5": None, "6": None, "7": None, "8": None, "24": None,
        "23": "ADC_CS", "22": "ADC_SCK", "20": "ADC_MOSI", "21": "ADC_MISO", "19": None, "18": None,
        "17": "ADC_NRST", "25": "ADC_MCLK", "26": None, "30": None, "31": None, "32": "GND", "16": "+3V3"}),
    C("C30", "1u", (30.48, 248.92), "+5VA", "GND"),
    C("C31", "100n", (40.64, 248.92), "+5VA", "GND"),
    C("C32", "1u", (50.8, 248.92), "+3V3", "GND"),
    C("C33", "1u", (60.96, 248.92), "+3V3", "GND"),
    C("C34", "1u", (71.12, 248.92), "ADC_CAP", "GND"),
    C("C35", "1u", (81.28, 248.92), "ADC_REFP", "GND"),     # REFP to REFN (= AVSS = GND)
    C("C36", "100n", (91.44, 248.92), "REF_2V5", "GND"),
    R("R30", "100k", (124.46, 248.92), "+3V3", "ADC_MISO"),  # DOUT pull-up, per datasheet

    # --- DAC and the reference buffer ---------------------------------------------
    ("U4", "Analog_DAC", "DAC8565", 1, "DAC8565IAPW", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
     (190.5, 223.52), {
        "1": "DAC_A", "2": "DAC_B", "7": "DAC_C", "8": "DAC_D", "3": "DAC_REF", "4": "+5VA", "5": "GND", "6": "GND",
        "9": "DAC_SYNC", "10": "DAC_SCLK", "11": "DAC_DIN", "12": "+3V3", "13": "DAC_NRST", "14": "+3V3",
        "15": "GND", "16": "GND"}),
    C("C40", "1u", (160.02, 254.0), "+5VA", "GND"),
    C("C41", "100n", (170.18, 254.0), "+5VA", "GND"),
    C("C42", "100n", (180.34, 254.0), "+3V3", "GND"),
    C("C43", "150n", (190.5, 254.0), "DAC_REF", "GND"),
    amp("U6", 4, (241.3, 205.74), {"12": "DAC_REF", "13": "REF_2V5", "14": "REF_2V5"}),

    # --- outputs: Vout = 10 - 6 Vdac ---------------------------------------------
    R("R40", "30k", (241.3, 236.22), "REF_2V5", "OUT_OFS"),
    R("R41", "40k", (256.54, 236.22), "OUT_OFS", "GND"),
    C("C44", "100n", (271.78, 236.22), "OUT_OFS", "GND"),
] + [
    p for k, (dac, unit, pins) in enumerate((("DAC_A", 1, ("3", "2", "1")), ("DAC_B", 2, ("5", "6", "7")),
                                             ("DAC_C", 3, ("10", "9", "8")), ("DAC_D", 4, ("12", "13", "14"))))
    for p in (
        R(f"R{50 + 4 * k}", "20k", (304.8, 205.74 + 30.48 * k), dac, f"OSUM{k + 1}"),
        R(f"R{51 + 4 * k}", "120k", (325.12, 195.58 + 30.48 * k), f"OSUM{k + 1}", f"OAMP{k + 1}"),
        C(f"C{50 + k}", "100p", (340.36, 195.58 + 30.48 * k), f"OSUM{k + 1}", f"OAMP{k + 1}"),
        amp("U5", unit, (325.12, 210.82 + 30.48 * k), {pins[0]: "OUT_OFS", pins[1]: f"OSUM{k + 1}", pins[2]: f"OAMP{k + 1}"}),
        R(f"R{52 + 4 * k}", "1k", (355.6, 210.82 + 30.48 * k), f"OAMP{k + 1}", f"OUT{k + 1}"),
    )
] + [
    amp("U5", 5, (378.46, 205.74), {"4": "+12V", "11": "-12V"}),
    amp("U6", 5, (378.46, 236.22), {"4": "+12V", "11": "-12V"}),
    C("C60", "100n", (393.7, 200.66), "+12V", "GND"),
    C("C61", "100n", (393.7, 210.82), "GND", "-12V"),
    C("C62", "100n", (393.7, 231.14), "+12V", "GND"),
    C("C63", "100n", (393.7, 241.3), "GND", "-12V"),
] + [
    # --- inputs: Vo = 2.5 - (Vin - 2.5) / 3, into AINxN ------------------------------
    p for k, (unit, pins) in enumerate(((1, ("3", "2", "1")), (2, ("5", "6", "7"))))
    for p in (
        R(f"R{70 + 5 * k}", "100k", (30.48, 289.56 + 35.56 * k), f"IN{k + 1}", f"ISUM{k + 1}"),
        R(f"R{71 + 5 * k}", "33.2k", (55.88, 279.4 + 35.56 * k), f"ISUM{k + 1}", f"IAMP{k + 1}"),
        C(f"C{70 + 2 * k}", "1n", (71.12, 279.4 + 35.56 * k), f"ISUM{k + 1}", f"IAMP{k + 1}"),
        amp("U6", unit, (55.88, 294.64 + 35.56 * k), {pins[0]: "REF_2V5", pins[1]: f"ISUM{k + 1}", pins[2]: f"IAMP{k + 1}"}),
        R(f"R{72 + 5 * k}", "1k", (86.36, 294.64 + 35.56 * k), f"IAMP{k + 1}", f"ADC_IN{k + 1}"),
        ("D%d" % (10 + k), "Diode", "BAT54S", 1, "BAT54S", "Package_TO_SOT_SMD:SOT-23",
         (104.14, 294.64 + 35.56 * k), {"1": "GND", "2": "+5VA", "3": f"ADC_IN{k + 1}"}),
        C(f"C{71 + 2 * k}", "1n", (119.38, 294.64 + 35.56 * k), f"ADC_IN{k + 1}", "GND"),
    )
] + [
    amp("U6", 3, (55.88, 365.76), {"10": "GND", "9": "U6C_OUT", "8": "U6C_OUT"}),   # spare: follower to ground

    # --- calibration mux: input 1's normal ---------------------------------------
    ("U7", "Analog_Switch", "ADG1408YRUZ", 1, "ADG1408YRUZ", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
     (190.5, 317.5), {
        "13": "+12V", "3": "-12V", "14": "GND", "2": "+3V3", "1": "CAL_A0", "16": "CAL_A1", "15": "CAL_A2",
        "4": "OAMP4", "5": "OAMP3", "6": "OAMP2", "7": "OAMP1", "12": "REF_2V5", "11": "GND", "10": "GND", "9": "GND",
        "8": "IN1_NORM"}),
    C("C80", "100n", (220.98, 307.34), "+12V", "GND"),
    C("C81", "100n", (220.98, 327.66), "GND", "-12V"),
]
# U9 is drawn with USBLC6-2P6, the symbol the -2SC6 derives from (same pins),
# and J2 with the TC2030 symbol, given the no-legs footprint: embedding the
# derived symbols flattened trips KiCad's library-mismatch check.
# The GND flag also meets U7's grounded spare inputs, which KiCad calls
# bidirectional: three "bidirectional and power output" warnings, expected.
FLAGS = ["+12V", "-12V", "GND", "+5VA"]


def build():
    blocks = {}
    for _, lib, sym, *_ in PARTS:
        key = f"{lib}:{sym}"
        if key not in blocks:
            blocks[key] = ads131a02(key) if lib == "corone" else embed(lib, sym)
    for p in sorted(POWER) + ["PWR_FLAG"]:
        blocks[f"power:{p}"] = embed("power", p)

    o = ["(kicad_sch", "\t(version 20231120)", '\t(generator "make_corone.py")',
         '\t(generator_version "8.0")', f'\t(uuid "{ROOT_UUID}")', '\t(paper "A2")',
         "\t(title_block", '\t\t(title "Corone - crow daughterboard")',
         '\t\t(comment 1 "Generated by tools/make_corone.py - do not edit by hand")',
         '\t\t(comment 2 "Pin map and scaling from monome/crow firmware; see README.md")', "\t)",
         "\t(lib_symbols"]
    for b in blocks.values():
        o.append("\t\t" + b.replace("\n\t", "\n\t\t"))
    o.append("\t)")

    def instance(lib_id, ref, value, fp, x, y, unit, pinnums, hide_ref=False):
        lines = [f"\t(symbol\n\t\t(lib_id \"{lib_id}\")\n\t\t(at {x:g} {y:g} 0)\n\t\t(unit {unit})\n"
                 "\t\t(exclude_from_sim no)\n"
                 f"\t\t(in_bom {'no' if ref.startswith(('#', 'TP')) else 'yes'})\n\t\t(on_board yes)\n\t\t(dnp no)\n"
                 f'\t\t(uuid "{uid()}")\n',
                 prop("Reference", ref, x + 2.54, y - 7.62, hide_ref),
                 prop("Value", value, x + 2.54, y + 7.62, hide_ref and ref.startswith("#FLG")),
                 prop("Footprint", fp, x, y, True),
                 prop("Datasheet", "", x, y, True)]
        for n in pinnums:
            lines.append(f'\t\t(pin "{n}"\n\t\t\t(uuid "{uid()}")\n\t\t)\n')
        lines.append(f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{ROOT_UUID}"\n'
                     f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit {unit})\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')
        return "".join(lines)

    npwr = [0]

    def power(net, x, y):
        npwr[0] += 1
        lib_id = f"power:{net}"
        (px, py, _), = pins_of(blocks[lib_id], 1).values()
        return instance(lib_id, f"#PWR{npwr[0]:03d}", net, "", round(x - px, 3), round(y + py, 3), 1, ["1"], hide_ref=True)

    # a label reads away from its symbol: a pin drawn rightward from its end
    # (angle 0) is on the symbol's left, so its label runs left, and so on
    AWAY = {0: (180, "right"), 180: (0, "left"), 90: (270, "right"), 270: (90, "left")}

    def label(net, x, y, pin_angle=180):
        a, just = AWAY[pin_angle]
        return (f'\t(label "{net}"\n\t\t(at {x:g} {y:g} {a})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n'
                f'\t\t\t)\n\t\t\t(justify {just} bottom)\n\t\t)\n\t\t(uuid "{uid()}")\n\t)')

    nets = {}
    for ref, lib, sym, unit, value, fp, (x, y), conn in PARTS:
        pp = pins_of(blocks[f"{lib}:{sym}"], unit)
        missing = set(pp) - set(conn)
        assert not missing, (ref, unit, sorted(missing))
        o.append(instance(f"{lib}:{sym}", ref, value, fp, x, y, unit, list(pp)))
        done = set()
        for num, net in conn.items():
            px, py, pa = pp[num]
            ax, ay = round(x + px, 2), round(y - py, 2)
            key = (ax, ay, net)
            nets.setdefault(net, []).append(f"{ref}.{num}")
            if key in done:          # stacked pins share one point
                continue
            done.add(key)
            if net is None:
                o.append(f'\t(no_connect\n\t\t(at {ax:g} {ay:g})\n\t\t(uuid "{uid()}")\n\t)')
            elif net in POWER:
                o.append(power(net, ax, ay))
            else:
                o.append(label(net, ax, ay, pa))
    for i, net in enumerate(FLAGS):
        x, y = 25.4 + 15.24 * i, 20.32
        o.append(label(net, x, y) if net not in POWER else power(net, x, y))
        o.append(instance("power:PWR_FLAG", f"#FLG{i + 1:02d}", "PWR_FLAG", "", x, y, 1, ["1"], hide_ref=True))
    o.append('\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)')
    o.append(")")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(o) + "\n")
    with open(LIB_OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write('(kicad_symbol_lib\n\t(version 20231120)\n\t(generator "make_corone.py")\n\t'
                + ads131a02("ADS131A02") + "\n)\n")
    return nets


if __name__ == "__main__":
    nets = build()
    print(f"wrote {OUT}")
    lonely = [n for n, m in nets.items() if n is not None and n not in POWER and len(m) < 2 and n not in FLAGS]
    for net, members in sorted(nets.items(), key=lambda kv: str(kv[0])):
        if net is not None:
            print(f"  {net:12} {' '.join(members)}")
    if lonely:
        raise SystemExit(f"nets with one pin: {lonely}")
