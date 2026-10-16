"""Draw the main board's outline behind the Moirae panel, with the panel and
the stack traced on user layers. Run with KiCad's own Python:

    "/mnt/g/Program Files/KiCad/10.0/bin/python.exe" tools/make_outline.py

The board shares the panel builder's frame: panel point (x, y) is board point
(100 + x, 30 + y), so the panel's holes land on the board as drawn.

First run only: everything shieldXL left on the board (parts, tracks, zones,
artwork) moves aside by STASH_DX as a stash for Update PCB to reuse, and its
outline goes to User.9. Every run: Edge.Cuts and User.1-4 are redrawn.

  User.1  Panel        the panel as seen from the front: outline, holes and
                       its front artwork (title, labels, rings, the CORONE box)
  User.2  Front        the display module, between panel and board
  User.3  Pi (back)    Pi 4, upside down, landscape: its 40-pin header along
                       the top, behind the display, clear of the controls;
                       its two screw holes by the header, the printed feet at
                       the other corners, port block and the USB adapters' room
  User.4  Corone       the room for the daughterboard, below the Pi
  User.5  Panel back   the panel's back artwork, as KiCad draws B.Silkscreen
"""

import os

import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(HERE, "shieldXL-euro.kicad_pcb")
PANEL = os.path.normpath(os.path.join(HERE, "..", "..", "..", "Missing Mile Modular", "ShieldXL Euro",
                                     "shieldxl_euro_panel.kicad_pcb"))
OX, OY = 100.0, 30.0                 # panel origin on the board
STASH_DX = 160.0
SILK = {pcbnew.F_SilkS: "F", pcbnew.B_SilkS: "B"}
STASH_MARK = "SHIELDXL DESKTOP BOARD - PARTS STASH"

# --- the board: inside the rails, inside the panel's width ------------------------
# 108 mm between the rails (10.25 - 118.25 of the 128.5 panel), 1.65 mm in from
# each side of the 20 HP, 101.3 mm panel.
PANEL_W = 101.3
BX0, BX1, BY0, BY1, BR = 1.65, PANEL_W - 1.65, 10.25, 118.25, 1.0

# --- the display module, on standoffs between panel and board ---------------------
DISP_W, DISP_H, DISP_TOP = 82.0, 47.5, 10.5
DISP_X0 = PANEL_W / 2 - DISP_W / 2
# Its FPC cable runs from the module's connector through a slot in the board to
# the connector on the back (U$1), kept where shieldXL had them relative to the
# display: there the module's lower-right hole (NHD-2.7-12864WDW3-M, holes 2.5 in
# from each edge) sat on the board hole at (319.948, 136.417), so its top-left
# corner was at (240.448, 91.417). From that corner:
FPC_SLOT = (28.045, 29.182, 54.253, 33.241)     # x0, y0, x1, y1; 1 mm corners
FPC_SLOT_R = 1.0
# the module's own mounting holes, d2.5, 2.5 in from each edge (77 x 42.5 apart);
# not the top-left one, which falls on the Pi header's pin 2
DISP_HOLE_IN, DISP_HOLE_D = 2.5, 2.5
DISP_HOLES = [(DISP_HOLE_IN, DISP_H - DISP_HOLE_IN), (DISP_W - DISP_HOLE_IN, DISP_HOLE_IN),
              (DISP_W - DISP_HOLE_IN, DISP_H - DISP_HOLE_IN)]

# --- Pi 4 on the back: 85 x 56, holes 3.5 in on a 58 x 49 grid, the 40-pin
# header on a long edge, centred 3.5 in, pins 1-40 from 8.37 to 56.63 along it.
# Upside down (its top faces the board), landscape, header along the top: seen
# from the front it reads as a Pi seen from above, Pi (px, py) -> board
# (PI_X0 + px, PI_Y0 + py). microSD to the left, ports to the right.
PI_L, PI_W = 85.0, 56.0
SD_PROUD = 2.6                       # the card, past the left edge
PORT_PROUD = 2.9                     # USB and Ethernet past the board edge
# Ports along the far short edge, from the Pi's mechanical drawing (centres
# measured from the edge opposite the header): USB stacks at 27 and 9, 13.2
# wide, 17.5 deep; Ethernet at 45.75, 15.3 wide, 21.4 deep.
USB_PY = (56.0 - 27.0, 56.0 - 9.0)   # stack centres, from the header edge
USB_W, USB_DEPTH = 13.2, 17.5
ETH_PY, ETH_W, ETH_DEPTH = 56.0 - 45.75, 15.3, 21.4
ADAPTER = 6.0                        # USB adapter beyond the port faces
PI_X0 = BX0 + SD_PROUD               # card flush with the board edge
PI_Y0 = BY0 + 0.5

