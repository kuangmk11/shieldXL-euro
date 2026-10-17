"""Place every panel-mounted part on the main board at its hole in the Moirae
panel, and the Pi where the outline drew it. Run with KiCad's own Python,
after Update PCB from Schematic has brought the parts in:

    "/mnt/g/Program Files/KiCad/10.0/bin/python.exe" tools/place_panel_parts.py

Positions come from the panel builder itself (build_panel.py in the Missing
Mile Modular repo), so a change to the panel moves the parts with it. The board
shares the panel's frame: panel (x, y) is board (100 + x, 30 + y).

The board must not be open in KiCad: the script stops if it finds KiCad's
lock file, rather than have an open session save over it.
"""

import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.environ.get("MOIRAE_BOARD", os.path.join(HERE, "shieldXL-euro.kicad_pcb"))
PANEL_TOOLS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "Missing Mile Modular", "ShieldXL Euro", "tools"))
OX, OY = 100.0, 30.0
sys.path.insert(0, PANEL_TOOLS)
import build_panel as P      # noqa: E402
import panel_lib as PL       # noqa: E402

# panel name -> board reference
REF = {"K1": "SW1", "K2": "SW2", "K3": "SW3", "E1": "E1", "E2": "E2", "E3": "E3",
       "I/1": "J115", "I/2": "J116", "O/1": "J117", "O/2": "J118", "O/3": "J119", "O/4": "J120",
       "I/L": "J102", "I/R": "J103", "M/I": "J106", "M/O": "J107", "O/L": "J104", "O/R": "J105",
       "USB 1": "J109", "USB 2": "J110", "USB 3": "J111", "USB-C power": "J108",
       "MIDI in LED": "D1", "MIDI out LED": "D2"}

# where each footprint's shaft (or opening) centre sits from its origin, at 0 deg
CENTRE = {"Jack_3.5mm_QingPu_WQP-PJ398SM_Vertical_CircularHoles": (0.0, 6.48),
          "Jack_3.5mm_QingPu_WQP-PJ366ST_Vertical": (0.0, 0.0),
          "PEC11RN": (0.0, 0.0),
          "Choc_MX_combo": (0.0, 0.0),
          "SW_CK_D6R": (0.0, 0.0),
          "USB_C_Receptacle_Molex_2047110001_Vertical": (0.0, 0.0),
          "USB_C_Receptacle_JAE_DX07S024WJ1R350": (0.0, 0.0),
          "LED_3mm_PadsAC": (0.0, 0.0),
          "USB_A_Molex_105057_Vertical": (3.5, -2.38)}   # middle of its pads / body
# parts that stand turned on the board (deg); the rest sit at 0
ANGLE = {"USB_C_Receptacle_Molex_2047110001_Vertical": 90, "USB_C_Receptacle_JAE_DX07S024WJ1R350": 90}

# the display's FPC connector, on the back where shieldXL had it relative to the
# display module (see FPC_SLOT in tools/make_outline.py): its origin 40.540,
# 41.351 from the module's top-left corner, at 90 deg
FPC_REF, FPC_AT = "U$1", (40.540, 41.351)
DISP_X0, DISP_TOP = 101.3 / 2 - 82.0 / 2, 10.5
# the display module itself: a board-only footprint (no pads, not in the
# schematic) that carries its outline and 3D model, origin at its top-left
DISP_REF, DISP_FP = "DS1", "Display_NHD-2.7-12864WDW3"
# the panel itself, for the 3D view: board-only too, origin at its top-left
PNL_REF, PNL_FP = "PNL1", "Panel_Moirae"
# and Corone, behind the board on J121, for the 3D view: origin at its corner
COR_REF, COR_FP, COR_AT = "COR1", "Corone_Daughterboard", (101.65, 98.5)

# the Pi, as tools/make_outline.py draws it: its footprint's origin is the
# corner below the header, seen from the front
PI_REF = "X1"
PI_X0, PI_Y0, PI_W = 1.65 + 2.6, 10.25 + 0.5, 56.0


def mm(v):
    return pcbnew.FromMM(v)


