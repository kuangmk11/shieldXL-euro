# Pi USB adapter

Brings the Pi 4's four USB ports to Moirae's main board. The Pi lies upside
down on the main board's back, ports toward the right edge; a small board
stands at each of its two USB stacks with two vertical male USB-A plugs, one
per port, and a 2 x 5 IDC whose ribbon runs behind the Pi down to the main
board (J112 for the stack beside Ethernet, J113 for the outer one). The two
boards are identical.

    usb-adapter.kicad_sch                 generated - do not edit by hand
    usb-adapter.kicad_pcb                 routed by hand; the script only writes one if there is none
    usb-adapter.pretty                    the plug footprint, generated
    3d/USB_A_plug_placeholder.step        a 12 x 4.5 x 15 mm box standing in for the plug
    tools/make_usb_adapter.py             writes the rest (KiCad's Python)

In Moirae's 3D view, USBA1 / USBA2 on the main board carry this board as
../shieldXL-euro/3d/USB_adapter.step: rerun
../shieldXL-euro/tools/export_usb_adapter_step.sh after changing it.

    "/mnt/g/Program Files/KiCad/10.0/bin/python.exe" tools/make_usb_adapter.py

Board: 17.2 x 40 mm, standing at the port faces, from 5.3 to 45.3 mm off the
main board's back. The plugs face the Pi; so does the IDC, above the Pi's
underside, its ribbon running behind the Pi. Routed.

## IDC pinout, in ribbon order

| pin | | pin | |
|---|---|---|---|
| 1 | VBUS A | 2 | GND |
| 3 | D- A | 4 | D+ A |
| 5 | GND | 6 | GND |
| 7 | D- B | 8 | D+ B |
| 9 | GND | 10 | VBUS B |

A is the port nearer the Pi's PCB, B the further one. Each pair rides
between grounds.

## Before ordering

- **The plug.** A side-mount USB-A male, the "USB-71" (L = 15 mm short;
  Molex 48037 pattern), stood on its back end. `USB_A_Plug_Vertical` takes
  its four contact tails straight through, on the plug's centre line, in
  1.0 x 0.6 plated slots at the side-mount spacing (2.5 / 2.0 / 2.5), and its
  shell tabs in 0.9 x 4.0 plated slots at the jack's edges, 11.7 apart. The
  insert faces the Pi's PCB, where the Pi's tongue (along the top of each
  port) wants it. Its two bottom posts stand clear of the board; clip them
  or leave them. Check a sample's tails against the slots before ordering.
- **The plug spacing.** `PORT_ZC`, each port's centre above the Pi's PCB:
  3.49 and 12.63 (9.14 apart), read off the Pi 4 STEP model, where each
  opening is 5.1 mm tall with the port's tongue along its top. Check it with
  calipers on a real Pi.
- **The stack height.** `H`, the Pi's PCB above the main board's back, is
  20 mm, set by the 40-pin header and standoffs chosen for the main board.
