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
    
    def __init__(self,i2c_device):
        """
        Initialize the underlyiing adafruit_tsl2591 sensor class
        and setup the sensor gain/integration values
        Additionally find the calibration file stored on the main
        drive read it in to setup the MPSAS interpolation
        """
        super(myTSL2591, self).__init__(i2c_device)
        self._calFile = 'tsl2591_calibration.json'
        self._calData = None
        self.calibrated = False
        self._checkCalibration()
        self.gains = {0:(adafruit_tsl2591.GAIN_LOW,  1.0),
                      1:(adafruit_tsl2591.GAIN_MED,  25.0),
                      2:(adafruit_tsl2591.GAIN_HIGH, 425.0),
                      3:(adafruit_tsl2591.GAIN_MAX,  9876.0)}
        self.integrations = {0:(adafruit_tsl2591.INTEGRATIONTIME_200MS, 200.0),
                             1:(adafruit_tsl2591.INTEGRATIONTIME_300MS, 300.0),
                             2:(adafruit_tsl2591.INTEGRATIONTIME_400MS, 400.0),
                             3:(adafruit_tsl2591.INTEGRATIONTIME_500MS, 500.0),
                             4:(adafruit_tsl2591.INTEGRATIONTIME_600MS, 600.0)}
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

    def _calibrationPass(self,sqm_reading):
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
                # take a reading to flush the sensor
                _ = self.raw_luminosity
                time.sleep(0.01)
                visCumulative = 0
                count = 0
                for ii in range(32):
                    ch0, ch1 = self.raw_luminosity
                    if ch0 != 0xffff and ch1 != 0xffff: #saturation
                        visCumulative += ch0-ch1
                        count += 1
                vis = 0
                if visCumulative > 0:
                    vis = visCumulative/32
                # store visble and sqm reading as a tuple
                if vis > 128:
                    self._calData[gainIdx][integrationIdx].append((vis,sqm_reading))
   
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
        ans = 'n'
        while ans.lower() != 'y':
            ans = input("lowest level ready? (y/n): ")
        # 2: get sqm-l reading
        sqm_reading = float(input("Input SQM-L reading: "))
        self._calibrationPass(sqm_reading)
        self.printCalibration()
        # 4: restart at #1 with new light level
        print("Set next light level and type 'y'to continue OR type 'q' to complete calibration")
        ans = input("(y/q): ")
        while ans.lower() == 'y':
            sqm_reading = float(input("Input SQM-L reading: "))
            self._calibrationPass(sqm_reading)
            self.printCalibration()
            print("Set next light level and type 'y' to continue OR type 'q' to complete calibration")
            ans = input("(y/q): ")
        # just in case, sort the readings by visible light
        for gainIdx in self.gains:
            for integrationIdx in self.integrations:
                self._calData[gainIdx][integrationIdx]=sorted(self._calData[gainIdx][integrationIdx])
        try:
            with open(self._calFile,'w') as jf:
                json.dump(self._calData,jf)
        except RuntimeError as err:
            print("Unable to save calibration data")
            print(err)
        self.calibrated = True

    def findMPSAS(self,vis):
        """
        Once a valid reading is acquired, lookup the gain/integration table
        for the list of values to search for the closest value in visible light
        interpolate between closest point and neighbor and return mpsas reading
        """
        if self.current_gain not in self._calData.keys():
            return -1
        if self.current_intergration not in self._calData[self.current_gain].keys():
            return -1
        readings = self._calData[self.current_gain][self.current_integration]
        # remove invalid readings
        #readings = [r for r in readings if r[0] != None]
        # readings is a list of tuples (visible,mpsas)
        if vis < readings[0][0]: # too low
            return -1
        if vis > readings[-1][0]: # too high
            return -1
        return np.interp(np.array([vis]),
                         [v[0] for v in readings if v[0]], #visible
                         [m[1] for m in readings if m[0]])[0] #mpsas

    def bump_gain(self,up):
        """
        Adjust the gain up or down by 1 unit
        return whether we've hit a limit
        """
        limit = False
        if up:
            self.current_gain += 1
            if self.current_gain > self.max_gain: #already at max gain
                limit = True
                self.current_gain = self.max_gain
        else:
            self.current_gain-=1
            if self.current_gain < self.min_gain: # already at min gain
                limit = True
                self.current_gain = self.min_gain
        self.gain = self.gains[self.current_gain][0]
        return limit

    def bump_integration(self,up):
        """
        Adjust the integration duration up or down by 1 unit
        return whether we've hit a limit
        """
        limit = False
        if up:
            self.current_integration += 1
            if self.current_integration > self.max_integration:
                limit = True
                self.current_integration = self.max_integration
        else:
            self.current_integration -= 1
            if self.current_integration < self.min_integration:
                limit = True
                self.current_integration = self.min_integration
        self.integration_time = self.integrations[self.current_integration][0]
        return limit

    def readMPSAS(self):
        """
        Find the MPSAS value for the current sensor reading
        This includes interpolating across the calibration data
        once a quality ready from the TSL2591 is obtained
        returns the two channels and an MPSAS value
        if the MPSAS value is < 0 it is invalid
        """
        # Both channel levels range from 0-65535 (16-bit)
        ch0, ch1 = self.raw_luminosity
        # calculate magnitudes per square arcsecond
        visCumulative = ch0-ch1
        # adjust the gain depending on the sensor and re-measure
        goodReading = True
        if visCumulative < 128: #gain too low
            goodReading = False
            if self.bump_gain(True):
                #print("max gain")
                if self.bump_integration(True):
                    # max gain/integration
                    goodReading = True
            _ = self.raw_luminosity
            #print("gain up")
        if ch0 == 0xffff or ch1 == 0xffff: #gain too high
            goodReading = False
            if self.bump_gain(False):
                #print("min gain")
                if self.bump_integration(False):
                    # min gain/integration
                    goodReading = True
            _ = self.raw_luminosity
            #print("gain down")
        # sample the sensor multiple times at low intensity
        if goodReading:
            ii = 1
            while visCumulative < 128:
                time.sleep(.005)
                ch0, ch1 = self.raw_luminosity
                visCumulative += (ch0-ch1)
                ii+=1
                if ii > 32: # only take in 32 measurements
                    break
            # update mpsas when we have valid readings
            if visCumulative != 0:
                vis = visCumulative/ii
                mpsas = self.findMPSAS(vis)
                return (ch0, ch1, mpsas)
        return (ch0, ch1, -1)

