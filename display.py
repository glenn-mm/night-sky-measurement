# controls the night-sky-measurement display

#import and setup the display
import board
from adafruit_display_text.bitmap_label import Label
from terminalio import FONT
from i2cdisplaybus import I2CDisplayBus
import displayio
import adafruit_displayio_ssd1306

#### Start of Display Configuration ####
# create a main_group to hold anything we want to show on the display.
main_group = displayio.Group()
displayio.release_displays()
# Initialize I2C for display
i2c_d = board.I2C()  # uses board.SCL and board.SDA
display_bus = I2CDisplayBus(i2c_d, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=32)
#### End of Display Configuration ####

#### Start of text labels for output ####
# Create Label(s) to show the readings. If you have a very small
# display you may need to change to scale=1.
light_output_label = Label(FONT, text="")
infra_output_label = Label(FONT, text="")
mpsas_output_label = Label(FONT, text="")
# place the label(s) in the middle of the screen with anchored positioning
light_output_label.anchor_point = (0, 0)
light_output_label.anchored_position = (4, 0)
infra_output_label.anchor_point = (0, 0)
infra_output_label.anchored_position = (4, 11)
mpsas_output_label.anchor_point = (0, 0)
mpsas_output_label.anchored_position = (4, 22)
# add the label(s) to the main_group
main_group.append(light_output_label)
main_group.append(infra_output_label)
main_group.append(mpsas_output_label)
# set the main_group as the root_group of the built-in DISPLAY
display.root_group = main_group
#### End of text labels for output ####

def set_light(lstr):
    light_output_label.text = lstr

def set_ir(irstr):
    infra_output_label.text = irstr

def set_mpsas(mstr):
    mpsas_output_label.text = mstr

