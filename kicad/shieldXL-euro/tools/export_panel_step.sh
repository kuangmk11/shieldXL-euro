#!/bin/sh
# Export the Moirae panel (Missing Mile Modular repo) as a STEP model for the
# main board's 3D view: PNL1 carries it, 10.0 mm up, on the jacks' shoulders.
# Origin at the panel's top-left, (100, 30) in the panel file's frame, so it
# lands on the board as drawn. Rerun after the panel changes.
set -e
HERE=$(cd "$(dirname "$0")/.." && pwd)
PANEL="$HERE/../../../Missing Mile Modular/ShieldXL Euro/shieldxl_euro_panel.kicad_pcb"
KICAD_CLI=${KICAD_CLI:-"/mnt/g/Program Files/KiCad/10.0/bin/kicad-cli.exe"}
"$KICAD_CLI" pcb export step --user-origin 100x30mm --include-silkscreen --include-soldermask \
    --no-components -f -o "$(wslpath -w "$HERE/3d/Moirae_panel.step")" "$(wslpath -w "$PANEL")"
