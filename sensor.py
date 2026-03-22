# import for lux device
import adafruit_tsl2591
from ulab import numpy as np
import time
import json
import os

# Given a gain and integration setting
# obtain current visible light and adjust gain/integration based on
# reading
# Once a valid reading is acquired, lookup the gain/integration table
# for the list of values to search for the closest value in visible light
# interpolate between closest point and neighbor and return mpsas reading

# Note: skipping 100ms integration time as it's not likely to be useful
#  in night time conditions

NUM_READINGS = 32
MIN_READING_DIFF = 16

class myTSL2591(adafruit_tsl2591.TSL2591):
    """
    Wrapper class for the TSL2591 to return MPSAS based on calibration
    against an SQM-L device from Unihedron (https://www.unihedron.com/index.php)

    The TSL2591 is a readily available chip in a nice form factor from Adafruit
    (https://www.adafruit.com/product/1980)

    This wrapper attempts to map the visible light spectrum to an MPSAS
    value based on linearly interpolating between calibrated values.  The
    more variable the light sources during calibration the better the
    MPSAS interpolation
    """

    def __init__(self, i2c_device):
        """
        Initialize the underlyiing adafruit_tsl2591 sensor class
        and setup the sensor gain/integration values
        Additionally find the calibration file stored on the main
        drive read it in to setup the MPSAS interpolation
        """
        super(myTSL2591, self).__init__(i2c_device)
        self._calFile = "tsl2591_calibration.json"
        self._calData = None
        self.calibrated = False
        self._checkCalibration()
        self.gains = {
            0: (adafruit_tsl2591.GAIN_LOW, 1.0),
            1: (adafruit_tsl2591.GAIN_MED, 25.0),
            2: (adafruit_tsl2591.GAIN_HIGH, 425.0),
            3: (adafruit_tsl2591.GAIN_MAX, 9876.0),
        }
        self.integrations = {
            0: (adafruit_tsl2591.INTEGRATIONTIME_200MS, 200.0),
            1: (adafruit_tsl2591.INTEGRATIONTIME_300MS, 300.0),
            2: (adafruit_tsl2591.INTEGRATIONTIME_400MS, 400.0),
            3: (adafruit_tsl2591.INTEGRATIONTIME_500MS, 500.0),
            4: (adafruit_tsl2591.INTEGRATIONTIME_600MS, 600.0),
        }
        self.max_integration = 4
        self.min_integration = 0
        self.max_gain = 3
        self.min_gain = 0
        # store gain conversion
        self.current_gain = 0
        # store integration conversions (skipping 100ms)
        self.current_integration = 0
        # start at low gain with 2nd shortest integration interval
        self.gain = self.gains[self.current_gain][0]
        self.integration_time = self.integrations[self.current_integration][0]

    def _checkCalibration(self):
        """
        Try to find the calibration file and read it into class
        storage for interpolating values
        """
        if self._calFile in os.listdir():
            try:
                with open(self._calFile) as jf:
                    self._calData = json.load(jf)
                    self.calibrated = True
            except RuntimeError as err:
                print("Unable to read calibration data, sensor is uncalibrated!")
                print(err)

    def _reading(self):
        # take a reading to flush the sensor
        _ = self.raw_luminosity
        #time.sleep(self.integration_time/1e3)
        time.sleep(1)
        visCumulative = 0
        count = 0
        for ii in range(NUM_READINGS):
            ch0, ch1 = self.raw_luminosity
            if ch0 != 0xFFFF and ch1 != 0xFFFF:  # saturation
                visCumulative += (ch0 - ch1)
                count += 1
        vis = 0
        if visCumulative > 0:
            vis = visCumulative / count
        return vis

    def _calibrationPass(self, sqm_reading):
        """
        Iterate the gain and integration ranges at the current light
        level given the sqm reading
        Store each visible light reading with the sqm value as a tuple
        in the self._calData matrix
        """
        # iterate gain and integration and get reading
        for gainIdx in self.gains.keys():
            self.gain = self.gains[gainIdx][0]
            for integrationIdx in self.integrations.keys():
                self.integration_time = self.integrations[integrationIdx][0]
                # store visble and sqm reading as a tuple
                vis = self._reading()
                #if vis > 128:
                self._calData[gainIdx][integrationIdx].append((vis, sqm_reading))

    def printCalibration(self):
        for gain in self._calData.keys():
            for integ in self._calData[gain].keys():
                print(json.dumps(self._calData[gain][integ]))

    def runCalibration(self):
        """
        Routine to walk a use through calibration via the serial
        console I/O
        1) Start from lowest light level
        2) Take reading with SQM-L
        3) Take readings from TSL2591 and store
        4) Adjust light level higher then goto step 2
        """
        self._calData = {}
        for gi in self.gains.keys():
            self._calData[gi] = {}
            for ii in self.integrations.keys():
                self._calData[gi][ii] = []
        # 1: set light level
        print("Set light to lowest level (off in a black chamber is best)")
        ans = "n"
        while ans.lower() != "y":
            ans = input("lowest level ready? (y/n): ")
        # 2: get sqm-l reading
        sqm_reading = float(input("Input SQM-L reading: "))
        self._calibrationPass(sqm_reading)
        self.printCalibration()
        # 4: restart at #1 with new light level
        print(
            "Set next light level and type 'y'to continue OR type 'q' to complete calibration"
        )
        ans = input("(y/q): ")
        while ans.lower() == "y":
            sqm_reading = float(input("Input SQM-L reading: "))
            self._calibrationPass(sqm_reading)
            self.printCalibration()
            print(
                "Set next light level and type 'y' to continue OR type 'q' to complete calibration"
            )
            ans = input("(y/q): ")
        # just in case, sort the readings by visible light
        for gainIdx in self.gains:
            for integrationIdx in self.integrations:
                self._calData[gainIdx][integrationIdx] = sorted(
                    self._calData[gainIdx][integrationIdx]
                )
        try:
            with open(self._calFile, "w") as jf:
                json.dump(self._calData, jf)
        except RuntimeError as err:
            print("Unable to save calibration data")
            print(err)
        self.calibrated = True

    def findMPSAS(self, vis):
        """
        Once a valid reading is acquired, lookup the gain/integration table
        for the list of values to search for the closest value in visible light
        interpolate between closest point and neighbor and return mpsas reading
        """
        s_g = str(self.current_gain)
        s_i = str(self.current_integration)
        if s_g not in self._calData.keys():
            return 0,-1
        if s_i not in self._calData[s_g].keys():
            return 0,-1
        readings = self._calData[s_g][s_i]
        # readings is a list of tuples (visible,mpsas)
        if vis < readings[0][0]:  # too low
            return 0,-1
        if vis > readings[-1][0]:  # too high
            return 0,-1
        # mpsas
        # find closest visible
        min_diff = np.min(abs(np.array([v[0] for v in readings])-vis))
        if min_diff > MIN_READING_DIFF:
            return 0,-1
        mpsas_interp = np.interp(
            np.array([vis]),
            [v[0] for v in readings if v[0]],  # visible
            [m[1] for m in readings if m[0]],  # mpsas
        )[0]
        return min_diff,mpsas_interp

    def calcMPSAS(self, visCumulative, ii):
        """
        Return MPSAS based on *rough* formula to translate
        visible sensor reading to MPSAS
        """
        cg = self.gains[self.current_gain][1]
        ci = self.integrations[self.current_integration][1]
        vis = visCumulative / (cg * ci / 200.0 * ii)
        mpsas = 12.6 - 1.086 * np.log(vis)
        return mpsas

    def readMPSAS(self):
        mpsas = []
        print(f"Gain,Integration,Visible,MPSAS(estimate)")
        for gainIdx in self.gains.keys():
            self.current_gain = gainIdx
            self.gain = self.gains[gainIdx][0]
            for integrationIdx in self.integrations.keys():
                self.current_integration = integrationIdx
                self.integration_time = self.integrations[integrationIdx][0]
                vis = self._reading()
                if vis > 0:
                    c_mpsas = self.findMPSAS(vis)
                    if c_mpsas[1] > 0:
                        print(f"{self.gain},{self.integration_time},{vis},{c_mpsas}")
                        mpsas.append(c_mpsas)
        if len(mpsas) > 0:
            # alternative mpsas is return min
            #midx = np.argmin(np.array([v[0] for v in mpsas]))
            #print(mpsas[midx])
            m_mpsas = np.mean([x[1] for x in mpsas])
            print(f"Mean MPSAS = {m_mpsas}")
            return (m_mpsas, True)
        else:
            return (0, False)
