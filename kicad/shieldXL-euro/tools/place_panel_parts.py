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
       "USB 1": "J109", "USB 2": "J110", "USB 3": "J111", "USB-C power": "J108"}

# where each footprint's shaft (or opening) centre sits from its origin, at 0 deg
CENTRE = {"Jack_3.5mm_QingPu_WQP-PJ398SM_Vertical_CircularHoles": (0.0, 6.48),
          "Jack_3.5mm_QingPu_WQP-PJ366ST_Vertical": (0.0, 0.0),
          "PEC11RN": (0.0, 0.0),
          "Choc_MX_combo": (0.0, 0.0),
          "SW_CK_D6R": (0.0, 0.0),
          "USB_A_Molex_105057_Vertical": (3.5, -2.38)}   # middle of its pads / body

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
    for r in PL.RECTS:
        if r[0] in REF:
            out[r[0]] = ((r[1] + r[3]) / 2, (r[2] + r[4]) / 2)
    return out


def main():
    lock = os.path.join(os.path.dirname(BOARD), "~" + os.path.basename(BOARD) + ".lck")
    if os.path.exists(lock):
        raise SystemExit("the board is open in KiCad (lock file found): save, close it, then run again")
    board = pcbnew.LoadBoard(BOARD)
    fps = {f.GetReference(): f for f in board.GetFootprints()}
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
        f.SetOrientationDegrees(0)
        dx, dy = CENTRE[fpname]
        f.SetPosition(pcbnew.VECTOR2I(mm(OX + x - dx), mm(OY + y - dy)))
        f.SetLocked(True)
        placed.append(f"{ref} {name}")
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
