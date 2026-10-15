#!/usr/bin/env python3
"""Remove shieldXL's desktop I/O from the two shield sheets, leaving a
global label wherever a signal used to reach it.

    python3 tools/strip_shield_io.py

  sheet 1  J1, J2 (6.35 mm outputs), J4, J5 (6.35 mm inputs)
  sheet 2  J3 (MIDI out jack), S1 (Type A/B slide switch), J6 (MIDI in jack)

The 3.5 mm jacks, the A/B jumpers and the level stages that replace them are
on eurorack.kicad_sch, joined by these global labels:

  IN_L_LINE   codec left input divider (R9, was J4 tip)
  IN_R_LINE   codec right input divider (R7, was J5 tip)
  OUT_L_LINE  codec left output filter (R14 / C17, was J1 tip)
  OUT_R_LINE  codec right output filter (R12 / C15, was J2 tip)
  MIDI_OUT_SRC  +3V3 through R18 (was S1 1 / 4)
  MIDI_OUT_SNK  TX through R17 (was S1 3 / 6)
  MIDI_IN_TIP   opto, R16 / U2 K2 (was J6 tip)
  MIDI_IN_RING  opto, R6 / U2 K1 (was J6 ring)

Parts are found by library and position, not reference: sheet 2 still
carries Eagle-era references on its symbols. Every pin point is checked
against a wire end before anything is removed. Wires left hanging by a
removed part are pruned, chain by chain, and so are junctions left on
nothing. Idempotent: a second run finds nothing to remove.
"""

import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schlib as S  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = uuid.UUID("5f3d2a10-1c2b-4e5f-8a9b-0c1d2e3f4a50")

# sheet -> [(lib_id, x, y, {pin: label or None})]; None = pin is pruned
PLAN = {
    "norns-shield-210330_1.kicad_sch": [
        ("Connector_Audio:NRJ6HF", 276.86, 194.31, {"T": "OUT_L_LINE"}),
        ("Connector_Audio:NRJ6HF", 276.86, 215.9, {"T": "OUT_R_LINE"}),
        ("Connector_Audio:NRJ6HF", 82.55, 209.55, {"T": "IN_L_LINE"}),
        ("Connector_Audio:NRJ6HF", 82.55, 233.68, {"T": "IN_R_LINE"}),
    ],
    "norns-shield-210330_2.kicad_sch": [
        ("Hachi-Ni_v26-eagle-import:EG1390B", 212.09, 78.74,
         {"1": "MIDI_OUT_SRC", "4": "MIDI_OUT_SRC", "3": "MIDI_OUT_SNK", "6": "MIDI_OUT_SNK"}),
        ("Hachi-Ni_v26-eagle-import:PJ-320B", 181.61, 63.5, {}),
        ("Hachi-Ni_v26-eagle-import:PJ-320B", 250.19, 33.02, {"2": "MIDI_IN_TIP", "3": "MIDI_IN_RING"}),
    ],
}


