# SPDX-FileCopyrightText: 2025 Glenn Henderson for Monterey Makers (adapted from https://github.com/gshau/SQM_TSL2591)
# SPDX-FileCopyrightText: 2024 Tim Cocks for Adafruit Industries
# SPDX-FileCopyrightText: 2024 Jose D. Montoya
#
# SPDX-License-Identifier: MIT

# imports for basic functions
import sys
import time
import board
import math
import microcontroller
# import for lux device
import adafruit_tsl2591
# import display functions
import display

# store a global calibration offset for tsl2591
_calibrationOffset = 0

# store gain conversion
gains = {0:(adafruit_tsl2591.GAIN_LOW,  1.0),
         1:(adafruit_tsl2591.GAIN_MED,  25.0),
         2:(adafruit_tsl2591.GAIN_HIGH, 425.0),
         3:(adafruit_tsl2591.GAIN_MAX,  9876.0)}
current_gain = 0

# store integration conversions (skipping 100ms)
integrations = {0:(adafruit_tsl2591.INTEGRATIONTIME_200MS, 200.0),
                1:(adafruit_tsl2591.INTEGRATIONTIME_300MS, 300.0),
                2:(adafruit_tsl2591.INTEGRATIONTIME_400MS, 400.0),
                3:(adafruit_tsl2591.INTEGRATIONTIME_500MS, 500.0),
                4:(adafruit_tsl2591.INTEGRATIONTIME_600MS, 600.0)}
current_integration = 0

calibrated = False

#### Start of Sensor Configuration ####
# Initialize I2C for sensor
i2c_s = board.STEMMA_I2C() # uses STEMMA connector
sensor = adafruit_tsl2591.TSL2591(i2c_s)
# start at low gain with 2nd shortest integration interval
sensor.gain = gains[current_gain][0]
sensor.integration_time = integrations[current_integration][0]
#### End of Sensor Configuration ####

# Adjust the gain up or down by 1 unit
def bump_gain(up):
    global current_gain
    limit = False
    if up:
        current_gain += 1
        if current_gain == 4: #already at max gain
            limit = True
            current_gain -= 1
    else:
        current_gain-=1
        if current_gain < 0: # already at min gain
            limit = True
            current_gain = 0
    sensor.gain = gains[current_gain][0]
    return limit

# Adjust the integration duration up or down by 1 unit
def bump_integration(up):
    global current_integration
    limit = False
    if up:
        current_integration += 1
        if current_integration == 5:
            limit = True
            current_integration -= 1
    else:
        current_integration -= 1
        if current_integration < 0:
            limit = True
            current_integration = 0
    sensor.integration_time = integrations[current_integration][0]
    return limit

# begin main loop
while True:
    # update the text of the label(s) to show the sensor readings
    # Both channel levels range from 0-65535 (16-bit)
    ch0, ch1 = sensor.raw_luminosity
    ch0_s = f"Channel 0 (VS): {ch0}"
    #print(ch0_s)
    ch1_s = f"Channel 1 (IR): {ch1}"
    #print(ch1_s)
    display.set_light(ch0_s)
    display.set_ir(ch1_s)
    # calculate magnitudes per square arcsecond
    visCumulative = ch0-ch1
    # adjust the gain depending on the sensor and re-measure
    goodReading = True
    if visCumulative < 128: #gain too low
        goodReading = False
        if bump_gain(True):
            #print("max gain")
            if bump_integration(True):
                # max gain/integration
                goodReading = True
        _ = sensor.raw_luminosity
        #print("gain up")
    if ch0 == 0xffff or ch1 == 0xffff: #gain too high
        goodReading = False
        if bump_gain(False):
            #print("min gain")
            if bump_integration(False):
                # min gain/integration
                goodReading = True
        _ = sensor.raw_luminosity
        #print("gain down")
    # sample the sensor multiple times at low intensity
    if goodReading:
        ii = 1
        while visCumulative < 128:
            time.sleep(.005)
            ch0, ch1 = sensor.raw_luminosity
            visCumulative += (ch0-ch1)
            ii+=1
            if ii > 32: # only take in 32 measurements
                break
        # update mpsas when we have valid readings
        if visCumulative != 0:
            vis = visCumulative/(gains[current_gain][1] * integrations[current_integration][1] / 200.0 * ii)
            mpsas = 12.6 - 1.086 * math.log(vis) + _calibrationOffset;
            mpsas_s = f"MPSAS:{mpsas:.1f}"
            #print(mpsas_s)
            display.set_mpsas(mpsas_s)
    else:
        display.set_mpsas("MPSAS: Calibrating")
