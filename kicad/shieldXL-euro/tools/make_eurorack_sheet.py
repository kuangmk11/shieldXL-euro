#!/usr/bin/env python3
"""Write eurorack.kicad_sch: the I/O that makes shieldXL a Eurorack module,
and hook it into the root sheet.

    python3 tools/make_eurorack_sheet.py

What it adds (references in the 100s, clear of shieldXL's):

  Eurorack power    J101 10-pin header; D101 / D102 reverse protection into
                    +12V / -12V; 10u + 100n on each rail. Feeds the op-amps
                    only - the Pi does not run from the rack.
  audio in  (x2)    J102 / J103 3.5 mm, T -> 69.8k / 30.1k divider (100k in,
                    x0.301) -> follower, out to IN_L_LINE / IN_R_LINE, which
                    feed shieldXL's own 4.99k / 10k dividers into the codec.
                    Non-inverting, so audio keeps its polarity through the
                    module; 13.4 Vpp reaches the codec's 2.7 Vpp full scale.
                    100p across the 30.1k: about 76 kHz. Switch contact to
                    AGND: unpatched reads zero.
  audio out (x2)    OUT_L_LINE / OUT_R_LINE (codec, after shieldXL's filter)
                    -> non-inverting stage, gain 3.49 (24.9k / 10k) -> 1k ->
                    J104 / J105. Codec full scale, about 2.85 Vpp, leaves as
                    about 10 Vpp.
  MIDI              J106 in (PJ366ST) to MIDI_IN_TIP / _RING; J107 out, its
                    tip and ring chosen by JP101 / JP102 from MIDI_OUT_SNK /
                    _SRC - Type A as made (1-2 bridged), Type B by cutting
                    1-2 on both and bridging 2-3. Replaces shieldXL's slide
                    switch.
  Pi power          J108 USB-C (JAE DX07S024WJ1R350, vertical, 12 mm), power only (5.1k on CC1 / CC2), F101 polyfuse
                    and D103 TVS onto +5V, which reaches the Pi through the
                    header as shieldXL's +5V does. Bulk C113.
  USB host (x3)     J109-J111 vertical USB-A on the panel. The Pi's four
                    ports come down from two USB adapters (../usb-adapter),
                    one per stack, on 2 x 5 IDC ribbons to J112 / J113. At
                    each panel socket: a USBLC6-2SC6 on D+ / D- (U102-U104)
                    and 47u + 100n on its VBUS (C114-C119). The ribbons:
                    J112 the stack beside Ethernet, port A (nearer the Pi's
                    PCB) to USB 1, B to USB 2; J113 the outer stack, A to
                    USB 3, B to Corone.
  Corone (crow)     J115-J120, the six jacks in the panel's CORONE outline:
                    I/1 (its switch contact carried as CRW_IN1_NORM, which
                    crow's calibration mux drives), I/2, O/1-O/4. J121, the
                    2 x 10 header the Corone daughterboard plugs onto (pinout
                    in ../corone/README.md); J122 ii (GND, SCL, SDA) at the
                    back edge. Corone's USB comes from J113's port B.

  MIDI out buffer   U105 74LVC1G125 between the Pi's TXD (MIDI_TX) and shieldXL's
                    MIDI out resistor and TX LED (MIDI_TX_BUF): a plug going
                    in shorts tip and ring to the sleeve, and that current
                    is the buffer's to take, not the Pi's.
  display           C121 / C122, 10u + 100n on +3V3 at the display's FPC
                    connector, for the OLED's boost converter.
  grounds           JP103, open, across shieldXL's AGND-GND ferrite L3: bridge
                    it if Corone's USB (returning through L3) misbehaves.

Every pin gets a label or power symbol at its end. Nets that cross to the
shield sheets are global labels; +5V, GND and AGND use the shield sheets'
own power symbols, copied in, so they are the same nets.
"""

import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "eurorack.kicad_sch")
ROOT_FILE = os.path.join(HERE, "shieldXL-euro.kicad_sch")
SHEET1 = os.path.join(HERE, "norns-shield-210330_1.kicad_sch")
KLIB = os.environ.get("KICAD_SYMBOLS", "/mnt/g/Program Files/KiCad/10.0/share/kicad/symbols")
NS = uuid.UUID("7c1e4b2a-3d5f-4a6b-8c7d-9e0f1a2b3c40")
SHEET_UUID = str(uuid.uuid5(NS, "eurorack-sheet"))
PROJECT = "shieldXL-euro"
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


