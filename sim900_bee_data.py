import serial
import time
from datetime import timedelta, datetime
import redis
import os

# https://thingspeak.mathworks.com/channels/2016699/private_show
# https://thingspeak.mathworks.com/channels/2016699
# Write API key : 6TXU2QX7J9FSNCIF
# Write a Channel Feed : GET https://api.thingspeak.com/update?api_key=6TXU2QX7J9FSNCIF&field1=0
# https://www.mathworks.com/   usr: s_stavrev@hotmail.com  password: SMX#ThSp&SIM900 username: mwa0000028975976
# https://www.thingsmobile.com/

OPEN_SESSION_COMMANDS_LIST = [
    'AT+SAPBR=3,1,"Contype","GPRS"',
    'AT+SAPBR=3,1,"APN","TM"',
    'AT+SAPBR=1,1',
    'AT+SAPBR=2,1',
    'AT+HTTPINIT',
    'AT+HTTPPARA="CID",1'
]

CLOSE_SESSION_COMMANDS_LIST = [
    'AT+HTTPTERM',
    'AT+SAPBR=0,1'
]

SERIAL_PORT_NAME = '/dev/ttyS0' # Сериен порт към SIM900 
log_file = "./log/sim900_bee_data.log"

pid = os.getpid()
print("send_aprs_tm.py PID:", pid)
now = datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
# Проверява дали е достъпен сериен порт за SIM900. 
# Ако не е, пише в log файл и излиза
if not os.path.exists(SERIAL_PORT_NAME):
    with open(log_file, "a") as file:
        file.write(f"PID:{pid}\n")
        file.write(f"Current date-time: {timestamp} ERR: SIM900 serial port not found!\n")
        print('ERR: SIM900 serial port not found!')
        exit(1)    

rds = redis.Redis(host='localhost', port=6379, decode_responses=True)
db_connect_retry = 3
# Не тръгва докато няма връзка с БД
while True:
    if db_connect_retry == 0:
        with open(log_file, "a") as file:
            file.write(f"PID:{pid}\n")
            file.write(f"Current date-time: {timestamp} ERR: No connection with Redis DB!\n")
            print('ERR: No connection with Redis DB!\n')
            exit(1)
    try:
        rds.ping()
        break
    except (redis.exceptions.ConnectionError, ConnectionRefusedError):
        print("Redis connection error!")
        db_connect_retry = db_connect_retry - 1        
        time.sleep(5)
        continue

print(datetime.now(), "  Sending bees data SIM900...")

h1_weight = rds.get('h1_weight')
h2_weight = rds.get('h2_weight')

# Отваряне на серийния порт
ser = serial.Serial(SERIAL_PORT_NAME, baudrate=9600, timeout=2)
# Отваряне на HTTP режима:
for cmd in OPEN_SESSION_COMMANDS_LIST:
    # Изпращане на команда
    ser.write(str.encode(cmd+'\r\n'))
    # Четене на отговора
    time.sleep(3)
    response =  ser.read(ser.inWaiting()).decode(errors='ignore')  # Read response
    if len(response) == 0:
        print('ERR: No response to command CMD:', cmd)
        # TODO: 
    else:
        print('CMD:', cmd, '  RESP:', response)

# Изпращане на данни към ThingsSpeak с GET заявкa
cmd = 'AT+HTTPPARA="URL","api.thingspeak.com/update/?api_key=6TXU2QX7J9FSNCIF&field3={}&field6={}"'.format(h1_weight, h2_weight)
ser.write(str.encode(cmd + '\r\n'))
# Четене на отговора
time.sleep(3)
response = ser.read(ser.inWaiting()).decode(errors='ignore')  # Read response
print('CMD:', cmd, '  RESP:', response)
cmd = 'AT+HTTPACTION=0'
ser.write(str.encode(cmd + '\r\n'))
# Четене на отговора
time.sleep(7)
response = ser.read(ser.inWaiting()).decode(errors='ignore')  # Read response
if len(response) == 0:
    print('ERR: No response to command CMD:', cmd)
else:
    print('CMD:', cmd, '  RESP:', response)
time.sleep(3)

# Затваряне на HTTP режима:
for cmd in CLOSE_SESSION_COMMANDS_LIST:
    # Изпращане на команда
    ser.write(str.encode(cmd+'\r\n'))
    # Четене на отговора
    time.sleep(1)
    response =  ser.read(ser.inWaiting()).decode(errors='ignore')  # Read response
    if len(response) == 0:
        print('ERR: No response to command CMD:', cmd)
    else:
        print('CMD:', cmd, '  RESP:', response)
# Затваряне на порта
ser.close()


