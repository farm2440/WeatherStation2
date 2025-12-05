import time
import serial
from os.path import exists

# Send a packet using kissutil.
# Start Direwolf:
#    pi@raspberrypi:~/work/python/weatherstation2 $ direwolf -t 0 -c direwolf.conf -l ./log -d u -d n
# Start kissutil:
#    kissutil  -f KISSOUT    (Only TX)
#    kissutil  -f KISSOUT -o KISSIN   (TX&RX)
# Create a text file with content a packet in KISS format and kissutil will send it
# and than it wii delete the file


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
    
k = 39
for n in range(10):
    # PTT ON
    relay_on()
    # Write a packet to a file
    f = open("./KISSOUT/txpacket", "a")
    # Info
    f.write("LZ2SMX-3>APDW14,WIDE2-2:!4313.98N/02753.78EyTEST-{}".format(k))
    f.close()
    time.sleep(2)
    # Weatherstation
    # f.write("LZ2SMX-3>APDW14,WIDE2-2:!4313.98N/02753.78E_225/003g005t041r000p000P000b10198h44")
    # f.close()
    # Telemetry
    f = open("./KISSOUT/txpacket2", "a")
    f.write("LZ2SMX-3>APDW16,WIDE2-2::LZ2SMX-3 :UNIT.Vdc,deg.C,deg.C,deg.C")
    f.close()
    time.sleep(2)
    f = open("./KISSOUT/txpacket3", "a")
    f.write("LZ2SMX-3>APDW16,WIDE2-2::LZ2SMX-3 :EQNS.0,1,0,0,1,0,0,1,0,0,1,0")
    f.close()
    time.sleep(2)
    f = open("./KISSOUT/txpacket1", "a")
    f.write("LZ2SMX-3>APDW16,WIDE2-2::LZ2SMX-3 :PARM.UBatt,Temp1,Temp2,Temp3")
    f.close()
    time.sleep(2)
    f = open("./KISSOUT/txpacket4", "a")
    f.write("LZ2SMX-3>APDW16,WIDE2-2:T#{},13.65,013,014,015".format(k))
    f.close()
    time.sleep(2)
    
    # Wait for kissutil to process the file. It will be deleted when done.
    while exists('./KISSOUT/txpacket'):
        time.sleep(1)
    time.sleep(2)
    # PTT OFF
    relay_off()
    time.sleep(30)
    k+=1