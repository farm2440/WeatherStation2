from socket import *
import time
import serial


def relay_on():
    sp = serial.Serial(port='/dev/ttyUSB0', baudrate=9600)
    # Turn On: A0 01 01 A2
    cmd_on = b'\xA0\x01\x01\xA2'
    sp.write(cmd_on)
    sp.close()

def relay_off():
    sp = serial.Serial(port='/dev/ttyUSB0', baudrate=9600)
    # Turn Off: A0 01 00 A1
    cmd_off = b'\xA0\x01\x00\xA1'
    sp.write(cmd_off)
    sp.close()

def aprs(aprs_data_string, callsigns, msg_header):
    # This function takes a string which should contain sensors data and transmit, adds APRS header including
    # APRS symbol, GPS coordinates and transmits it over radio. PTT is triggered by GPIO  .
    # Direwolf shall be started on on power on. This function connects to Direwolf (software TNC) on port 8001.

    print("Sending APRS:", aprs_data_string)
    msg_body = aprs_data_string
    # msg_body = '!4323.28H/02789.64E>TEST'
    # msg_body = '!4313.98NW02753.78E# TEST 6'
    # msg_body = '!4313.98N/02753.78Ey c999s999g008t054r001 TEST 20'
    # the leter after N  between long and alt is the overlay char. / for none
    # the leter after E after long and alt is the symbol. _ weather station, y house with yagi, > car

    #               DST       SRC      DIGI-->
#    callsigns = ['LZ2SMX9 ', 'LZ2SMX3', 'WIDE2 1']
    # msg_header = '!4313.98N/02753.78Ey '  # vazrajdane 66, house with Yagi
    # msg_header = '!4307.46N/02744.14Ey '  # Zdravets, house with Yagi
#    msg_header = '!4307.46N/02744.14E'  # Zdravets, Weather Station WX
    
    msg = chr(0xC0)
    msg += chr(0x00)
    for i in range(0, len(callsigns)):
        cs = callsigns[i]
        for j in range(0, 6):
            msg += chr(ord(cs[j]) << 1)
        ssid = ord(cs[6])
        ssid <<= 1
        ssid += 0x60
        if i == len(callsigns) - 1:
            # Last address
            ssid += 1
        msg += chr(ssid)

    msg += chr(0x03)
    msg += chr(0xF0)
    msg += msg_header
    msg += msg_body
    msg += chr(0xC0)

    try:
#        soc = socket(AF_INET, SOCK_STREAM)
#        soc.connect(('127.0.0.1', 8001))
        msg = 'K1NRO-1>APDW14,WIDE2-2:!4238.80NS07105.63W#PHG5630'

        relay_on()
        time.sleep(0.1)
        soc.send(msg.encode())
        soc.close()
        time.sleep(2)
        relay_off()
    except socket_error as err:
        print("ERR: Failed APRS trasmission! Check that Direwolf is running.")
        print(err)
        print

    return 0


    
soc = socket(AF_INET, SOCK_STREAM)
soc.connect(('127.0.0.1', 8001))

# msgBody = '!4323.28H/02789.64E>TEST'
# msgBody = '!4313.98NW02753.78E# TEST 6'
# msgBody = '!4313.98N/02753.78Ey c999s999g008t054r001 TEST 20'
# the leter after N  between long and alt is the overlay char. / for none
# the leter after E after long and alt is the symbol. _ weather station, y house with yagi, > car

#               DST       SRC      DIGI-->
callsigns = ['LZ2SMX9 ', 'LZ2SMX3', 'WIDE2 1']
# msgHeader = '!4313.98N/02753.78Ey '  # vazrajdane 66, house with Yagi
msg_header = '!4307.46N/02744.14Ey '  # Zdravets, house with Yagi

while True:
    # weather station report:
    aprs_message = '>TEST'       # all data in one string in format <var>=<value>
    aprs_wx_message = 'c999s999g008t054r001'    # weather data in aprs weather station format

    aprs(aprs_wx_message,callsigns,msg_header)
    break
    time.sleep(2)

