"""Set the board's net classes - track width, clearance, vias - and assign nets
to them by pattern, in shieldXL-euro.kicad_pro. Plain Python, run with KiCad
closed (it keeps net classes in the project file and would save over this):

    python3 tools/set_netclasses.py

Widths are for 1 oz outer copper and about a 10 C rise. The 5 V input carries
the Pi's 3 A, so it gets 1.5 mm and wants a pour or both layers where it can;
the rails, ground and USB VBUS are sized for their currents, the rest is
signal. USB is full speed (12 Mbit/s) over ribbon, so its pairs are kept
together and short, not impedance-matched.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRO = os.path.join(HERE, "shieldXL-euro.kicad_pro")

# name: (track, clearance, via diameter, via drill, diff-pair width, diff-pair gap), patterns
CLASSES = {
    "Default":    ((0.25, 0.2, 0.6, 0.3, 0.25, 0.2), []),
    "Power_5V":   ((1.5, 0.25, 0.8, 0.4, 0.25, 0.2), ["+5V", "*VBUS_C"]),
    "USB_VBUS":   ((0.8, 0.2, 0.8, 0.4, 0.25, 0.2), ["*VBUS"]),
    "Rails_12V":  ((0.5, 0.25, 0.6, 0.3, 0.25, 0.2), ["*12V*"]),
    "Ground":     ((0.5, 0.2, 0.6, 0.3, 0.25, 0.2), ["GND", "AGND"]),
    "Logic_Supply": ((0.4, 0.2, 0.6, 0.3, 0.25, 0.2), ["+3V3", "*A5V"]),
    "USB_Data":   ((0.3, 0.2, 0.6, 0.3, 0.3, 0.2), ["*_DP", "*_DM"]),
    "Audio":      ((0.3, 0.25, 0.6, 0.3, 0.25, 0.2),
                   ["*_LINE", "*_JACK", "*INL_*", "*INR_*", "*OUTL_*", "*OUTR_*",
                    "*CRW_IN*", "*CRW_OUT*", "*/INA", "*/INB", "*/OUTA", "*/OUTB",
                    # the codec's own analog nodes: its coupling caps and references
                    "Net-(C10-Pad2)", "Net-(C12-Pad2)", "Net-(C14-Pad2)", "Net-(C16-Pad2)",
                    "Net-(U1-FILT+)", "Net-(U1-VQ)"]),
}
TRACK_PRESETS = [0.0, 0.25, 0.3, 0.4, 0.5, 0.8, 1.0, 1.5]
VIA_PRESETS = [(0.0, 0.0), (0.6, 0.3), (0.8, 0.4)]


def main():
    lock = os.path.join(HERE, "~" + os.path.basename(PRO) + ".lck")
    if os.path.exists(lock):
        raise SystemExit("KiCad has the project open (lock file found): close it, then run again")
    d = json.load(open(PRO, encoding="utf-8"))
    ns = d.setdefault("net_settings", {})
    template = next(c for c in ns["classes"] if c["name"] == "Default")
    classes = []
    for prio, (name, ((tw, cl, vd, vdr, dpw, dpg), _)) in enumerate(CLASSES.items()):
        c = dict(template)
        c.update(name=name, track_width=tw, clearance=cl, via_diameter=vd, via_drill=vdr,
                 diff_pair_width=dpw, diff_pair_gap=dpg, diff_pair_via_gap=dpg,
                 priority=2147483647 if name == "Default" else prio)
        classes.append(c)
    ns["classes"] = classes
    ns["netclass_patterns"] = [{"netclass": name, "pattern": p}
                               for name, (_, pats) in CLASSES.items() for p in pats]
    ns["netclass_assignments"] = None
    ds = d["board"]["design_settings"]
    ds["track_widths"] = TRACK_PRESETS
    ds["via_dimensions"] = [{"diameter": a, "drill": b} for a, b in VIA_PRESETS]
    json.dump(d, open(PRO, "w", encoding="utf-8"), indent=2)
    print("net classes:", ", ".join(f"{n} {v[0][0]} mm" for n, v in CLASSES.items()))


if __name__ == "__main__":
    sys.exit(main())