# --- Corone: below the Pi, clear of its standoffs ----------------------------------
CORONE = (BX0 + 4.0, PI_Y0 + PI_W + 3.0, BX0 + 64.0, BY1 - 3.0)


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def pi_pt(px, py):
    return PI_X0 + px, PI_Y0 + py


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
    """The panel's cuts, holes and silkscreen as plain numbers (panel frame,
    mm). KiCad's Python holds one board at a time, so this is read before the
    main board."""
    panel = pcbnew.LoadBoard(PANEL)
    T = lambda v: (pcbnew.ToMM(v.x) - OX, pcbnew.ToMM(v.y) - OY)
    cuts, holes, art = [], [], []
    for d in panel.GetDrawings():
        if d.GetLayer() in SILK:
            art.append(art_item(d, T))
            continue
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
        for g in fp.GraphicalItems():
            if g.GetLayer() in SILK and isinstance(g, pcbnew.PCB_SHAPE):
                art.append(art_item(g, T))
    return cuts, holes, art


def art_item(d, T):
    """One silkscreen shape: (side, kind, points, width, filled)."""
    k = d.GetShape()
    if k == pcbnew.SHAPE_T_SEGMENT:
        pts = (T(d.GetStart()), T(d.GetEnd()))
    elif k == pcbnew.SHAPE_T_ARC:
        pts = (T(d.GetStart()), T(d.GetArcMid()), T(d.GetEnd()))
    elif k == pcbnew.SHAPE_T_CIRCLE:
        pts = (T(d.GetCenter()), pcbnew.ToMM(d.GetRadius()))
    elif k == pcbnew.SHAPE_T_BEZIER:
        pts = (T(d.GetStart()), T(d.GetBezierC1()), T(d.GetBezierC2()), T(d.GetEnd()))
    elif k == pcbnew.SHAPE_T_RECTANGLE:
        pts = (T(d.GetStart()), T(d.GetEnd()))
    elif k == pcbnew.SHAPE_T_POLY:
        pts = tuple(T(d.GetPolyShape().CVertex(i)) for i in range(d.GetPolyShape().TotalVertices()))
    else:
        raise ValueError(f"panel artwork of shape {k}")
    return SILK[d.GetLayer()], k, pts, pcbnew.ToMM(d.GetWidth()), d.IsSolidFill()


def draw_art(board, layer, k, pts, width, filled):
    s = shape(board, layer, k, width)
    if k == pcbnew.SHAPE_T_ARC:
        s.SetArcGeometry(*(pt(*p) for p in pts))
    elif k == pcbnew.SHAPE_T_CIRCLE:
        s.SetCenter(pt(*pts[0]))
        s.SetEnd(pt(pts[0][0] + pts[1], pts[0][1]))
    elif k == pcbnew.SHAPE_T_BEZIER:
        s.SetStart(pt(*pts[0]))
        s.SetBezierC1(pt(*pts[1]))
        s.SetBezierC2(pt(*pts[2]))
        s.SetEnd(pt(*pts[3]))
        s.RebuildBezierToSegmentsPointsList(mm(0.005))
    elif k == pcbnew.SHAPE_T_POLY:
        s.SetPolyPoints([pt(*p) for p in pts])
    else:
        s.SetStart(pt(*pts[0]))
        s.SetEnd(pt(*pts[1]))
    if filled:
        s.SetFilled(True)


