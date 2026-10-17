#!/bin/sh
# Export the Moirae panel (Missing Mile Modular repo) as a STEP model for the
# main board's 3D view: PNL1 carries it, 10.0 mm up, on the jacks' shoulders.
# Origin at the panel's top-left, (100, 30) in the panel file's frame, so it
# lands on the board as drawn. The panel file has no stackup, which leaves the
# export in KiCad's default colours (translucent green, dark text); a temporary
# copy gets one - black core and solder mask (the mask exports translucent, so
# the core must be black too), white silkscreen - and is exported instead.
# Rerun after the panel changes.
set -e
HERE=$(cd "$(dirname "$0")/.." && pwd)
PANEL="$HERE/../../../Missing Mile Modular/ShieldXL Euro/shieldxl_euro_panel.kicad_pcb"
KICAD_CLI=${KICAD_CLI:-"/mnt/g/Program Files/KiCad/10.0/bin/kicad-cli.exe"}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
python3 - "$PANEL" "$TMP/panel.kicad_pcb" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding="utf-8").read()
stackup = """		(stackup
			(layer "F.SilkS" (type "Top Silk Screen") (color "White"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (color "Black") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 1" (type "core") (color "#141414FF") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.035))
			(layer "B.Mask" (type "Bottom Solder Mask") (color "Black") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
			(copper_finish "None")
			(dielectric_constraints no)
		)
"""
assert "(stackup" not in t and "\t(setup\n" in t
t = t.replace("\t(setup\n", "\t(setup\n" + stackup, 1)
open(dst, "w", encoding="utf-8").write(t)
PY
"$KICAD_CLI" pcb export step --user-origin 100x30mm --include-silkscreen --include-soldermask \
    --no-components -f -o "$(wslpath -w "$HERE/3d/Moirae_panel.step")" "$(wslpath -w "$TMP/panel.kicad_pcb")"
