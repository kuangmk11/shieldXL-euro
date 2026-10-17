#!/bin/sh
# Export the Pi USB adapter (../usb-adapter) as a STEP model for the main
# board's 3D view: USBA1 / USBA2 carry it at the Pi's two USB stacks.
# Origin at the adapter's (100, 100): u = 0 on its centre line, v = 0 level
# with the main board's back; the plug side at z 0. Rerun when the adapter
# changes.
set -e
HERE=$(cd "$(dirname "$0")/.." && pwd)
ADAPTER="$HERE/../usb-adapter/usb-adapter.kicad_pcb"
KICAD_CLI=${KICAD_CLI:-"/mnt/g/Program Files/KiCad/10.0/bin/kicad-cli.exe"}
"$KICAD_CLI" pcb export step --user-origin 100x100mm -f \
    -o "$(wslpath -w "$HERE/3d/USB_adapter.step")" "$(wslpath -w "$ADAPTER")"
