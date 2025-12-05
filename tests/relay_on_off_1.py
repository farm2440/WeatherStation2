import serial
import time

print('relay_on_off_1: started...')
while True:
    try:
        sp = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, exclusive=True)
        break
    except Exception:
        time.sleep(1)
        continue
print('relay_on_off_1: port open')
# Turn On: A0 01 01 A2
cmd_on = b'\xA0\x01\x01\xA2'
sp.write(cmd_on)
time.sleep(10)
# Turn Off: A0 01 00 A1
cmd_off = b'\xA0\x01\x00\xA1'
sp.write(cmd_off)
sp.close()
print('relay_on_off_1: port closed')