def shield_power(name):
    """One of the shield sheets' own (Eagle-import) power symbols, verbatim."""
    s = open(SHEET1, encoding="utf-8").read()
    i = s.index(f'(symbol "norns-shield-210330-eagle-import:{name}"')
    return balanced(s, i)


def pins_of(block, unit):
    out = {}
    for m in re.finditer(r'\(symbol "[^"]*_(\d+)_(\d+)"', block):
        if int(m.group(1)) not in (0, unit):
            continue
        sub = balanced(block, m.start())
        for x, y, num in re.findall(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) [-\d.]+\)[\s\S]*?\(number "([^"]*)"', sub):
            out[num] = (float(x), float(y))
    return out


def prop(name, value, x, y, hide=False):
    h = "\n\t\t\t(hide yes)" if hide else ""
    return (f'\t\t(property "{name}" "{value}"\n\t\t\t(at {x:g} {y:g} 0){h}\n'
            "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n")


FP_R = "Resistor_SMD:R_0805_2012Metric"
FP_C = "Capacitor_SMD:C_0805_2012Metric"
FP_JACK = "MMM:Jack_3.5mm_QingPu_WQP-PJ398SM_Vertical_CircularHoles"
FP_TRS = "MMM:Jack_3.5mm_QingPu_WQP-PJ366ST_Vertical"
FP_JP = "Jumper:SolderJumper-3_P1.3mm_Bridged12_Pad1.0x1.5mm"
GLOBAL = {"IN_L_LINE", "IN_R_LINE", "OUT_L_LINE", "OUT_R_LINE",
          "MIDI_OUT_SRC", "MIDI_OUT_SNK", "MIDI_IN_TIP", "MIDI_IN_RING", "MIDI_TX", "MIDI_TX_BUF"}
POWER = {"+5V": "shield", "+3V3": "shield", "GND": "shield", "AGND": "shield", "+12V": "power", "-12V": "power"}

