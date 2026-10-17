"""Stitch the ground pours: tidy the pours, then drop vias that tie each
ground's front and back fill together. Run with KiCad's own Python, KiCad
closed:

    "/mnt/g/Program Files/KiCad/10.0/bin/python.exe" tools/stitch_ground.py [board]

The board defaults to Moirae's; give another's path (Corone's) to stitch that.
Grounds without a pour on that board are skipped.

- AGND's pour takes priority over GND's, so where they overlap AGND wins and
  GND flows around it, and both pours drop islands nothing connects to.
- A via goes on a PITCH grid wherever one fits wholly inside its net's fill on
  both layers. The fill already keeps its clearance from other copper, so a
  via inside it clears every track and pad; part courtyards are left alone.
- Then every island of fill that still has no via or through-hole pad of its
  net gets one, at the first spot inside it where a via fits on both layers -
  under a part's courtyard if need be, as small islands sit among parts.

A rerun adds nothing where vias already stand: no new via comes within
HOLE_GAP of any existing hole, so it only fills in what edits have opened up.
"""

import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "shieldXL-euro.kicad_pcb")
PITCH = 5.0                      # mm, the stitching grid
VIA_D, VIA_DRILL = 0.6, 0.3      # the Ground net class's via
MARGIN = 0.05                    # mm inside the fill beyond the via's edge
HOLE_GAP = 1.0                   # mm between a new via and any other hole, centre to centre beyond diameters
NETS = ("GND", "AGND")
FREE_COURTYARDS = {"X1", "DS1"}  # the Pi and the display sit above parts and vias alike
F, B = pcbnew.F_Cu, pcbnew.B_Cu


def mm(v):
    return pcbnew.FromMM(v)


def fits(fill, x, y, r):
    """A via of radius r at (x, y) lies wholly inside this fill."""
    if not fill.Contains(pcbnew.VECTOR2I(x, y)):
        return False
    for k in range(8):
        a = k * math.pi / 4
        if not fill.Contains(pcbnew.VECTOR2I(int(x + r * math.cos(a)), int(y + r * math.sin(a)))):
            return False
    return True


def main():
    lock = os.path.join(os.path.dirname(BOARD), "~" + os.path.basename(BOARD) + ".lck")
    if os.path.exists(lock):
        raise SystemExit("the board is open in KiCad (lock file found): save, close it, then run again")
    board = pcbnew.LoadBoard(BOARD)
    zones = {n: [z for z in board.Zones() if z.GetNetname() == n] for n in NETS}
    nets = [n for n in NETS if zones[n]]
    for z in zones.get("AGND", []):
        z.SetAssignedPriority(7)
    for n in nets:
        for z in zones[n]:
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    for fp in board.GetFootprints():
        fp.BuildCourtyardCaches()
    yards = [fp.GetCourtyard(l) for fp in board.GetFootprints() if fp.GetReference() not in FREE_COURTYARDS
             for l in (pcbnew.F_CrtYd, pcbnew.B_CrtYd)]
    holes = [(t.GetPosition().x, t.GetPosition().y, t.GetDrill() / 2) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetDrillSize().x:
                holes.append((p.GetPosition().x, p.GetPosition().y, max(p.GetDrillSize().x, p.GetDrillSize().y) / 2))

    r = mm(VIA_D / 2 + MARGIN)
    edge = board.GetBoardEdgesBoundingBox()
    added = {n: 0 for n in nets}

    def clear(x, y, yards_too=True):
        pt = pcbnew.VECTOR2I(x, y)
        if yards_too and any(yd.Contains(pt) for yd in yards):
            return False
        lim = mm(VIA_DRILL / 2 + HOLE_GAP)
        return all((x - hx) ** 2 + (y - hy) ** 2 > (lim + hr) ** 2 for hx, hy, hr in holes)

    def place(n, x, y):
        v = pcbnew.PCB_VIA(board)
        v.SetLayerPair(F, B)
        v.SetPosition(pcbnew.VECTOR2I(x, y))
        v.SetWidth(mm(VIA_D))
        v.SetDrill(mm(VIA_DRILL))
        v.SetNet(board.FindNet(n))
        board.Add(v)
        holes.append((x, y, mm(VIA_DRILL / 2)))
        added[n] += 1

    def fills(n, layer):
        s = pcbnew.SHAPE_POLY_SET()
        for z in zones[n]:
            if z.IsOnLayer(layer):
                s.Append(z.GetFilledPolysList(layer))
        return s

    for n in nets:
        ff, bf = fills(n, F), fills(n, B)
        x0, y0 = edge.GetLeft(), edge.GetTop()
        step = mm(PITCH)
        y = y0 + step // 2
        while y < edge.GetBottom():
            x = x0 + step // 2
            while x < edge.GetRight():
                if fits(ff, x, y, r) and fits(bf, x, y, r) and clear(x, y):
                    place(n, x, y)
                x += step
            y += step

    # islands still on their own
    filler.Fill(board.Zones())
    for n in nets:
        net = board.FindNet(n).GetNetCode()
        ff, bf = fills(n, F), fills(n, B)
        anchors = [(t.GetPosition().x, t.GetPosition().y) for t in board.GetTracks()
                   if t.GetClass() == "PCB_VIA" and t.GetNetCode() == net]
        anchors += [(p.GetPosition().x, p.GetPosition().y) for fp in board.GetFootprints() for p in fp.Pads()
                    if p.GetNetCode() == net and p.GetDrillSize().x]
        for layer_fill, other in ((bf, ff), (ff, bf)):
            for i in range(layer_fill.OutlineCount()):
                if any(layer_fill.Contains(pcbnew.VECTOR2I(ax, ay), i) for ax, ay in anchors):
                    continue
                bb = layer_fill.Outline(i).BBox()
                done = False
                yy = bb.GetTop()
                while yy < bb.GetBottom() and not done:
                    xx = bb.GetLeft()
                    while xx < bb.GetRight():
                        if (layer_fill.Contains(pcbnew.VECTOR2I(xx, yy), i) and fits(layer_fill, xx, yy, r)
                                and fits(other, xx, yy, r) and clear(xx, yy, yards_too=False)):
                            place(n, xx, yy); anchors.append((xx, yy)); done = True
                            break
                        xx += mm(0.5)
                    yy += mm(0.5)

    filler.Fill(board.Zones())
    pcbnew.SaveBoard(BOARD, board)
    print("stitching vias added:", ", ".join(f"{n} {k}" for n, k in added.items()))


if __name__ == "__main__":
    main()
