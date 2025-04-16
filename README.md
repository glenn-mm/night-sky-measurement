# night-sky-measurement
Build and code for optical night sky measurements

## Build Steps:
1. Solder the pins onto the QtPy
2. Connect the uFL antenna to the QtPy
3. Solder the pins onto the display
4. Download Thonny (https://thonny.org)
5. Install Circuit Python onto QtPy via Thonny (put chp into boot mode first!)
6. Download Circuit Python libraries (https://circuitpython.org/libraries)
7. Add necessary libraries to Circuit Python drive under lib directory
   * adafruit_bus_device
   * adafruit_tsl2591.mpy
   * adafruit_displayio_ssd1306.mpy
   * adafruit_ssd1306.mpy
   * adafruit_display_text
8. Connect TSL2591 via STEMMA cable to QtPy
9. Run example from https://github.com/adafruit/Adafruit_CircuitPython_TSL2591/blob/main/examples/tsl2591_simpletest.py
10. Copy code.py from this project and test display and sensor
11. Package into case!
