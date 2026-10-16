"""Draw the main board's outline behind the Moirae panel, with the panel and
the stack traced on user layers. Run with KiCad's own Python:

    "/mnt/g/Program Files/KiCad/10.0/bin/python.exe" tools/make_outline.py

The board shares the panel builder's frame: panel point (x, y) is board point
(100 + x, 30 + y), so the panel's holes land on the board as drawn.

First run only: everything shieldXL left on the board (parts, tracks, zones,
artwork) moves aside by STASH_DX as a stash for Update PCB to reuse, and its
outline goes to User.9. Every run: Edge.Cuts and User.1-4 are redrawn.

  User.1  Panel        the panel's outline, holes and openings
  User.2  Front        the display module, between panel and board
  User.3  Pi (back)    Pi 4, upside down, ports toward the bottom rail; its
                       holes, 40-pin header, port block and the USB plugs'
                       room
  User.4  Corone       the room for the daughterboard, under the Pi
"""

import os

import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(HERE, "shieldXL-euro.kicad_pcb")
PANEL = os.path.normpath(os.path.join(HERE, "..", "..", "..", "Missing Mile Modular", "ShieldXL Euro",
                                     "shieldxl_euro_panel.kicad_pcb"))
OX, OY = 100.0, 30.0                 # panel origin on the board
STASH_DX = 160.0
STASH_MARK = "SHIELDXL DESKTOP BOARD - PARTS STASH"

# --- the board: inside the rails, inside the panel's width ------------------------
# 108 mm between the rails (10.25 - 118.25 of the 128.5 panel), 1.65 mm in from
# each side of the 91.3 mm panel.
BX0, BX1, BY0, BY1, BR = 1.65, 89.65, 10.25, 118.25, 1.0

# --- the display module, on standoffs between panel and board ---------------------
DISP_W, DISP_H, DISP_TOP = 82.0, 47.5, 10.5
PANEL_W = 91.3

# --- Pi 4 on the back: 85 x 56, holes 3.5 in on a 58 x 49 grid, the 40-pin
# header on the long edge, centred 3.5 in, pins 1-40 from 8.37 to 56.63 along it.
# Upside down (its top faces the board) and turned so its ports face the
# bottom rail: Pi (px, py) -> board (PI_X1 - py, PI_Y0 + px).
PI_L, PI_W = 85.0, 56.0
PI_Y0 = BY0 + 2.6                    # the microSD card stands 2.6 proud of the top edge
PI_X1 = PANEL_W / 2 + PI_W / 2       # centred
PORT_PROUD, PORT_DEPTH = 2.8, 21.5   # Ethernet: furthest out, deepest
PLUG_ROOM = BY1                      # adapter plugs, down to the board's bottom edge

# --- Corone: inside the Pi's four standoffs, above its port block -----------------
CORONE = (PI_X1 - PI_W + 6.5, PI_Y0 + 8.0, PI_X1 - 7.5, PI_Y0 + 85 - PORT_DEPTH - 2.0)


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def pi_pt(px, py):
    return PI_X1 - py, PI_Y0 + px


