#!/usr/bin/env bash
# Build and install Moirae's PCM3060 driver on the Pi, for the running kernel.
# Needs the kernel headers for `uname -r` (/lib/modules/$(uname -r)/build).
set -euo pipefail
cd "$(dirname "$0")"
KVER=$(uname -r)
BRANCH=${BRANCH:-rpi-$(echo "$KVER" | cut -d. -f1,2).y}
BUILD=build-$KVER
rm -rf "$BUILD" && mkdir "$BUILD" && cp Makefile patch_driver.py "$BUILD"/ && cd "$BUILD"
for f in pcm3060.c pcm3060.h pcm3060-i2c.c; do
    curl -fsSL -o "$f" "https://raw.githubusercontent.com/raspberrypi/linux/$BRANCH/sound/soc/codecs/$f"
done
python3 patch_driver.py
make
sudo install -D -m 644 snd-soc-pcm3060-moirae.ko "/lib/modules/$KVER/extra/snd-soc-pcm3060-moirae.ko"
sudo depmod -a
echo "installed snd-soc-pcm3060-moirae for $KVER"
