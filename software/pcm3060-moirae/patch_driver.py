#!/usr/bin/env python3
"""Turn the kernel's PCM3060 driver (pcm3060.c, pcm3060.h, pcm3060-i2c.c in
the current directory) into Moirae's copy:

- DT flag "moirae,adc-clock-consumer": the ADC stays a clock consumer (slave)
  whatever the link asks. Moirae's ADC and DAC share one BCK / LRCK pair, so
  the DAC is the clock provider off the 12.288 MHz crystal and the ADC
  listens; the stock driver gives both DAIs the link's single setting.
- its own compatible ("moirae,pcm3060") and driver name, and no exported
  symbols, so it builds as one module that can sit beside the stock one.
"""
import re

h = open("pcm3060.h").read()
h = h.replace("\tu8 out_se: 1;", "\tu8 out_se: 1;\n\tu8 adc_consumer: 1;", 1)
assert "adc_consumer" in h, "pcm3060.h: struct layout changed"
open("pcm3060.h", "w").write(h)

c = open("pcm3060.c").read()
old = "\tcase SND_SOC_DAIFMT_CBP_CFP:\n\t\tpriv->dai[dai->id].is_provider = true;\n"
new = ("\tcase SND_SOC_DAIFMT_CBP_CFP:\n"
       "\t\t/* Moirae: the ADC listens to the DAC's clocks on the shared bus */\n"
       "\t\tpriv->dai[dai->id].is_provider =\n"
       "\t\t\t!(dai->id == PCM3060_DAI_ID_ADC && priv->adc_consumer);\n")
assert old in c, "pcm3060.c: set_fmt changed"
c = c.replace(old, new, 1)
old = '\tpriv->out_se = of_property_read_bool(np, "ti,out-single-ended");\n'
assert old in c, "pcm3060.c: DT parsing changed"
c = c.replace(old, old + '\tpriv->adc_consumer = of_property_read_bool(np, "moirae,adc-clock-consumer");\n', 1)
c = re.sub(r"^EXPORT_SYMBOL[^\n]*\n", "", c, flags=re.M)
c = c.replace('MODULE_DESCRIPTION("PCM3060 codec driver");', 'MODULE_DESCRIPTION("PCM3060 codec driver, Moirae (ADC clock consumer)");')
open("pcm3060.c", "w").write(c)

i = open("pcm3060-i2c.c").read()
i = i.replace('"ti,pcm3060"', '"moirae,pcm3060"').replace('.name = "pcm3060"', '.name = "pcm3060-moirae"')
i = i.replace('{ "pcm3060", 0 }', '{ "pcm3060-moirae", 0 }')
i = re.sub(r"^MODULE_(DESCRIPTION|AUTHOR|LICENSE)[^\n]*\n", "", i, flags=re.M)
assert "moirae,pcm3060" in i, "pcm3060-i2c.c: of_match changed"
open("pcm3060-i2c.c", "w").write(i)
print("patched")
