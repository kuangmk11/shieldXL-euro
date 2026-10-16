# shieldXL-euro

A 20 HP Eurorack module from okyeron / denki-oto's
[shieldXL](https://github.com/okyeron/shieldXL), itself a remix of monome's
[norns shield](https://github.com/monome/norns-shield). GPL-3.0, as both are.

The original KiCad project, `../ShieldXL-M-20230615`, is left as it is, so
upstream fixes still merge. This copy changes only what Eurorack needs.

## What changes

| | shieldXL | shieldXL-euro |
|---|---|---|
| audio | 4 x 6.35 mm, line level | 4 x 3.5 mm (Thonkiconn); TL074 stages scale 10 Vpp modular to the codec and back |
| MIDI | PJ-320B TRS jacks, Type A/B slide switch | PJ366ST stereo Thonkiconns; A/B by two solder jumpers, Type A as made |
| Pi power | the Pi's own USB | USB-C on the panel, through a polyfuse and TVS onto +5V. The Pi never runs from the rack, so a rack power cycle cannot catch it mid-write |
| rack power | - | 10-pin header, ±12 V for the op-amps only, reverse protected |
| USB host | the Pi's own ports | three USB-A sockets on the panel, each cabled from a Pi port |
| headphones | - | none: the outputs go to the rack |

Codec, display, keys, encoders and the MIDI circuit are shieldXL's, unchanged.

## Levels

- **In:** 100k into an inverting stage, gain −0.40, then shieldXL's own
  4.99k / 10k divider. A 10 Vpp signal reaches the CS4270 at about its
  2.7 Vpp full scale; hotter signals clip in the codec, not the op-amp.
- **Out:** shieldXL's output filter into a non-inverting stage, gain 3.49,
  then 1k. Codec full scale, about 2.85 Vpp, leaves as about 10 Vpp.
- **Phase:** the input stage inverts. Fine for audio; flip the sign in
  software if a CV use needs it.

## Pi power

The Pi is powered through the 40-pin header, not its own USB-C / micro-USB
port, so nothing plugs into that port and no right-angle adapter is needed.
J108 on the panel feeds F101 and D103 onto `+5V`, and `+5V` is header pins 2
and 4 (X1), as on shieldXL.

- **Protection.** Header power bypasses the Pi's own input protection; F101
  and D103 stand in for it.
- **Voltage drop.** The Pi flags undervoltage at about 4.63 V. A 3 A 1812
  polyfuse drops around 0.1 V at 2-2.5 A, before the cable and connector.
  With a marginal supply that can trip the warning; a lower-resistance fuse
  or an eFuse would leave more margin.
- **Two supplies.** Plugging the Pi's own power port in while J108 is live
  ties the two supplies together. It can't be reached in a rack; on the
  bench, use one or the other. An ideal-diode controller on J108 would make
  it safe.
- **Pi 5.** Powered from the header it cannot negotiate USB PD, and limits
  its USB ports to 600 mA in total unless `usb_max_current_enable=1` is set
  in `config.txt`. That matters with three USB-A sockets on the panel.
  shieldXL's images are for the Pi 4.

## Files

    shieldXL-euro.kicad_sch          root: the two shield sheets and eurorack.kicad_sch
    norns-shield-210330_1/_2.kicad_sch   shieldXL's sheets, desktop I/O removed
    eurorack.kicad_sch               the Eurorack I/O - generated, do not edit by hand
    tools/strip_shield_io.py         removes the 6.35 mm jacks, PJ-320Bs and slide switch
    tools/make_eurorack_sheet.py     writes eurorack.kicad_sch and hooks it into the root
    tools/schlib.py                  pin positions and wire checks for the scripts

The two shield sheets are joined to the Eurorack sheet by global labels:

- **Audio:** `IN_L_LINE`, `IN_R_LINE`, `OUT_L_LINE`, `OUT_R_LINE`.
- **MIDI:** `MIDI_OUT_SRC`, `MIDI_OUT_SNK`, `MIDI_IN_TIP`, `MIDI_IN_RING`.
- **Power and grounds:** the shield's own `+5V`, `GND` and `AGND` symbols.

The panel layout is in the Missing Mile Modular repo
(`ShieldXL Euro/tools/build_panel.py`). The board will be placed to its holes.

## Checked

- **Netlist:**
  - Removing the desktop I/O changed no other connection. Every shield net
    keeps exactly its pins, less the removed parts'.
  - The new sheet's cross-sheet nets land on the parts named above.
- **ERC:** 34 findings, against the original's 47 (`kicad-cli sch erc`,
  KiCad 10; unchanged by the Corone jacks and headers).
  - 16 of the original's are gone with the parts that caused them.
  - 4 are new: two net-name aliases (`TIP1_5` / `RING1_4` now also carry the
    global `MIDI_OUT_*` names), and AGND / GND "not driven". That is the
    same kind of finding the original has on its Eagle-era power pins.
  - The rest are inherited from the original.

## Not done yet

- **The board.** The outline is drawn (`tools/make_outline.py`, run with
  KiCad's Python): 98 x 108 mm behind the 20 HP panel, with the panel, the
  display and the Pi traced on User.1-4. shieldXL's desktop layout sits
  160 mm aside as a stash for Update PCB. The panel parts and the Pi are
  placed and locked by `tools/place_panel_parts.py`; the panel, artwork
  included, is on User.1 (back artwork on User.5). The
  stack, front to back: panel, display on standoffs behind the window, main
  board, Pi 4 on the back, upside down as on MONOFA (extra-tall header,
  about 20 mm standoffs). The 20 mm, main board's back to the Pi's PCB, lets
  the Pi's USB stacks (16 mm) clear the SMD parts under them by 2 mm; it is
  modelled (`tools/set_3d_models.py`, on X1) as an 8.5 mm 2x20 socket on the
  board with a 2x20 stacking header in it, then the Pi's 2.5 mm header base.
- **The Pi lies landscape, header along the top**, behind the display and
  clear of the controls. That is why the module is 20 HP: 85 mm of Pi, its
  ports, a USB adapter and the microSD card come to about 96 mm, more than
  18 HP's 91.3. Two small adapter boards plug into its USB stacks and
  carry the four ports to J112 / J113 on 2 x 5 IDC ribbons
  (`../usb-adapter`). Only its two holes by the header are screwed down
  (footprint `MMM:RASPI_BOARD_B+_UPPER_HOLES`): the other two land on K1's
  and E2's pins, so those corners stand on 3D-printed feet fixed to the Pi,
  drawn on User.3. Keys are C&K D6R00 (`MMM:SW_CK_D6R`). The
  panel is drawn in the Missing Mile Modular repo and named Moirae there.
- **Corone (crow).** Two CV inputs and four CV outputs, the six jacks in the
  panel's CORONE outline. A daughterboard running monome's own crow
  firmware, on one 2 x 10 header on the back of the main board, lower half,
  below the Pi; USB to norns through the Pi's fourth port. Spec and
  schematic in `../corone/`. The main board's side is in the Eurorack sheet:
  J115-J120 jacks, J121 header, J122 ii; its USB comes through J113.
- **A vertical USB-C receptacle.** KiCad's library has none. J108 has no
  footprint until a part is chosen.
- **Keys.** SW1-SW3 are still shieldXL's Choc / MX key footprints; the
  panel is drawn for 9.3 mm round caps (C&K D6 style).
- **USB-A cable headers.** USB on a 4-pin JST PH is fine for full speed;
  keep the cables short. The plugs into the Pi's own USB-A ports stick out
  sideways and cost depth and side clearance behind the panel. Plan the
  layout around a small adapter board or flex with low-profile right-angle
  plugs, carried back to the main board.
