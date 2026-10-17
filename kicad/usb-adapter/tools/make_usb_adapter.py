"""Write the Pi USB adapter: a small board that stands at one of the Pi 4's
USB stacks, two vertical male USB-A plugs in its two ports, and a 2 x 4 header
whose ribbon runs behind the Pi to the main board. Two identical boards
cover the Pi's four ports. Run with KiCad's own Python:

    "/mnt/g/Program Files/KiCad/10.0/bin/python.exe" tools/make_usb_adapter.py

writes usb-adapter.kicad_sch, usb-adapter.kicad_pro and
usb-adapter.pretty/USB_A_Plug_Vertical.kicad_mod, and usb-adapter.kicad_pcb
unplaced and unrouted only if there is none: the board is now routed by hand,
and the script leaves it alone (delete it to start over).

Board frame: u across the stack (along the Pi's port edge), v the height
above the main board's back. Drawn with x = 100 + u, y = 100 - v.

PLACEHOLDERS - set before ordering:
  PORT_ZC   each port's centre height above the Pi's PCB, read off the Pi 4
            STEP model (openings 2.45-7.55 and 11.57-16.69 above its 1.5 mm
            PCB's underside, tongue at the top of each). Check with calipers.
  the plug  a side-mount USB-A male (USB-71, L 15 mm) stood on end; the
            tail and tab slots are from its drawing, the tails on its centre
            line. Its 3D model is a 12 x 4.5 x 15 mm placeholder box.

Header pinout, in ribbon order (pair A between grounds, B between ground
and its VBUS):
  1 VBUS_A  2 GND  3 D-_A  4 D+_A  5 GND  6 D-_B  7 D+_B  8 VBUS_B
A is the port nearer the Pi's PCB, B the further one.
"""

import os
import re
import uuid

import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "usb-adapter"
KLIB = os.environ.get("KICAD_SYMBOLS", r"G:\Program Files\KiCad\10.0\share\kicad\symbols")
KFP = os.environ.get("KICAD_FOOTPRINTS", r"G:\Program Files\KiCad\10.0\share\kicad\footprints")
NS = uuid.UUID("5d2c8e1f-3a47-4b6c-9d0e-1f2a3b4c5d6e")
ROOT_UUID = str(uuid.uuid5(NS, "file"))

# --- the stack, from the main board's back ---------------------------------------
H = 20.0                     # the Pi's PCB (its top face) above the main board's back
PI_T, PI_UNDER = 1.4, 2.0    # Pi PCB thickness; its underside parts (microSD)
PORT_ZC = (3.49, 12.63)      # port centres above the Pi's PCB, A then B (from its STEP model)
W = 17.2                     # across the stack; the two stacks are 18 mm apart, 0.8 between boards
IDC_CLEAR = 0.6              # IDC body clear of the Pi's underside

# --- parts ------------------------------------------------------------------------
# The plug: a side-mount USB-A male ("USB-71", L = 15 mm short; the same pattern
# as Molex 48037) stood on its back end. Its four contact tails leave the back
# straight, in line with the plug, along the face the plastic insert is on;
# its shell tabs drop at the jack's two edges, 11.7 apart. Footprint origin at
# the plug's centre, which goes on the port's centre, the tails on its centre
# line; the insert side toward the Pi's PCB, so the Pi's tongue, along the top
# of each port, meets it. The two bottom posts, 4.5 apart, stand clear of the board: clip
# them or leave them.
PLUG_PINS = (-3.5, -1.0, 1.0, 3.5)   # 1 VBUS, 2 D-, 3 D+, 4 GND
PLUG_PIN_DY = 0.0                    # the tails, on the plug's centre line
PLUG_TAIL_SLOT, PLUG_TAIL_PAD = (1.0, 0.6), (1.5, 1.2)   # tails 0.7 wide
PLUG_SHELL_DX = 5.85                 # the tabs, at the jack's edges
PLUG_SHELL_SLOT, PLUG_SHELL_PAD = (0.9, 4.0), (1.5, 4.6)  # along the shell's 4.5 side
# a plain (unboxed) 2 x 4 pin header; the ribbon's IDC socket plugs onto it,
# and the main board's end (J112 / J113) is a boxed 2 x 4
IDC_FP = ("Connector_PinHeader_2.54mm", "PinHeader_2x04_P2.54mm_Vertical")
IDC_ROWS = 4
IDC_BODY = 10.16             # along v; the pins span 7.62 of it
NETS_IDC = {"1": "VBUS_A", "2": "GND", "3": "DM_A", "4": "DP_A",
            "5": "GND", "6": "DM_B", "7": "DP_B", "8": "VBUS_B"}