# ref, lib, symbol, unit, value, footprint, (x, y), {pin: net or None}
PARTS = [
    # --- Eurorack power: op-amps only ------------------------------------------
    ("J101", "Connector_Generic", "Conn_02x05_Odd_Even", 1, "Eurorack power", "Connector_IDC:IDC-Header_2x05_P2.54mm_Vertical",
     (38.1, 50.8), {"1": "-12V_IN", "2": "-12V_IN", "3": "AGND", "4": "AGND", "5": "AGND", "6": "AGND",
                    "7": "AGND", "8": "AGND", "9": "+12V_IN", "10": "+12V_IN"}),
    ("D101", "Device", "D_Schottky", 1, "B5819W", "Diode_SMD:D_SOD-123", (76.2, 40.64), {"2": "+12V_IN", "1": "+12V"}),
    ("D102", "Device", "D_Schottky", 1, "B5819W", "Diode_SMD:D_SOD-123", (76.2, 60.96), {"2": "-12V", "1": "-12V_IN"}),
    ("C101", "Device", "C", 1, "10u 25V", FP_C, (101.6, 40.64), {"1": "+12V", "2": "AGND"}),
    ("C102", "Device", "C", 1, "10u 25V", FP_C, (101.6, 60.96), {"1": "AGND", "2": "-12V"}),
    ("C103", "Device", "C", 1, "100n", FP_C, (114.3, 40.64), {"1": "+12V", "2": "AGND"}),
    ("C104", "Device", "C", 1, "100n", FP_C, (114.3, 60.96), {"1": "AGND", "2": "-12V"}),
    ("U101", "Amplifier_Operational", "TL074", 5, "TL074", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
     (139.7, 50.8), {"4": "+12V", "11": "-12V"}),
    # --- audio in: 69.8k / 30.1k divider into a follower, x0.301 ---------------
    ("J102", "Connector_Audio", "AudioJack2_SwitchT", 1, "IN L", FP_JACK, (38.1, 101.6), {"T": "IN_L_JACK", "TN": "AGND", "S": "AGND"}),
    ("R101", "Device", "R", 1, "69.8k", FP_R, (63.5, 101.6), {"1": "IN_L_JACK", "2": "INL_DIV"}),
    ("R102", "Device", "R", 1, "30.1k", FP_R, (76.2, 116.84), {"1": "INL_DIV", "2": "AGND"}),
    ("C105", "Device", "C", 1, "100p", FP_C, (66.04, 116.84), {"1": "INL_DIV", "2": "AGND"}),
    ("U101", "Amplifier_Operational", "TL074", 1, "TL074", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
     (88.9, 106.68), {"3": "INL_DIV", "2": "IN_L_LINE", "1": "IN_L_LINE"}),
    ("J103", "Connector_Audio", "AudioJack2_SwitchT", 1, "IN R", FP_JACK, (38.1, 132.08), {"T": "IN_R_JACK", "TN": "AGND", "S": "AGND"}),
    ("R103", "Device", "R", 1, "69.8k", FP_R, (63.5, 132.08), {"1": "IN_R_JACK", "2": "INR_DIV"}),
    ("R104", "Device", "R", 1, "30.1k", FP_R, (76.2, 147.32), {"1": "INR_DIV", "2": "AGND"}),
    ("C106", "Device", "C", 1, "100p", FP_C, (66.04, 147.32), {"1": "INR_DIV", "2": "AGND"}),
    ("U101", "Amplifier_Operational", "TL074", 2, "TL074", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
     (88.9, 137.16), {"5": "INR_DIV", "6": "IN_R_LINE", "7": "IN_R_LINE"}),
    # --- audio out: non-inverting, gain 3.49, 1k out ---------------------------
    ("U101", "Amplifier_Operational", "TL074", 3, "TL074", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
     (165.1, 106.68), {"10": "OUT_L_LINE", "9": "OUTL_FB", "8": "OUTL_AMP"}),
    ("R105", "Device", "R", 1, "10k", FP_R, (152.4, 119.38), {"1": "OUTL_FB", "2": "AGND"}),
    ("R106", "Device", "R", 1, "24.9k", FP_R, (165.1, 93.98), {"1": "OUTL_FB", "2": "OUTL_AMP"}),
    ("C107", "Device", "C", 1, "100p", FP_C, (177.8, 93.98), {"1": "OUTL_FB", "2": "OUTL_AMP"}),
    ("R107", "Device", "R", 1, "1k", FP_R, (190.5, 106.68), {"1": "OUTL_AMP", "2": "OUT_L_JACK"}),
    ("J104", "Connector_Audio", "AudioJack2_SwitchT", 1, "OUT L", FP_JACK, (215.9, 106.68), {"T": "OUT_L_JACK", "TN": None, "S": "AGND"}),
    ("U101", "Amplifier_Operational", "TL074", 4, "TL074", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
     (165.1, 137.16), {"12": "OUT_R_LINE", "13": "OUTR_FB", "14": "OUTR_AMP"}),
    ("R108", "Device", "R", 1, "10k", FP_R, (152.4, 149.86), {"1": "OUTR_FB", "2": "AGND"}),
    ("R109", "Device", "R", 1, "24.9k", FP_R, (165.1, 124.46), {"1": "OUTR_FB", "2": "OUTR_AMP"}),
    ("C108", "Device", "C", 1, "100p", FP_C, (177.8, 124.46), {"1": "OUTR_FB", "2": "OUTR_AMP"}),
    ("R110", "Device", "R", 1, "1k", FP_R, (190.5, 137.16), {"1": "OUTR_AMP", "2": "OUT_R_JACK"}),
    ("J105", "Connector_Audio", "AudioJack2_SwitchT", 1, "OUT R", FP_JACK, (215.9, 137.16), {"T": "OUT_R_JACK", "TN": None, "S": "AGND"}),
    # --- MIDI -----------------------------------------------------------------
    ("J106", "Connector_Audio", "AudioJack3", 1, "MIDI IN", FP_TRS, (241.3, 50.8), {"T": "MIDI_IN_TIP", "R": "MIDI_IN_RING", "S": None}),
    ("JP101", "Jumper", "SolderJumper_3_Bridged12", 1, "TIP A/B", FP_JP, (279.4, 43.18), {"1": "MIDI_OUT_SNK", "2": "MIDI_OUT_T", "3": "MIDI_OUT_SRC"}),
    ("JP102", "Jumper", "SolderJumper_3_Bridged12", 1, "RING A/B", FP_JP, (279.4, 66.04), {"1": "MIDI_OUT_SRC", "2": "MIDI_OUT_R", "3": "MIDI_OUT_SNK"}),
    ("J107", "Connector_Audio", "AudioJack3", 1, "MIDI OUT", FP_TRS, (304.8, 53.34), {"T": "MIDI_OUT_T", "R": "MIDI_OUT_R", "S": "GND"}),
    # --- Pi power: USB-C on the panel ------------------------------------------
    # JAE DX07S024WJ1R350, vertical, 12.0 mm tall so its face reaches the
    # panel's front and a plug seats through the panel (the 9.05 mm Molex
    # 204711 left a plug about 2.5 mm short). Every VBUS and GND contact
    # carries current; USB 2.0, SBU and the SuperSpeed pairs are left open
    ("J108", "Connector", "USB_C_Receptacle", 1, "DX07S024WJ1R350", "Connector_USB:USB_C_Receptacle_JAE_DX07S024WJ1R350",
     (241.3, 116.84), {**{p: "VBUS_C" for p in ("A4", "A9", "B4", "B9")},
                       **{p: "GND" for p in ("A1", "A12", "B1", "B12", "SH")},
                       "A5": "CC1", "B5": "CC2",
                       **{p: None for p in ("A2", "A3", "A6", "A7", "A8", "A10", "A11",
                                            "B2", "B3", "B6", "B7", "B8", "B10", "B11")}}),
    ("R111", "Device", "R", 1, "5.1k", FP_R, (271.78, 129.54), {"1": "CC1", "2": "GND"}),
    ("R112", "Device", "R", 1, "5.1k", FP_R, (284.48, 129.54), {"1": "CC2", "2": "GND"}),
    ("F101", "Device", "Polyfuse", 1, "3A hold", "Fuse:Fuse_1812_4532Metric", (271.78, 104.14), {"1": "VBUS_C", "2": "+5V"}),
    ("D103", "Device", "D_TVS", 1, "SMBJ5.0CA", "Diode_SMD:D_SMB", (292.1, 99.06), {"1": "+5V", "2": "GND"}),
    ("C113", "Device", "C", 1, "47u", "Capacitor_SMD:C_1206_3216Metric", (304.8, 104.14), {"1": "+5V", "2": "GND"}),
    # --- Corone: crow's jacks and the daughterboard's header -------------------
    ("J115", "Connector_Audio", "AudioJack2_SwitchT", 1, "CORONE I/1", FP_JACK, (38.1, 226.06),
     {"T": "CRW_IN1", "TN": "CRW_IN1_NORM", "S": "AGND"}),
    ("J116", "Connector_Audio", "AudioJack2_SwitchT", 1, "CORONE I/2", FP_JACK, (76.2, 226.06),
     {"T": "CRW_IN2", "TN": "AGND", "S": "AGND"}),
] + [
    (f"J{116 + n}", "Connector_Audio", "AudioJack2_SwitchT", 1, f"CORONE O/{n}", FP_JACK, (76.2 + 38.1 * n, 226.06),
     {"T": f"CRW_OUT{n}", "TN": None, "S": "AGND"}) for n in (1, 2, 3, 4)
] + [
    ("J121", "Connector_Generic", "Conn_02x10_Odd_Even", 1, "Corone", "Connector_PinHeader_2.54mm:PinHeader_2x10_P2.54mm_Vertical",
     (304.8, 226.06), {"1": "+12V", "2": "-12V", "3": "AGND", "4": "AGND", "5": "CRW_IN1", "6": "CRW_IN1_NORM",
                       "7": "CRW_IN2", "8": "AGND", "9": "CRW_OUT1", "10": "CRW_OUT2", "11": "CRW_OUT3",
                       "12": "CRW_OUT4", "13": "AGND", "14": "AGND", "15": "CRW_USB_DP", "16": "CRW_USB_DM",
                       "17": "AGND", "18": "CRW_USB_VBUS", "19": "II_SCL", "20": "II_SDA"}),
    ("J122", "Connector_Generic", "Conn_01x03", 1, "ii", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
     (355.6, 215.9), {"1": "AGND", "2": "II_SCL", "3": "II_SDA"}),
] + [
    # --- USB host: three panel sockets ------------------------------------------
    (f"J{108 + n}", "Connector", "USB_A", 1, f"USB {n}", "Connector_USB:USB_A_Molex_105057_Vertical",
     (50.8 + 76.2 * (n - 1), 182.88), {"1": f"USB{n}_VBUS", "2": f"USB{n}_DM", "3": f"USB{n}_DP", "4": "GND", "SH": "GND"})
    for n in (1, 2, 3)
] + [
    (f"U{101 + n}", "Power_Protection", "USBLC6-2P6", 1, "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
     (50.8 + 76.2 * (n - 1), 203.2), {"1": f"USB{n}_DP", "6": f"USB{n}_DP", "3": f"USB{n}_DM", "4": f"USB{n}_DM",
                                      "5": f"USB{n}_VBUS", "2": "GND"})
    for n in (1, 2, 3)
] + [
    (f"C{113 + n}", "Device", "C", 1, "47u 10V", "Capacitor_SMD:C_1206_3216Metric",
     (25.4 + 76.2 * (n - 1), 203.2), {"1": f"USB{n}_VBUS", "2": "GND"})
    for n in (1, 2, 3)
] + [
    (f"C{116 + n}", "Device", "C", 1, "100n", FP_C,
     (35.56 + 76.2 * (n - 1), 203.2), {"1": f"USB{n}_VBUS", "2": "GND"})
    for n in (1, 2, 3)
] + [
    # --- MIDI out buffer, display decoupling, ground link -------------------------
    ("U105", "74xGxx", "74LVC1G125", 1, "74LVC1G125", "Package_TO_SOT_SMD:SOT-23-5",
     (342.9, 50.8), {"1": "GND", "2": "MIDI_TX", "4": "MIDI_TX_BUF", "3": "GND", "5": "+3V3"}),
    ("C120", "Device", "C", 1, "100n", FP_C, (342.9, 71.12), {"1": "+3V3", "2": "GND"}),
    ("C121", "Device", "C", 1, "10u", FP_C, (342.9, 101.6), {"1": "+3V3", "2": "GND"}),
    ("C122", "Device", "C", 1, "100n", FP_C, (355.6, 101.6), {"1": "+3V3", "2": "GND"}),
    ("JP103", "Jumper", "SolderJumper_2_Open", 1, "AGND-GND", "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
     (342.9, 132.08), {"1": "AGND", "2": "GND"}),
] + [
    # --- the Pi's ports, from the two USB adapters (pinout: ../usb-adapter) --------
    (ref, "Connector_Generic", "Conn_02x05_Odd_Even", 1, value, "Connector_IDC:IDC-Header_2x05_P2.54mm_Vertical", xy,
     {"1": f"{a}_VBUS", "2": "GND", "3": f"{a}_DM", "4": f"{a}_DP", "5": "GND",
      "6": "GND", "7": f"{b}_DM", "8": f"{b}_DP", "9": "GND", "10": f"{b}_VBUS"})
    for ref, value, xy, a, b in (("J112", "Pi USB, inner stack", (88.9, 248.92), "USB1", "USB2"),
                                 ("J113", "Pi USB, outer stack", (165.1, 248.92), "USB3", "CRW_USB"))
]
# Nets this sheet brings onto the board, driven from off it or through a diode
# or fuse. +5V, GND and AGND are not flagged: the shield sheets' Eagle-era
# parts call those pins bidirectional, and a flag there only trades the
# original's "not driven" for a pin-to-pin clash.
FLAGS = ["+12V", "-12V", "VBUS_C", "USB1_VBUS", "USB2_VBUS", "USB3_VBUS", "CRW_USB_VBUS"]


