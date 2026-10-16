# Pi USB adapter

Brings the Pi 4's four USB ports to Moirae's main board. The Pi lies upside
down on the main board's back, ports toward the right edge; a small board
stands at each of its two USB stacks with two vertical male USB-A plugs, one
per port, and a 2 x 5 IDC whose ribbon runs behind the Pi down to the main
board (J112 for the stack beside Ethernet, J113 for the outer one). The two
boards are identical.

    usb-adapter.kicad_sch / .kicad_pcb    generated - do not edit by hand
    usb-adapter.pretty                    the plug footprint, generated
    tools/make_usb_adapter.py             writes all of it (KiCad's Python)

    "/mnt/g/Program Files/KiCad/10.0/bin/python.exe" tools/make_usb_adapter.py

Board: 17.2 x 40 mm, standing at the port faces, from 5.3 to 45.3 mm off the
main board's back. The plugs face the Pi; so does the IDC, above the Pi's
underside, its ribbon running behind the Pi. ERC clean; DRC shows only the
unrouted connections - routing waits for the plug part.

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

- **The plug.** `USB_A_Plug_Vertical` is a placeholder in the common vertical
  USB-A pattern: contacts 2.5 / 2.0 / 2.5, 0.92 mm holes, 2.1 mm off the
  centre line; shell legs 13.3 apart, 2.3 mm holes, on it. Redraw it from
  the chosen part's drawing. A USB-A plug fits one way up: check which side
  its insert sits on against the Pi's ports.
- **The plug spacing.** `PORT_ZC`, each port's centre above the Pi's PCB, is
  a placeholder (4.3 and 11.7). The Pi's drawing gives only the stack's
  16 mm; measure it.
- **The stack height.** `H`, the Pi's PCB above the main board's back, is
  20 mm, set by the 40-pin header and standoffs chosen for the main board.