def wires(s):
    out = []
    for a, b, t in S.blocks(s, "wire"):
        pts = [(round(float(x), 3), round(float(y), 3)) for x, y in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', t)]
        out.append((a, b, pts))
    return out


def on_segment(p, a, b):
    (x, y), (x0, y0), (x1, y1) = p, a, b
    if abs((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)) > 1e-3:
        return False
    return min(x0, x1) - 1e-3 <= x <= max(x0, x1) + 1e-3 and min(y0, y1) - 1e-3 <= y <= max(y0, y1) + 1e-3


def label_xml(name, x, y, angle, n):
    just = "right" if angle in (180, 270) else "left"
    return (f'\t(global_label "{name}"\n\t\t(shape bidirectional)\n\t\t(at {x:g} {y:g} {angle})\n'
            f'\t\t(fields_autoplaced yes)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            f'\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{uuid.uuid5(NS, f"{name}{x}{y}{n}")}")\n'
            f'\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"\n\t\t\t(at {x:g} {y:g} 0)\n'
            f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n\t)\n')


def strip(path, plan):
    s = open(path, encoding="utf-8").read()
    insts = S.instances(s)
    ends = S.wire_ends(s)
    removed_pts, labels, cut = set(), [], []
    for lib_id, x, y, pinlabels in plan:
        hit = [i for i in insts if i["lib_id"] == lib_id and abs(i["x"] - x) < 0.01 and abs(i["y"] - y) < 0.01]
        if not hit:
            print(f"  {lib_id} at {x}, {y}: not found (already removed?)")
            continue
        inst = hit[0]
        pts = S.pin_points(s, inst)
        for pin, name in pinlabels.items():
            assert pts[pin] in ends, f"{inst['ref']} pin {pin} at {pts[pin]} is on no wire"
            labels.append((name, *pts[pin]))
        removed_pts |= {p for pin, p in pts.items() if pin not in pinlabels}
        cut.append(inst["span"])
        print(f"  removed {inst['ref']} ({lib_id.split(':')[1]}) at {x}, {y}")
    # every pin point that stays on the sheet
    keep_pins = set()
    for i in insts:
        if i["span"] in cut:
            continue
        try:
            keep_pins |= set(S.pin_points(s, i).values())
        except ValueError:
            pass
    anchors = keep_pins | {(round(x, 3), round(y, 3)) for _, x, y in labels}
    for head in ("label", "global_label", "hierarchical_label", "no_connect"):
        for _, _, t in S.blocks(s, head):
            m = re.search(r'\(at ([-\d.]+) ([-\d.]+)', t)
            anchors.add((round(float(m.group(1)), 3), round(float(m.group(2)), 3)))
    # prune: a wire with an end attached to nothing goes, starting from the
    # removed pins and following the chain
    ws = wires(s)
    dead = set()
    frontier = set(removed_pts)
    while frontier:
        nxt = set()
        for k, (a, b, pts) in enumerate(ws):
            if k in dead or not (set(pts) & frontier):
                continue
            for p in pts:
                if p in anchors:
                    continue
                others = [q for j, (_, _, qs) in enumerate(ws) if j != k and j not in dead
                          for q in [qs] if p in qs or on_segment(p, qs[0], qs[-1])]
                if not others:
                    dead.add(k)
                    nxt |= set(pts) - {p}
                    break
        frontier = nxt
    cut += [(ws[k][0], ws[k][1]) for k in dead]
    # junctions left touching fewer than three things
    live_w = [pts for k, (_, _, pts) in enumerate(ws) if k not in dead]
    for a, b, t in S.blocks(s, "junction"):
        m = re.search(r'\(at ([-\d.]+) ([-\d.]+)', t)
        p = (round(float(m.group(1)), 3), round(float(m.group(2)), 3))
        n = sum(1 for pts in live_w for q in pts if q == p) + sum(
            1 for pts in live_w if p not in pts and on_segment(p, pts[0], pts[-1])) * 2 + (p in keep_pins)
        if n < 3:
            cut.append((a, b))
    for a, b in sorted(set(cut), reverse=True):
        s = s[:a] + s[b:]
    # labels point away from the wire they sit on
    add = []
    for n, (name, x, y) in enumerate(labels):
        ang = 0
        for pts in live_w:
            if (x, y) in (pts[0], pts[-1]):
                q = pts[-1] if pts[0] == (x, y) else pts[0]
                ang = 180 if q[0] > x else 0 if q[0] < x else 90 if q[1] > y else 270
                break
        add.append(label_xml(name, x, y, ang, n))
    i = s.rstrip().rindex("\n)")          # before the file's closing parenthesis
    s = s[:i + 1] + "".join(add) + s[i + 1:]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    print(f"  {len(dead)} wires pruned, {len(labels)} global labels placed")


if __name__ == "__main__":
    for f, plan in PLAN.items():
        print(f)
        strip(os.path.join(HERE, f), plan)
