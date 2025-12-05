import time
import serial


sp = serial.Serial(port='/dev/ttyUSB0', baudrate=9600)
for n in range(0, 10):
    # Turn On: A0 01 01 A2
    cmd_on = b'\xA0\x01\x01\xA2'
    sp.write(cmd_on)
    time.sleep(3)
    # Turn Off: A0 01 00 A1
    cmd_off = b'\xA0\x01\x00\xA1'
    sp.write(cmd_off)
    time.sleep(3)
sp.close()