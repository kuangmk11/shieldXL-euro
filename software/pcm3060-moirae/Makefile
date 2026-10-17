# Out-of-tree build of Moirae's PCM3060 driver (see build.sh).
obj-m := snd-soc-pcm3060-moirae.o
snd-soc-pcm3060-moirae-objs := pcm3060.o pcm3060-i2c.o

KDIR ?= /lib/modules/$(shell uname -r)/build

all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
