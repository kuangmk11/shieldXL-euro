#!/bin/sh
# Export the Corone daughterboard (../corone) as a STEP model for the main
# board's 3D view: COR1 carries it where it plugs onto J121.
# Corone's x is the main board's mirrored (x' = 266.65 - x) and it hangs
# behind the main board turned over, so: origin at Corone (165, 98.5), which
# is main (101.65, 98.5), where COR1 sits; turned 180 deg about y; its J1 side
# at z -12.6 - the main board's back (-1.6), J121's 2.5 mm base, J1's 8.5 mm
# socket. Rerun as Corone's layout grows.
set -e
HERE=$(cd "$(dirname "$0")/.." && pwd)
CORONE="$HERE/../corone/corone.kicad_pcb"
KICAD_CLI=${KICAD_CLI:-"/mnt/g/Program Files/KiCad/10.0/bin/kicad-cli.exe"}
"$KICAD_CLI" pcb export step --user-origin 165x98.5mm -f \
    -o "$(wslpath -w "$HERE/3d/Corone.step")" "$(wslpath -w "$CORONE")"