def v_of_port(i):
    return H - PORT_ZC[i]


def plug_footprint():
    tw, th = PLUG_TAIL_SLOT
    pw, ph = PLUG_TAIL_PAD
    sw, sh = PLUG_SHELL_SLOT
    qw, qh = PLUG_SHELL_PAD
    pads = []
    for n, x in enumerate(PLUG_PINS, 1):
        shape = "rect" if n == 1 else "oval"
        pads.append(f'\t(pad "{n}" thru_hole {shape} (at {x:g} {PLUG_PIN_DY:g}) (size {pw:g} {ph:g}) '
                    f'(drill oval {tw:g} {th:g}) (layers "*.Cu" "*.Mask"))')
    for x in (-PLUG_SHELL_DX, PLUG_SHELL_DX):
        pads.append(f'\t(pad "SH" thru_hole oval (at {x:g} 0) (size {qw:g} {qh:g}) '
                    f'(drill oval {sw:g} {sh:g}) (layers "*.Cu" "*.Mask"))')
    y0, y1 = -2.25, 2.25
    body = (f'\t(fp_rect (start -6 {y0:g}) (end 6 {y1:g}) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))\n'
            f'\t(fp_line (start -4.5 {y0 + 0.6:g}) (end 4.5 {y0 + 0.6:g}) (stroke (width 0.1) (type solid)) (layer "F.Fab"))\n'
            f'\t(fp_text user "insert" (at 0 {y0 + 1.4:g} 0) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.08))))\n'
            f'\t(fp_rect (start -7.0 {y0 - 0.75:g}) (end 7.0 {y1 + 0.75:g}) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))\n')
    return ('(footprint "USB_A_Plug_Vertical"\n\t(version 20240108)\n\t(generator "make_usb_adapter.py")\n\t(layer "F.Cu")\n'
            '\t(descr "USB-A male plug, side-mount USB-71 type (L 15 mm, Molex 48037 pattern) stood on its back end: '
            'tails straight through in slots, shell tabs in slots at the jack edges")\n'
            '\t(attr through_hole)\n'
            '\t(property "Reference" "REF**" (at 0 -4.5 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
            '\t(property "Value" "USB_A_Plug_Vertical" (at 0 4.0 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))\n'
            + body + "\n".join(pads) + "\n"
            # a 12 x 4.5 x 15 mm box standing in for the plug
            '\t(model "${KIPRJMOD}/3d/USB_A_plug_placeholder.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n'
            ")\n")


# --- schematic ----------------------------------------------------------------------
def balanced(s, j):
    d = 0
    for k in range(j, len(s)):
        if s[k] == "(":
            d += 1
        elif s[k] == ")":
            d -= 1
            if d == 0:
                return s[j:k + 1]


def embed(lib, name):
    s = open(os.path.join(KLIB, lib + ".kicad_sym"), encoding="utf-8").read()
    i = s.find(f'\n\t(symbol "{name}"')
    return balanced(s, i + 1).replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)


def pins_of(block):
    out = {}
    for x, y, a, num in re.findall(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)[\s\S]*?\(number "([^"]*)"', block):
        out[num] = (float(x), float(y), int(float(a)))
    return out


SCH_PARTS = [
    ("J1", "Connector", "USB_A", "USB-A plug, port A", f"{NAME}:USB_A_Plug_Vertical", (50.8, 50.8),
     {"1": "VBUS_A", "2": "DM_A", "3": "DP_A", "4": "GND", "SH": "GND"}),
    ("J2", "Connector", "USB_A", "USB-A plug, port B", f"{NAME}:USB_A_Plug_Vertical", (50.8, 88.9),
     {"1": "VBUS_B", "2": "DM_B", "3": "DP_B", "4": "GND", "SH": "GND"}),
    ("J3", "Connector_Generic", "Conn_02x04_Odd_Even", "To main board", ":".join(IDC_FP), (127.0, 66.04), NETS_IDC),
]


