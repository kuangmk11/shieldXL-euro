# PCM3060 driver for Moirae

Moirae's codec is a TI PCM3060 (U1) in place of the norns shield's CS4270,
which Cirrus ended in 2023. Like the CS4270 on the shield, it is the I2S clock
master, running off the board's 12.288 MHz crystal at 48 kHz.

The PCM3060's ADC and DAC each have their own BCK / LRCK pins; on Moirae they
share the Pi's one pair, so the DAC drives the clocks and the ADC follows. The
kernel's driver gives both halves the link's one master / slave setting, so
this is the kernel's own driver with one addition, the device-tree flag
`moirae,adc-clock-consumer`, built as its own module (`snd-soc-pcm3060-moirae`,
compatible `moirae,pcm3060`) so it never clashes with the stock one.

## Install (on the Pi)

    sudo apt install raspberrypi-kernel-headers   # headers for `uname -r`
    ./build.sh                                     # fetch, patch, build, install
    cd ../../install/boot/overlays
    dtc -@ -I dts -O dtb -o moirae-pcm3060.dtbo moirae-pcm3060-overlay.dts
    sudo cp moirae-pcm3060.dtbo /boot/overlays/

then in `/boot/config.txt` replace `dtoverlay=monome-snd-4270` with
`dtoverlay=moirae-pcm3060`, and reboot. `aplay -l` should list a card named
Moirae.

`build.sh` takes the driver from the Raspberry Pi kernel branch matching the
running kernel (`rpi-X.Y.y`; override with `BRANCH=`), patches it with
`patch_driver.py`, and installs into `/lib/modules/$(uname -r)/extra`. A norns
image runs monome's kernel build; if its headers aren't packaged, build against
a matching kernel tree with `make KDIR=...`.

## Not yet tested on hardware

Written from the PCM3060 datasheet (SLAS533B) and the kernel driver; check on
the first board:

- `i2cdetect -y 1` shows 0x46 (needs GPIO17 high: the overlay's hog).
- Playback and capture at 48 kHz together (jack duplex). The DAC is the clock
  source, so capture alone has no clocks.
- Levels: 13.3 Vpp at an input jack is the ADC's full scale; full-scale
  playback is about 10 Vpp at the output jacks.