def shape(board, layer, kind, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(kind)
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    board.Add(s)
    return s


def line(board, layer, a, b, width=0.1):
    s = shape(board, layer, pcbnew.SHAPE_T_SEGMENT, width)
    s.SetStart(pt(*a))
    s.SetEnd(pt(*b))


def rect(board, layer, x0, y0, x1, y1, width=0.1, r=0.0):
    s = shape(board, layer, pcbnew.SHAPE_T_RECTANGLE, width)
    s.SetStart(pt(x0, y0))
    s.SetEnd(pt(x1, y1))
    if r:
        s.SetCornerRadius(mm(r))


def circle(board, layer, x, y, r, width=0.1):
    s = shape(board, layer, pcbnew.SHAPE_T_CIRCLE, width)
    s.SetCenter(pt(x, y))
    s.SetEnd(pt(x + r, y))


def text(board, layer, s, x, y, size=1.5):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetPosition(pt(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * 0.12))
    board.Add(t)


def stash(board):
    """Move shieldXL's desktop layout aside, once, and keep its outline on User.9."""
    for d in board.GetDrawings():
        if isinstance(d, pcbnew.PCB_TEXT) and d.GetText() == STASH_MARK:
            return False
    v = pcbnew.VECTOR2I(mm(STASH_DX), 0)
    for item in list(board.GetFootprints()) + list(board.GetTracks()) + list(board.Zones()) + list(board.GetDrawings()):
        item.Move(v)
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            d.SetLayer(pcbnew.User_9)
    text(board, pcbnew.User_9, STASH_MARK, 140 + STASH_DX - OX, 20, 3)
    return True


def panel_geometry():
    """The panel's cuts and holes as plain numbers (panel frame, mm). KiCad's
    Python holds one board at a time, so this is read before the main board."""
    panel = pcbnew.LoadBoard(PANEL)
    T = lambda v: (pcbnew.ToMM(v.x) - OX, pcbnew.ToMM(v.y) - OY)
    cuts, holes = [], []
    for d in panel.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        k = d.GetShape()
        if k == pcbnew.SHAPE_T_ARC:
            cuts.append(("arc", T(d.GetStart()), T(d.GetArcMid()), T(d.GetEnd())))
        elif k == pcbnew.SHAPE_T_CIRCLE:
            cuts.append(("circle", T(d.GetCenter()), pcbnew.ToMM(d.GetRadius())))
        elif k == pcbnew.SHAPE_T_SEGMENT:
            cuts.append(("line", T(d.GetStart()), T(d.GetEnd())))
        elif k == pcbnew.SHAPE_T_RECTANGLE:
            cuts.append(("rect", T(d.GetStart()), T(d.GetEnd())))
        else:
            raise ValueError(f"panel cut of shape {k}")
    for fp in panel.GetFootprints():
        for pad in fp.Pads():
            holes.append((*T(fp.GetPosition()), pcbnew.ToMM(pad.GetDrillSize().x) / 2))
    return cuts, holes


def build():
    cuts, holes = panel_geometry()
    board = pcbnew.LoadBoard(BOARD)
    moved = stash(board)
    layers = {pcbnew.Edge_Cuts: None, pcbnew.User_1: "Panel", pcbnew.User_2: "Front",
              pcbnew.User_3: "Pi (back)", pcbnew.User_4: "Corone"}
    for d in list(board.GetDrawings()):
        if d.GetLayer() in layers and not (isinstance(d, pcbnew.PCB_TEXT) and d.GetText() == STASH_MARK):
            board.Remove(d)
    for layer, name in layers.items():
        if name:
            board.SetLayerName(layer, name)

    # the board
    rect(board, pcbnew.Edge_Cuts, BX0, BY0, BX1, BY1, 0.1, BR)

    # User.1: the panel, traced from its own file
    for c in cuts:
        if c[0] == "line":
            line(board, pcbnew.User_1, c[1], c[2])
        elif c[0] == "rect":
            rect(board, pcbnew.User_1, *c[1], *c[2])
        elif c[0] == "circle":
            circle(board, pcbnew.User_1, *c[1], c[2])
        else:
            a = shape(board, pcbnew.User_1, pcbnew.SHAPE_T_ARC)
            a.SetArcGeometry(pt(*c[1]), pt(*c[2]), pt(*c[3]))
    for x, y, r in holes:
        circle(board, pcbnew.User_1, x, y, r)

    # User.2: the display module
    dx0 = PANEL_W / 2 - DISP_W / 2
    rect(board, pcbnew.User_2, dx0, DISP_TOP, dx0 + DISP_W, DISP_TOP + DISP_H)
    text(board, pcbnew.User_2, "DISPLAY MODULE (FRONT)", PANEL_W / 2, DISP_TOP + DISP_H - 3)

    # User.3: the Pi
    U3 = pcbnew.User_3
    (ax, ay), (bx, by) = pi_pt(0, 0), pi_pt(PI_L, PI_W)
    rect(board, U3, min(ax, bx), min(ay, by), max(ax, bx), max(ay, by), 0.15)
    for px in (3.5, 61.5):
        for py in (3.5, 52.5):
            x, y = pi_pt(px, py)
            circle(board, U3, x, y, 1.35)            # M2.5
            circle(board, U3, x, y, 2.75)            # standoff
    hx0, hy0 = pi_pt(8.37 - 1.27, 3.5 - 2.54)
    hx1, hy1 = pi_pt(56.63 + 1.27, 3.5 + 2.54)
    rect(board, U3, min(hx0, hx1), min(hy0, hy1), max(hx0, hx1), max(hy0, hy1), 0.15)
    x, y = pi_pt(8.37, 3.5 + 1.27)
    text(board, U3, "1", x - 3, y, 1.2)
    px0, py0 = pi_pt(PI_L - PORT_DEPTH, 0)
    px1, py1 = pi_pt(PI_L + PORT_PROUD, PI_W)
    rect(board, U3, min(px0, px1), min(py0, py1), max(px0, px1), max(py0, py1), 0.1)
    rect(board, U3, min(px0, px1), max(py0, py1), max(px0, px1), PLUG_ROOM, 0.1)
    sx0, sy0 = pi_pt(-2.6, 22.0)
    sx1, sy1 = pi_pt(0, 34.0)
    rect(board, U3, min(sx0, sx1), min(sy0, sy1), max(sx0, sx1), max(sy0, sy1), 0.1)
    cx = (min(ax, bx) + max(ax, bx)) / 2
    text(board, U3, "PI 4, UPSIDE DOWN (BACK)", cx, PI_Y0 + 40)
    text(board, U3, "PORTS", cx, (min(py0, py1) + max(py0, py1)) / 2, 1.2)
    text(board, U3, "USB PLUGS", cx, (max(py0, py1) + PLUG_ROOM) / 2, 1.2)
    text(board, U3, "40-PIN", max(hx0, hx1) + 3.5, (hy0 + hy1) / 2, 1.0)

    # User.4: Corone's room
    rect(board, pcbnew.User_4, *CORONE, 0.15)
    text(board, pcbnew.User_4, "CORONE", (CORONE[0] + CORONE[2]) / 2, (CORONE[1] + CORONE[3]) / 2 + 4)

    pcbnew.SaveBoard(BOARD, board)
    return moved


if __name__ == "__main__":
    moved = build()
    print("stashed shieldXL's layout" if moved else "stash already in place")
    print(f"board {BX1 - BX0:.2f} x {BY1 - BY0:.2f} mm; Pi x {PI_X1 - PI_W:.2f}-{PI_X1:.2f}, y {PI_Y0:.2f}-{PI_Y0 + PI_L:.2f}")
    print(f"Corone room {CORONE[2] - CORONE[0]:.1f} x {CORONE[3] - CORONE[1]:.1f} mm")
