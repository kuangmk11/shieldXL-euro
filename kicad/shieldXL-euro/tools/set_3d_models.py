"""Give the board's footprints 3D models: shieldXL's Eagle-imported parts get
KiCad's stock models, turned to match their pads (worked out by matching pad
positions against the stock footprints), and broken paths are repointed.
Run with KiCad's own Python, the board closed:

    "/mnt/g/Program Files/KiCad/10.0/bin/python.exe" tools/set_3d_models.py

Writes both the footprint libraries (ShieldXL.pretty, MMM.pretty) and the
copies on the board, which keeps its own.
"""

import os
import re

import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(HERE, "shieldXL-euro.kicad_pcb")
K = "${KICAD10_3DMODEL_DIR}/"
P = "${KIPRJMOD}/3dmodels/"
H = "${KIPRJMOD}/3d/"                 # models that come with the MMM house library

# (library, footprint): (model, z rotation in deg[, offset x y z in mm, y up]). The angle is how far the
# Eagle footprint's pads stand turned (counterclockwise, seen from the front)
# from the stock footprint's; KiCad turns a model by its rotate z the other way,
# so the model takes the negative (checked against pin 1 on U1 in a render).
MODELS = {
    ("ShieldXL", "R0603"): (K + "Resistor_SMD.3dshapes/R_0603_1608Metric.step", 0),
    ("ShieldXL", "C0603"): (K + "Capacitor_SMD.3dshapes/C_0603_1608Metric.step", 0),
    ("ShieldXL", "C0805"): (K + "Capacitor_SMD.3dshapes/C_0805_2012Metric.step", 0),
    ("ShieldXL", "C1206"): (K + "Capacitor_SMD.3dshapes/C_1206_3216Metric.step", 0),
    ("ShieldXL", "L0805"): (K + "Inductor_SMD.3dshapes/L_0805_2012Metric.step", 0),
    ("ShieldXL", "CHIPLED_0603_NOOUTLINE"): (K + "LED_SMD.3dshapes/LED_0603_1608Metric.step", -270),
    ("ShieldXL", "TSSOP24"): (K + "Package_SO.3dshapes/TSSOP-24_4.4x7.8mm_P0.65mm.step", -90),
    ("ShieldXL", "SSOP5"): (K + "Package_TO_SOT_SMD.3dshapes/SOT-23-5.step", -90),
    ("ShieldXL", "SSOP-8_3.9x5.05mm_P1.27mm"): (K + "Package_SO.3dshapes/SSOP-8_3.9x5.05mm_P1.27mm.step", 0),
    # ASFL1 oscillator, 5.0 x 3.2: the same body as EuroQuartz's XO53
    ("ShieldXL", "ASF"): (K + "Oscillator.3dshapes/Oscillator_SMD_EuroQuartz_XO53-4Pin_5.0x3.2mm.step", 0),
    ("ShieldXL", "PEC11RN"): (P + "SW-PEC11R-4215F-N0024.stp", 0),
    # C&K's own model; its pins sit on the footprint's 5 mm square, z 0 at the board
    ("MMM", "SW_CK_D6R"): (H + "SW-D6R00-F2-LFS.stp", 0),
    # Molex's own models (the house library carries them). The USB-A's shell
    # flange sits at z -5.0 and its pins on y -1.9 about its centre; pad 1 is
    # 3.5 left of the middle. The USB-C stands on its z axis with the legs' tips
    # at -5.22 and L = 1.4 below the board, so the board is at -3.82 (shell top
    # then 9.04 up, as drawn); it is centred on the footprint's origin.
    ("Connector_USB", "USB_A_Molex_105057_Vertical"): (H + "1050570001.stp", 0, (3.5, 1.9, 5.0)),
    ("MMM", "USB_C_Receptacle_Molex_2047110001_Vertical"): (H + "2047110001.stp", 0, (0, 0, 3.82)),
    # KiCad 10 ships no 1812 fuse model; the 1812 resistor is the same box
    ("Fuse", "Fuse_1812_4532Metric"): (K + "Resistor_SMD.3dshapes/R_1812_4532Metric.step", 0),
}


