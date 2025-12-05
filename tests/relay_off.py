import serial

sp = serial.Serial(port='/dev/ttyUSB0', baudrate=9600)
# Turn Off: A0 01 00 A1
cmd_off = b'\xA0\x01\x00\xA1'
sp.write(cmd_off)
sp.close()