def write_schematic():
    """Write the schematic; return each part's symbol uuid, for the board to link to."""
    n = [0]
    sym_uuid = {}

    def uid():
        n[0] += 1
        return str(uuid.uuid5(NS, f"s{n[0]}"))

    def prop(k, v, x, y, hide=False):
        h = " (hide yes)" if hide else ""
        return f'\t\t(property "{k}" "{v}" (at {x:g} {y:g} 0) (effects (font (size 1.27 1.27)){h}))\n'

    blocks = {f"{lib}:{sym}": embed(lib, sym) for _, lib, sym, *_ in SCH_PARTS}
    blocks["power:GND"] = embed("power", "GND")
    blocks["power:PWR_FLAG"] = embed("power", "PWR_FLAG")
    o = ["(kicad_sch", "\t(version 20231120)", '\t(generator "make_usb_adapter.py")', '\t(generator_version "8.0")',
         f'\t(uuid "{ROOT_UUID}")', '\t(paper "A4")', "\t(title_block", '\t\t(title "Pi USB adapter")',
         '\t\t(comment 1 "Generated by tools/make_usb_adapter.py - do not edit by hand")', "\t)", "\t(lib_symbols"]
    o += ["\t\t" + b.replace("\n\t", "\n\t\t") for b in blocks.values()]
    o.append("\t)")

    def inst(lib_id, ref, value, fp, x, y, pins, hide=False):
        sym_uuid[ref] = uid()
        s = (f'\t(symbol (lib_id "{lib_id}") (at {x:g} {y:g} 0) (unit 1) (exclude_from_sim no) '
             f'(in_bom {"no" if ref.startswith("#") else "yes"}) (on_board yes) (dnp no)\n\t\t(uuid "{sym_uuid[ref]}")\n'
             + prop("Reference", ref, x + 2.54, y - 10.16, hide) + prop("Value", value, x + 2.54, y + 10.16, hide)
             + prop("Footprint", fp, x, y, True) + prop("Datasheet", "", x, y, True))
        s += "".join(f'\t\t(pin "{p}" (uuid "{uid()}"))\n' for p in pins)
        return s + (f'\t\t(instances (project "{NAME}" (path "/{ROOT_UUID}" (reference "{ref}") (unit 1))))\n\t)')

    npwr = [0]
    away = {0: (180, "right"), 180: (0, "left"), 90: (270, "right"), 270: (90, "left")}
    for ref, lib, sym, value, fp, (x, y), conn in SCH_PARTS:
        pp = pins_of(blocks[f"{lib}:{sym}"])
        o.append(inst(f"{lib}:{sym}", ref, value, fp, x, y, list(pp)))
        for num, net in conn.items():
            px, py, pa = pp[num]
            ax, ay = round(x + px, 2), round(y - py, 2)
            if net == "GND":
                npwr[0] += 1
                (gx, gy, _), = pins_of(blocks["power:GND"]).values()
                o.append(inst("power:GND", f"#PWR{npwr[0]:02d}", "GND", "", round(ax - gx, 3), round(ay + gy, 3), ["1"], True))
            else:
                a, j = away[pa]
                o.append(f'\t(label "{net}" (at {ax:g} {ay:g} {a}) (effects (font (size 1.27 1.27)) (justify {j} bottom)) (uuid "{uid()}"))')
    (gx, gy, _), = pins_of(blocks["power:GND"]).values()
    o.append(inst("power:GND", "#PWR99", "GND", "", 25.4, 25.4, ["1"], True))
    o.append(inst("power:PWR_FLAG", "#FLG01", "PWR_FLAG", "", 25.4, 25.4 - gy, ["1"], True))
    for i, net in enumerate(("VBUS_A", "VBUS_B")):
        x = 40.64 + 15.24 * i
        o.append(f'\t(label "{net}" (at {x:g} 25.4 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uid()}"))')
        o.append(inst("power:PWR_FLAG", f"#FLG{i + 2:02d}", "PWR_FLAG", "", x, 25.4, ["1"], True))
    o.append('\t(sheet_instances (path "/" (page "1")))')
    o.append(")")
    with open(os.path.join(HERE, f"{NAME}.kicad_sch"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(o) + "\n")
    return sym_uuid


# --- board --------------------------------------------------------------------------
def mm(v):
    return pcbnew.FromMM(v)


def at(u, v):
    return pcbnew.VECTOR2I(mm(100 + u), mm(100 - v))


def net_name(n):
    """The schematic's name for a net: local labels get the root sheet's '/'."""
    return n if n == "GND" else "/" + n


def write_board(sym_uuid):
    lib = os.path.join(HERE, f"{NAME}.pretty")
    os.makedirs(lib, exist_ok=True)
    with open(os.path.join(lib, "USB_A_Plug_Vertical.kicad_mod"), "w", encoding="utf-8", newline="\n") as f:
        f.write(plug_footprint())

    board = pcbnew.BOARD()
    nets = {}
    for name in sorted(set(NETS_IDC.values())):
        n = pcbnew.NETINFO_ITEM(board, net_name(name))
        board.Add(n)
        nets[name] = n

    def place(libpath, nick, fpname, ref, value, u, v, conn):
        fp = pcbnew.FootprintLoad(libpath, fpname)
        fp.SetFPID(pcbnew.LIB_ID(nick, fpname))
        fp.SetPath(pcbnew.KIID_PATH("/" + sym_uuid[ref]))
        fp.SetSheetname("/")
        fp.SetSheetfile(f"{NAME}.kicad_sch")
        fp.SetReference(ref)
        fp.SetValue(value)
        board.Add(fp)
        fp.SetPosition(at(u, v))
        fp.Reference().SetVisible(False)     # no room on a 17 mm board; J1 / J2 / J3 go on the fab layer
        for pad in fp.Pads():
            if pad.GetNumber() in conn:
                pad.SetNet(nets[conn[pad.GetNumber()]])
        return fp

    for port, (ref, _, _, value, _, _, conn) in enumerate(SCH_PARTS[:2]):
        place(lib, NAME, "USB_A_Plug_Vertical", ref, value, 0, v_of_port(port), conn)

    # the IDC: behind the Pi, clear of its underside; pins in two columns along v
    body_bottom = H + PI_T + PI_UNDER + IDC_CLEAR
    pin1_v = body_bottom + (IDC_BODY - (IDC_ROWS - 1) * 2.54) / 2 + (IDC_ROWS - 1) * 2.54
    place(os.path.join(KFP, IDC_FP[0] + ".pretty"), IDC_FP[0], IDC_FP[1], "J3", "To main board", -1.27, pin1_v, NETS_IDC)

    # outline
    bottom = min(v_of_port(i) for i in (0, 1)) - 2.25 - 0.75
    top = body_bottom + IDC_BODY + 1.0
    r = pcbnew.PCB_SHAPE(board)
    r.SetShape(pcbnew.SHAPE_T_RECTANGLE)
    r.SetLayer(pcbnew.Edge_Cuts)
    r.SetWidth(mm(0.1))
    r.SetStart(at(-W / 2, top))
    r.SetEnd(at(W / 2, bottom))
    r.SetCornerRadius(mm(1.0))
    board.Add(r)
    for s, v in (("PI PCB", H), ("PI UNDERSIDE", H + PI_T + PI_UNDER)):
        line = pcbnew.PCB_SHAPE(board)
        line.SetShape(pcbnew.SHAPE_T_SEGMENT)
        line.SetLayer(pcbnew.Dwgs_User)
        line.SetWidth(mm(0.1))
        line.SetStart(at(-W / 2 - 3, v))
        line.SetEnd(at(W / 2 + 3, v))
        board.Add(line)
        t = pcbnew.PCB_TEXT(board)
        t.SetText(s)
        t.SetLayer(pcbnew.Dwgs_User)
        t.SetPosition(at(W / 2 + 10, v + 0.8))
        t.SetTextSize(pcbnew.VECTOR2I(mm(1), mm(1)))
        board.Add(t)
    out = os.path.join(HERE, f"{NAME}.kicad_pcb")
    if os.path.exists(out):
        print(f"{NAME}.kicad_pcb exists (routed by hand): left alone")
    else:
        pcbnew.SaveBoard(out, board)
    return W, top - bottom, bottom, top


def write_project():
    pro = os.path.join(HERE, f"{NAME}.kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w", encoding="utf-8", newline="\n") as f:
            f.write('{\n  "meta": {\n    "filename": "%s.kicad_pro",\n    "version": 1\n  }\n}\n' % NAME)
    with open(os.path.join(HERE, "fp-lib-table"), "w", encoding="utf-8", newline="\n") as f:
        f.write('(fp_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.pretty")(options "")(descr "Pi USB adapter"))\n)\n' % (NAME, NAME))


if __name__ == "__main__":
    write_project()
    w, h, bottom, top = write_board(write_schematic())
    print(f"board {w:.1f} x {h:.1f} mm, from {bottom:.1f} to {top:.1f} above the main board's back")
    print(f"plugs at {v_of_port(0):.1f} (A) and {v_of_port(1):.1f} (B); pitch {PORT_ZC[1] - PORT_ZC[0]:.2f}")
