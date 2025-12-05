import socket
import time
import serial

# When TCP connection is established thre relay is ON
HOST = "0.0.0.0"  # Standard loopback interface address (localhost)
PORT = 8888  # Port to listen on (non-privileged ports are > 1023)
SERIAL = '/dev/ttyUSB0'

def ron():
    sp = serial.Serial(port=SERIAL, baudrate=9600)
    # Turn On: A0 01 01 A2
    cmd_on = b'\xA0\x01\x01\xA2'
    sp.write(cmd_on)
    sp.close()

def roff():
    sp = serial.Serial(port=SERIAL, baudrate=9600)
    # Turn Off: A0 01 00 A1
    cmd_off = b'\xA0\x01\x00\xA1'
    sp.write(cmd_off)
    sp.close()

soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
soc.bind((HOST, PORT))
soc.listen(1)
soc.settimeout(0.1)

while True:
    print(" Awaiting TCP connection on port {0}".format(PORT))
    # open port and wait for TCP connection
    clnt_conn = None
    while clnt_conn is None:
        try:
            clnt_conn, clnt_addr = soc.accept()
        except Exception as ex:
            pass
    ron()
    print('Relay ON')

    while True:
        try:
            data = clnt_conn.recv(1024)
            if len(data)==0:
                clnt_conn.close()
                break            
        except Exception as ex:
            break
        time.sleep(0.05)
    roff()
    print('Relay OFF')
