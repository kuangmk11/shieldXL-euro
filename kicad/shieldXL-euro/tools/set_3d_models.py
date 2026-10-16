"""Give the board's footprints 3D models: shieldXL's Eagle-imported parts get
KiCad's stock models, turned to match their pads (worked out by matching pad
positions against the stock footprints), and broken paths are repointed.
Run with KiCad's own Python, the board closed:

    "/mnt/g/Program Files/KiCad/10.0/bin/python.exe" tools/set_3d_models.py

Writes both the footprint libraries (ShieldXL.pretty) and the copies on the
board, which keeps its own.
"""

import os
import re

import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(HERE, "shieldXL-euro.kicad_pcb")
K = "${KICAD10_3DMODEL_DIR}/"
P = "${KIPRJMOD}/3dmodels/"

# (library, footprint): (model, z rotation in deg). The angle is how far the
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
    # KiCad 10 ships no 1812 fuse model; the 1812 resistor is the same box
    ("Fuse", "Fuse_1812_4532Metric"): (K + "Resistor_SMD.3dshapes/R_1812_4532Metric.step", 0),
}


def model_block(path, rot, indent="\t"):
    i, j = indent, indent + "\t"
    return (f'{i}(model "{path}"\n{j}(offset\n{j}\t(xyz 0 0 0)\n{j})\n{j}(scale\n{j}\t(xyz 1 1 1)\n{j})\n'
            f'{j}(rotate\n{j}\t(xyz 0 0 {rot})\n{j})\n{i})\n')


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
    for (lib, name), (path, rot) in MODELS.items():
        f = os.path.join(HERE, f"{lib}.pretty", f"{name}.kicad_mod")
        if not os.path.exists(f):
            continue
        t = strip_models(open(f, newline="").read()).rstrip()
        assert t.endswith(")")
        t = t[:-1].rstrip("\n") + "\n" + model_block(path, rot, "  ") + ")\n"
        open(f, "w", newline="").write(t)
        done.append(name)
    return done


def fix_board():
    board = pcbnew.LoadBoard(BOARD)
    n = 0
    for fp in board.GetFootprints():
        fid = fp.GetFPID()
        key = (fid.GetLibNickname().wx_str(), fid.GetLibItemName().wx_str())
        if key not in MODELS:
            continue
        path, rot = MODELS[key]
        fp.Models().clear()
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = path
        m.m_Rotation = pcbnew.VECTOR3D(0, 0, rot)
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
