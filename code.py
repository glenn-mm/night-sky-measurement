# SPDX-FileCopyrightText: 2025 Glenn Henderson for Monterey Makers (inspiration from https://github.com/gshau/SQM_TSL2591)
# SPDX-FileCopyrightText: 2024 Tim Cocks for Adafruit Industries
# SPDX-FileCopyrightText: 2024 Jose D. Montoya
#
# SPDX-License-Identifier: MIT

# imports for basic functions
import time
import board
import storage
# import display functions
import display
# sensor class
import sensor

#### Start of Sensor Configuration ####
# Initialize I2C for sensor
i2c_s = board.STEMMA_I2C() # uses STEMMA connector
tsl2591 = sensor.myTSL2591(i2c_s)
#### End of Sensor Configuration ####

def runCalibration():
    # 0: unmount USB
    print("un-mount the USB CIRCUITPY drive from your computer")
    readonly = True
    while readonly:
        try:
            print("Trying to remount storage for calibration....")
            storage.remount('/',readonly=False)
            readonly = False
        except RuntimeError as err:
            print("Failed: un-mount the USB CIRCUITPY drive from your computer")
            print(err)
            time.sleep(5)
    print("Beginning calibration routine")
    tsl2591.runCalibration()

# prepare for calibration w/ 3 second timeout
if not tsl2591.calibrated:
    print("Device uncalibrated, begin calibration...")
    runCalibration()

# begin main loop
while True:
    # update the text of the label(s) to show the sensor readings
    ch0, ch1, mpsas = tsl2591.readMPSAS()
    ch0_s = f"Channel 0 (VS): {ch0}"
    display.set_light(ch0_s)
    #print(ch0_s)
    ch1_s = f"Channel 1 (IR): {ch1}"
    display.set_ir(ch1_s)
    #print(ch1_s)
    if mpsas > 0:
        mpsas_s = f"MPSAS:{mpsas:.1f}"
        #print(mpsas_s)
        display.set_mpsas(mpsas_s)
    else:
        display.set_mpsas("MPSAS: Out of Range")