# The Pi stack, on X1: the Pi hangs upside down 20 mm (STACK) behind the board's
# back, far enough for its USB stacks (16 mm) to clear the SMD parts under them
# (2 mm at most) with 2 mm to spare. Modelled as a standard 8.5 mm 2x20 socket
# on the board with a 2x20 stacking header (8.5 mm body) in it, seated 0.5 short,
# then the Pi's own 2.5 mm header base. Seen from the front the socket's pin 2
# is above pin 1 and the rows run right, so the stock model is flipped about x
# and turned about z (KiCad turns models the opposite way to footprints).
# In the Pi model the Pi's PCB top is at y 1.5 and the parts stand along +y.
STACK, BOARD_T, SOCKET_H, SEAT_GAP, PI_HEADER_BASE = 20.0, 1.6, 8.5, 0.5, 2.5
SOCKET = K + "Connector_PinSocket_2.54mm.3dshapes/PinSocket_2x20_P2.54mm_Vertical.step"
PIN1 = (8.37, 51.23)                  # X1's pad 1, y up
MULTI = {
    # the MIDI LEDs stand on spacers so their flange (z 3-4 in the model) meets
    # the panel's back at 10.0; -1.27 in x as the footprint's own note explains
    ("MMM", "LED_3mm_PadsAC"): [
        (K + "LED_THT.3dshapes/LED_D3.0mm.step", (0, 0, 0), (-1.27, 0, 6.0)),
    ],
    # JAE's model (SamacSys) stands on its y axis, legs at -y, centred like
    # KiCad's footprint; the board is 7.3 up its legs, so the top lands 12.0 up
    ("Connector_USB", "USB_C_Receptacle_JAE_DX07S024WJ1R350"): [
        (H + "DX07S024WJ1R350.stp", (0, 0, 0), (0, 0, 7.3)),
    ],
    ("MMM", "RASPI_BOARD_B+_UPPER_HOLES"): [
        (P + "RASPBERRY PI 4B_4GB.STEP", (-90, 0, 0), (42.5, 28, -(BOARD_T + STACK + 1.5))),
        (SOCKET, (180, 0, 90), (*PIN1, -BOARD_T)),
        (SOCKET, (180, 0, 90), (*PIN1, -(BOARD_T + SOCKET_H + SEAT_GAP))),
    ],
}
assert abs(SOCKET_H * 2 + SEAT_GAP + PI_HEADER_BASE - STACK) < 1e-9


def model_block(path, rot, off=(0, 0, 0), indent="\t"):
    i, j = indent, indent + "\t"
    r = rot if isinstance(rot, tuple) else (0, 0, rot)
    return (f'{i}(model "{path}"\n{j}(offset\n{j}\t(xyz {off[0]:g} {off[1]:g} {off[2]:g})\n{j})\n{j}(scale\n{j}\t(xyz 1 1 1)\n{j})\n'
            f'{j}(rotate\n{j}\t(xyz {r[0]:g} {r[1]:g} {r[2]:g})\n{j})\n{i})\n')


def strip_models(text):
    out, i = [], 0
    while True:
        j = text.find("(model ", i)
        if j < 0:
            out.append(text[i:])
            return "".join(out)
        k = text.rfind("\n", 0, j) + 1          # start of its line
        depth, n = 0, j
        while True:
            c = text[n]
            if c == '"':
                n = text.index('"', n + 1)
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            n += 1
        end = text.find("\n", n) + 1
        out.append(text[i:k])
        i = end


def fix_library():
    done = []
    entries = {k: [(p, r, o[0] if o else (0, 0, 0))] for k, (p, r, *o) in MODELS.items()}
    entries.update(MULTI)
    for (lib, name), models in entries.items():
        f = os.path.join(HERE, f"{lib}.pretty", f"{name}.kicad_mod")
        if not os.path.exists(f):
            continue
        t = strip_models(open(f, newline="").read()).rstrip()
        assert t.endswith(")")
        t = t[:-1].rstrip("\n") + "\n" + "".join(model_block(p, r, o, "  ") for p, r, o in models) + ")\n"
        open(f, "w", newline="").write(t)
        done.append(name)
    return done


def fix_board():
    board = pcbnew.LoadBoard(BOARD)
    n = 0
    for fp in board.GetFootprints():
        fid = fp.GetFPID()
        key = (fid.GetLibNickname().wx_str(), fid.GetLibItemName().wx_str())
        if key in MULTI:
            models = MULTI[key]
        elif key in MODELS:
            path, rot, *off = MODELS[key]
            models = [(path, (0, 0, rot), off[0] if off else (0, 0, 0))]
        else:
            continue
        fp.Models().clear()
        for path, rot, off in models:
            m = pcbnew.FP_3DMODEL()
            m.m_Filename = path
            m.m_Rotation = pcbnew.VECTOR3D(*rot)
            m.m_Offset = pcbnew.VECTOR3D(*off)
            fp.Models().push_back(m)
        n += 1
    pcbnew.SaveBoard(BOARD, board)
    return n


if __name__ == "__main__":
    lock = os.path.join(HERE, "~" + os.path.basename(BOARD) + ".lck")
    if os.path.exists(lock):
        raise SystemExit("the board is open in KiCad (lock file found): save, close it, then run again")
    print("library:", ", ".join(fix_library()))
    print("board footprints given models:", fix_board())
