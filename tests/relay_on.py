import serial
import time

print('relay_on: port open')
sp = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, exclusive=True)
# Turn On: A0 01 01 A2
cmd_on = b'\xA0\x01\x01\xA2'
sp.write(cmd_on)
sp.close()
print('relay_on: port closed')