def build():
    blocks = {}
    for _, lib, sym, *_ in PARTS:
        blocks[f"{lib}:{sym}"] = embed(lib, sym)
    for p in ("+12V", "-12V", "PWR_FLAG"):
        blocks[f"power:{p}"] = embed("power", p)
    for p in ("+5V", "+3V3", "GND", "AGND"):
        blocks[f"norns-shield-210330-eagle-import:{p}"] = shield_power(p)

    o = ["(kicad_sch", "\t(version 20231120)", '\t(generator "make_eurorack_sheet.py")',
         '\t(generator_version "8.0")', f'\t(uuid "{str(uuid.uuid5(NS, "file"))}")', '\t(paper "A3")',
         "\t(title_block", '\t\t(title "Eurorack I/O")', '\t\t(comment 1 "Generated by tools/make_eurorack_sheet.py")', "\t)",
         "\t(lib_symbols"]
    for b in blocks.values():
        o.append("\t\t" + b.replace("\n\t", "\n\t\t"))
    o.append("\t)")

    def instance(lib_id, ref, value, fp, x, y, unit, pinnums, hide_ref=False):
        lines = [f"\t(symbol\n\t\t(lib_id \"{lib_id}\")\n\t\t(at {x:g} {y:g} 0)\n\t\t(unit {unit})\n"
                 "\t\t(exclude_from_sim no)\n"
                 f"\t\t(in_bom {'no' if ref.startswith(('JP', '#')) else 'yes'})\n\t\t(on_board yes)\n\t\t(dnp no)\n"
                 f'\t\t(uuid "{uid()}")\n',
                 prop("Reference", ref, x + 2.54, y - 7.62, hide_ref),
                 prop("Value", value, x + 2.54, y + 7.62, hide_ref and ref.startswith("#FLG")),
                 prop("Footprint", fp, x, y, True),
                 prop("Datasheet", "", x, y, True)]
        for n in pinnums:
            lines.append(f'\t\t(pin "{n}"\n\t\t\t(uuid "{uid()}")\n\t\t)\n')
        lines.append(f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{root_uuid}/{SHEET_UUID}"\n'
                     f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit {unit})\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')
        return "".join(lines)

    npwr = [0]

    def power(net, x, y):
        npwr[0] += 1
        lib_id = f"{'norns-shield-210330-eagle-import' if POWER[net] == 'shield' else 'power'}:{net}"
        (px, py), = pins_of(blocks[lib_id], 1).values()
        return instance(lib_id, f"#PWR{100 + npwr[0]}", net, "", round(x - px, 3), round(y + py, 3), 1, ["1"], hide_ref=True)

    def label(net, x, y):
        kind = "global_label" if net in GLOBAL else "label"
        extra = ('\t\t(shape bidirectional)\n' if kind == "global_label" else "")
        prop_isr = ('\t\t(property "Intersheetrefs" "${INTERSHEET_REFS}"\n\t\t\t(at %g %g 0)\n\t\t\t(effects\n'
                    '\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n' % (x, y)
                    if kind == "global_label" else "")
        return (f'\t({kind} "{net}"\n{extra}\t\t(at {x:g} {y:g} 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n'
                f'\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{uid()}")\n{prop_isr}\t)')

    nets = {}
    for ref, lib, sym, unit, value, fp, (x, y), conn in PARTS:
        pp = pins_of(blocks[f"{lib}:{sym}"], unit)
        o.append(instance(f"{lib}:{sym}", ref, value, fp, x, y, unit, list(pp)))
        done = set()
        for num, net in conn.items():
            px, py = pp[num]
            ax, ay = round(x + px, 2), round(y - py, 2)
            key = (ax, ay, net)
            nets.setdefault(net, []).append(f"{ref}.{num}")
            if key in done:          # stacked pins (USB-C VBUS / GND) share one point
                continue
            done.add(key)
            if net is None:
                o.append(f'\t(no_connect\n\t\t(at {ax:g} {ay:g})\n\t\t(uuid "{uid()}")\n\t)')
            elif net in POWER:
                o.append(power(net, ax, ay))
            else:
                o.append(label(net, ax, ay))
    for i, net in enumerate(FLAGS):
        x, y = 25.4 + 15.24 * i, 20.32
        o.append(label(net, x, y) if net not in POWER else power(net, x, y))
        o.append(instance("power:PWR_FLAG", f"#FLG{101 + i}", "PWR_FLAG", "", x, y, 1, ["1"], hide_ref=True))
    o.append(")")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(o) + "\n")
    return nets


