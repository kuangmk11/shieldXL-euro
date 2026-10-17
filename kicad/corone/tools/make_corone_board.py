"""Create corone.kicad_pcb: the outline and the board frame, ready for Update
PCB from Schematic. Run with KiCad's own Python, once:

    "/mnt/g/Program Files/KiCad/10.0/bin/python.exe" tools/make_corone_board.py

Corone plugs onto the main board's J121 (2 x 10 pin header on its back, lower
left), parallel to it, about 11 mm behind: an 8.5 mm socket (J1) on Corone's
B side, every other part on its F side, facing the module's rear - single-
sided SMD, and the TC2030, buttons and debug header reachable from behind.

Frame: Corone is seen from its F side, the main board's back, so its x runs
mirrored. A main-board point (x, y) is Corone point (MIRROR - x, y); with
MIRROR = 266.65 the two outlines share x 101.65..165 and y. J121's pin 1 at
main (103.36, 126.3) is Corone (163.29, 126.3), where J1's pin 1 goes.

Outline: below the Pi (whose USB stacks come within 4 mm of the main board's
back, so Corone keeps clear of its whole footprint), left of J101 and the Pi's
USB ribbons, to the main board's bottom edge.
"""

import os

import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(HERE, "corone.kicad_pcb")
MIRROR = 266.65
X0, X1, Y0, Y1, R = 101.65, 165.0, 98.5, 148.25, 1.0
J1_PIN1 = (MIRROR - 103.36, 126.3)


def mm(v):
    return pcbnew.FromMM(v)


def main():
    if os.path.exists(BOARD):
        raise SystemExit("corone.kicad_pcb exists - this only creates it")
    b = pcbnew.BOARD()
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_RECTANGLE)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.1))
    s.SetStart(pcbnew.VECTOR2I(mm(X0), mm(Y0)))
    s.SetEnd(pcbnew.VECTOR2I(mm(X1), mm(Y1)))
    s.SetCornerRadius(mm(R))
    b.Add(s)
    # J1's pin 1, marked for placement
    t = pcbnew.PCB_TEXT(b)
    t.SetText("J1 pin 1 here (mates J121)")
    t.SetLayer(pcbnew.Cmts_User)
    t.SetTextSize(pcbnew.VECTOR2I(mm(1), mm(1)))
    t.SetPosition(pcbnew.VECTOR2I(mm(J1_PIN1[0] - 12), mm(J1_PIN1[1] + 3)))
    b.Add(t)
    c = pcbnew.PCB_SHAPE(b)
    c.SetShape(pcbnew.SHAPE_T_CIRCLE)
    c.SetLayer(pcbnew.Cmts_User)
    c.SetWidth(mm(0.1))
    c.SetCenter(pcbnew.VECTOR2I(mm(J1_PIN1[0]), mm(J1_PIN1[1])))
    c.SetEnd(pcbnew.VECTOR2I(mm(J1_PIN1[0] + 1.2), mm(J1_PIN1[1])))
    b.Add(c)
    ds = b.GetDesignSettings()
    ds.m_MinClearance = mm(0.2)
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_HoleClearance = mm(0.25)
    ds.m_ViasMinSize = mm(0.5)
    pcbnew.SaveBoard(BOARD, b)
    print(f"corone.kicad_pcb: {X1 - X0:.2f} x {Y1 - Y0:.2f} mm; J1 pin 1 at {J1_PIN1}")


if __name__ == "__main__":
    main()
