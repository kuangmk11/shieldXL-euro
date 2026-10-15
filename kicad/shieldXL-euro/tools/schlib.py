"""Small helpers for editing KiCad 10 schematics as text: find symbol
instances, work out where their pins are on the sheet, and check those points
against the wires already drawn."""

import math
import re


def blocks(s, head):
    """(start, end, text) of each top-level `\\n\\t(<head>` block."""
    out, pat = [], f"\n\t({head}"
    i = s.find(pat)
    while i >= 0:
        j, d = i + 1, 0
        for k in range(j, len(s)):
            if s[k] == "(":
                d += 1
            elif s[k] == ")":
                d -= 1
                if d == 0:
                    break
        out.append((i, k + 1, s[j:k + 1]))
        i = s.find(pat, k)
    return out


def lib_pins(s, lib_id, unit=1):
    """{pin number: (x, y)} of an embedded library symbol, in symbol units (Y up)."""
    i = s.index("(lib_symbols")
    j = s.index(f'(symbol "{lib_id}"', i)
    d = 0
    for k in range(j, len(s)):
        if s[k] == "(":
            d += 1
        elif s[k] == ")":
            d -= 1
            if d == 0:
                break
    blk = s[j:k + 1]
    pins = {}
    for sub in re.finditer(r'\(symbol "[^"]*_(\d+)_(\d+)"', blk):
        u = int(sub.group(1))
        if u not in (0, unit):
            continue
        a = sub.start()
        d = 0
        for m in range(a, len(blk)):
            if blk[m] == "(":
                d += 1
            elif blk[m] == ")":
                d -= 1
                if d == 0:
                    break
        for x, y, num in re.findall(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) [-\d.]+\)[\s\S]*?\(number "([^"]*)"', blk[a:m]):
            pins[num] = (float(x), float(y))
    return pins


def instances(s):
    """Symbol instances on a sheet: dicts with ref, lib_id, at, rot, mirror, unit, span."""
    out = []
    for a, b, t in blocks(s, "symbol\n"):
        lib = re.search(r'\(lib_id "([^"]+)"\)', t)
        if not lib:
            continue
        at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)', t)
        mir = re.search(r'\n\t\t\(mirror (\w+)\)', t)
        unit = int(re.search(r'\(unit (\d+)\)', t).group(1))
        ref = re.search(r'\(reference "([^"]+)"\)', t) or re.search(r'\(property "Reference" "([^"]+)"', t)
        out.append(dict(ref=ref.group(1), lib_id=lib.group(1), x=float(at.group(1)), y=float(at.group(2)),
                        rot=float(at.group(3)), mirror=mir.group(1) if mir else None, unit=unit, span=(a, b)))
    return out


def pin_points(s, inst):
    """{pin: (x, y)} on the sheet. KiCad mirrors in symbol space, then rotates
    counter-clockwise, then flips Y onto the sheet."""
    out = {}
    for num, (px, py) in lib_pins(s, inst["lib_id"], inst["unit"]).items():
        if inst["mirror"] == "x":
            py = -py
        elif inst["mirror"] == "y":
            px = -px
        a = math.radians(inst["rot"])
        rx = px * math.cos(a) - py * math.sin(a)
        ry = px * math.sin(a) + py * math.cos(a)
        out[num] = (round(inst["x"] + rx, 3), round(inst["y"] - ry, 3))
    return out


def wire_ends(s):
    pts = set()
    for _, _, t in blocks(s, "wire"):
        for x, y in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', t):
            pts.add((round(float(x), 3), round(float(y), 3)))
    for head in ("label", "global_label", "junction", "no_connect"):
        for _, _, t in blocks(s, head):
            m = re.search(r'\(at ([-\d.]+) ([-\d.]+)', t)
            pts.add((round(float(m.group(1)), 3), round(float(m.group(2)), 3)))
    return pts