def hook_root():
    """Add the sheet to the root schematic, once."""
    s = open(ROOT_FILE, encoding="utf-8").read()
    if "eurorack.kicad_sch" in s:
        return False
    block = f'''	(sheet
		(at 127 25.4)
		(size 48.895 40.64)
		(fields_autoplaced yes)
		(stroke
			(width 0)
			(type solid)
		)
		(fill
			(color 0 0 0 0.0000)
		)
		(uuid "{SHEET_UUID}")
		(property "Sheetname" "eurorack"
			(at 127 24.6884 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left bottom)
			)
		)
		(property "Sheetfile" "eurorack.kicad_sch"
			(at 127 66.6246 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left top)
			)
		)
		(instances
			(project "{PROJECT}"
				(path "/{root_uuid}"
					(page "3")
				)
			)
		)
	)
'''
    i = s.index("\t(sheet_instances")
    s = s[:i] + block + s[i:]
    with open(ROOT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    return True


root_uuid = re.search(r'\(uuid "([^"]+)"\)', open(ROOT_FILE, encoding="utf-8").read()).group(1)

if __name__ == "__main__":
    nets = build()
    print(f"wrote {OUT}")
    print("root sheet:", "hooked in" if hook_root() else "already has it")
    for net, members in sorted(nets.items(), key=lambda kv: str(kv[0])):
        print(f"  {str(net):13} {' '.join(members)}")