def build():
    lock = os.path.join(os.path.dirname(BOARD), "~" + os.path.basename(BOARD) + ".lck")
    if os.path.exists(lock):
        raise SystemExit("the board is open in KiCad (lock file found): save, close it, then run again")
    cuts, holes, art = panel_geometry()
    board = pcbnew.LoadBoard(BOARD)
    moved = stash(board)
    layers = {pcbnew.Edge_Cuts: None, pcbnew.User_1: "Panel", pcbnew.User_2: "Front",
              pcbnew.User_3: "Pi (back)", pcbnew.User_4: "Corone", pcbnew.User_5: "Panel back"}
    for d in list(board.GetDrawings()):
        if d.GetLayer() in layers and not (isinstance(d, pcbnew.PCB_TEXT) and d.GetText() == STASH_MARK):
            board.Remove(d)
    for layer, name in layers.items():
        if name:
            board.SetLayerName(layer, name)

    # the board
    rect(board, pcbnew.Edge_Cuts, BX0, BY0, BX1, BY1, 0.1, BR)
    sx0, sy0, sx1, sy1 = FPC_SLOT
    rect(board, pcbnew.Edge_Cuts, DISP_X0 + sx0, DISP_TOP + sy0, DISP_X0 + sx1, DISP_TOP + sy1, 0.05, FPC_SLOT_R)
    for hx, hy in DISP_HOLES:
        circle(board, pcbnew.Edge_Cuts, DISP_X0 + hx, DISP_TOP + hy, DISP_HOLE_D / 2, 0.05)

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
    for side, *a in art:
        draw_art(board, pcbnew.User_1 if side == "F" else pcbnew.User_5, *a)

    # User.2: the display module
    dx0 = DISP_X0
    rect(board, pcbnew.User_2, dx0, DISP_TOP, dx0 + DISP_W, DISP_TOP + DISP_H)
    text(board, pcbnew.User_2, "DISPLAY MODULE (FRONT)", PANEL_W / 2, DISP_TOP + DISP_H - 3)

    # User.3: the Pi
    U3 = pcbnew.User_3
    (ax, ay), (bx, by) = pi_pt(0, 0), pi_pt(PI_L, PI_W)
    rect(board, U3, min(ax, bx), min(ay, by), max(ax, bx), max(ay, by), 0.15)
    for px in (3.5, 61.5):
        x, y = pi_pt(px, 3.5)                    # by the header: screwed down
        circle(board, U3, x, y, 1.35)            # M2.5
        circle(board, U3, x, y, 2.75)            # standoff
        x, y = pi_pt(px, 52.5)                   # far edge: a printed foot fixed
        circle(board, U3, x, y, 2.75)            # to the Pi, no hole here - K1
        text(board, U3, "FOOT", x, y + 4.0, 0.8)  # and E2 sit under these corners
    hx0, hy0 = pi_pt(8.37 - 1.27, 3.5 - 2.54)
    hx1, hy1 = pi_pt(56.63 + 1.27, 3.5 + 2.54)
    rect(board, U3, min(hx0, hx1), min(hy0, hy1), max(hx0, hx1), max(hy0, hy1), 0.15)
    x, y = pi_pt(8.37, 3.5 + 1.27)
    text(board, U3, "1", x - 3, y, 1.2)
    for c, w, d in [(c, USB_W, USB_DEPTH) for c in USB_PY] + [(ETH_PY, ETH_W, ETH_DEPTH)]:
        x0, y0 = pi_pt(PI_L - d + PORT_PROUD, c - w / 2)
        x1, y1 = pi_pt(PI_L + PORT_PROUD, c + w / 2)
        rect(board, U3, x0, y0, x1, y1, 0.1)
    for c in USB_PY:
        x0, y0 = pi_pt(PI_L + PORT_PROUD, c - USB_W / 2 - 1.0)
        x1, y1 = pi_pt(PI_L + PORT_PROUD + ADAPTER, c + USB_W / 2 + 1.0)
        rect(board, U3, x0, y0, x1, y1, 0.1)
    px0, py0 = pi_pt(PI_L - USB_DEPTH, USB_PY[0])
    px1, py1 = pi_pt(PI_L, USB_PY[1])
    sx0, sy0 = pi_pt(-SD_PROUD, 22.0)
    sx1, sy1 = pi_pt(0, 34.0)
    rect(board, U3, sx0, sy0, sx1, sy1, 0.1)
    text(board, U3, "PI 4, UPSIDE DOWN (BACK)", PI_X0 + PI_L / 2 - 8, PI_Y0 + 32)
    text(board, U3, "PORTS", (px0 + px1) / 2, (py0 + py1) / 2, 1.2)
    x, y = pi_pt(PI_L + PORT_PROUD + ADAPTER / 2, USB_PY[0] - USB_W / 2 - 3.0)
    text(board, U3, "USB", x, y, 1.0)
    text(board, U3, "40-PIN", (hx0 + hx1) / 2, max(hy0, hy1) + 2.0, 1.0)

    # User.4: Corone's room
    rect(board, pcbnew.User_4, *CORONE, 0.15)
    text(board, pcbnew.User_4, "CORONE", (CORONE[0] + CORONE[2]) / 2, (CORONE[1] + CORONE[3]) / 2 + 4)

    pcbnew.SaveBoard(BOARD, board)
    return moved, len(art)


if __name__ == "__main__":
    moved, n_art = build()
    print("stashed shieldXL's layout" if moved else "stash already in place")
    print(f"board {BX1 - BX0:.2f} x {BY1 - BY0:.2f} mm; Pi x {PI_X0:.2f}-{PI_X0 + PI_L:.2f}, y {PI_Y0:.2f}-{PI_Y0 + PI_W:.2f}; "
          f"adapters to x {PI_X0 + PI_L + PORT_PROUD + ADAPTER:.2f} (panel {PANEL_W})")
    print(f"panel artwork copied: {n_art} shapes")
    print(f"Corone room {CORONE[2] - CORONE[0]:.1f} x {CORONE[3] - CORONE[1]:.1f} mm")