def targets():
    out = {}
    for _, name, x, y, _ in P.DRAWN:
        out[P.__dict__.get("SHOWN", {}).get(name, name)] = (x, y)
    for what, x, y, _ in getattr(P, "LEDS", []):
        out[what] = (x, y)
    for r in PL.RECTS:
        if r[0] in REF:
            out[r[0]] = ((r[1] + r[3]) / 2, (r[2] + r[4]) / 2)
    return out


def main():
    lock = os.path.join(os.path.dirname(BOARD), "~" + os.path.basename(BOARD) + ".lck")
    if os.path.exists(lock):
        raise SystemExit("the board is open in KiCad (lock file found): save, close it, then run again")
    # KiCad's Python reads a footprint library only before it loads a board
    protos = {ref: (name, pcbnew.FootprintLoad(os.path.join(HERE, "MMM.pretty"), name))
              for ref, name in ((DISP_REF, DISP_FP), (PNL_REF, PNL_FP), (COR_REF, COR_FP))}
    board = pcbnew.LoadBoard(BOARD)
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    for ref, (name, proto) in protos.items():
        if ref not in fps:
            d = pcbnew.FOOTPRINT(proto)
            d.SetParent(board)
            d.SetFPID(pcbnew.LIB_ID("MMM", name))
            d.SetReference(ref)
            board.Add(d)
            fps[ref] = d
    placed, missing, unknown = [], [], []
    for name, (x, y) in targets().items():
        ref = REF.get(name)
        if ref is None:
            continue
        f = fps.get(ref)
        if f is None:
            missing.append(f"{ref} ({name})")
            continue
        fpname = f.GetFPID().GetLibItemName().wx_str() if hasattr(f.GetFPID().GetLibItemName(), "wx_str") else str(f.GetFPID().GetLibItemName())
        if fpname not in CENTRE:
            unknown.append(f"{ref} ({name}): footprint '{fpname or 'none'}'")
            continue
        if f.IsFlipped():
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        f.SetOrientationDegrees(ANGLE.get(fpname, 0))
        dx, dy = CENTRE[fpname]
        f.SetPosition(pcbnew.VECTOR2I(mm(OX + x - dx), mm(OY + y - dy)))
        f.SetLocked(True)
        placed.append(f"{ref} {name}")
    fpc = fps.get(FPC_REF)
    if fpc is not None:
        if not fpc.IsFlipped():
            fpc.Flip(fpc.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fpc.SetOrientationDegrees(90)
        fpc.SetPosition(pcbnew.VECTOR2I(mm(OX + DISP_X0 + FPC_AT[0]), mm(OY + DISP_TOP + FPC_AT[1])))
        fpc.SetLocked(True)
        placed.append(f"{FPC_REF} display FPC")
    else:
        missing.append(FPC_REF)
    d = fps[DISP_REF]
    d.SetOrientationDegrees(0)
    d.SetPosition(pcbnew.VECTOR2I(mm(OX + DISP_X0), mm(OY + DISP_TOP)))
    d.SetLocked(True)
    placed.append(f"{DISP_REF} display")
    p = fps[PNL_REF]
    p.SetOrientationDegrees(0)
    p.SetPosition(pcbnew.VECTOR2I(mm(OX), mm(OY)))
    p.SetLocked(True)
    placed.append(f"{PNL_REF} panel")
    c = fps[COR_REF]
    c.SetOrientationDegrees(0)
    c.SetPosition(pcbnew.VECTOR2I(mm(COR_AT[0]), mm(COR_AT[1])))
    c.SetLocked(True)
    placed.append(f"{COR_REF} Corone")
    pi = fps.get(PI_REF)
    if pi is not None:
        if pi.IsFlipped():
            pi.Flip(pi.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        pi.SetOrientationDegrees(0)
        pi.SetPosition(pcbnew.VECTOR2I(mm(OX + PI_X0), mm(OY + PI_Y0 + PI_W)))
        pi.SetLocked(True)
        placed.append(f"{PI_REF} Pi 4")
    else:
        missing.append(PI_REF)
    pcbnew.SaveBoard(BOARD, board)
    return placed, missing, unknown


if __name__ == "__main__":
    placed, missing, unknown = main()
    print(f"placed and locked {len(placed)}: " + ", ".join(placed))
    if missing:
        print("not on the board (run Update PCB from Schematic): " + ", ".join(missing))
    if unknown:
        print("no footprint to place by: " + "; ".join(unknown))
