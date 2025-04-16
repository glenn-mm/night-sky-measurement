# SPDX-FileCopyrightText: 2025 Glenn Henderson for Monterey Makers
# SPDX-FileCopyrightText: 2024 Tim Cocks for Adafruit Industries
# SPDX-FileCopyrightText: 2024 Jose D. Montoya
#
# SPDX-License-Identifier: MIT

# imports for basic functions
import time
import board
import math
# imports for dispaly
from adafruit_display_text.bitmap_label import Label
from terminalio import FONT
from i2cdisplaybus import I2CDisplayBus
import displayio
import adafruit_displayio_ssd1306
# import for lux device
import adafruit_tsl2591

# store a global calibration offset for tsl2591
_calibrationOffset = 0

# store gain conversion
gains = {0:adafruit_tsl2591.GAIN_LOW,
         1:adafruit_tsl2591.GAIN_MED,
         2:adafruit_tsl2591.GAIN_HIGH,
         3:adafruit_tsl2591.GAIN_MAX}
current_gain = 0

# store integration conversions (skipping 100ms)
integrations = {0:adafruit_tsl2591.INTEGRATIONTIME_200MS,
                1:adafruit_tsl2591.INTEGRATIONTIME_300MS,
                2:adafruit_tsl2591.INTEGRATIONTIME_400MS,
                3:adafruit_tsl2591.INTEGRATIONTIME_500MS,
                4:adafruit_tsl2591.INTEGRATIONTIME_600MS}
current_integration = 0

#### Start of Display Configuration ####
# create a main_group to hold anything we want to show on the display.
main_group = displayio.Group()
displayio.release_displays()
# Initialize I2C for display
i2c_d = board.I2C()  # uses board.SCL and board.SDA
display_bus = I2CDisplayBus(i2c_d, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=32)
#### End of Display Configuration ####

#### Start of Sensor Configuration ####
# Initialize I2C for sensor
i2c_s = board.STEMMA_I2C() # uses STEMMA connector
sensor = adafruit_tsl2591.TSL2591(i2c_s)
# start at low gain with 2nd shortest integration interval
sensor.gain = gains[current_gain]
sensor.integration_time = integrations[current_integration]
#### End of Sensor Configuration ####

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

# begin main loop
while True:
    # update the text of the label(s) to show the sensor readings
    # Infrared levels range from 0-65535 (16-bit)
    light_output_label.text = f"Total light:{sensor.lux:.1f}lux"
    infra_output_label.text = f"Infrared light:{sensor.infrared}"
    # calculate magnitudes per square arcsecond
    mpsas = 12.6 - 1.086 * math.log(sensor.visible) + _calibrationOffset;
    mpsas_output_label.text = f"MPSAS:{mpsas:.1f}"
    # adjust the gain if visible light is too low
    if sensor.visible < 128:
        if current_gain >= 3: #already at max gain, increase integration
            current_integration = current_integration + 1
            if current_integration >= 4:
                current_integration = 4
            sensor.integration_time = integrations[current_integration]
        else:
            current_gain = (current_gain + 1)
            sensor.gain = gains[current_gain]
    # wait for a bit
    time.sleep(0.5)

