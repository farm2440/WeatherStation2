import serial
import time
import subprocess
from datetime import datetime
import os
import sys


# Сверява часовника на компютъра вземайки точно време през SIM900A модула
# За проба трябв да се спре сверяването по NTP с команда:
# sudo timedatectl set-ntp off

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

pid = os.getpid()
print("sim900_set_time.py PID:", pid)
now = datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
log_file = "./log/sim900_set_time.log"
with open(log_file, "a") as file:
    file.write(f"PID:{pid}\n")
    file.write(f"Current date-time: {timestamp}\n")

# Отваряне на серийния порт
ser = serial.Serial('/dev/ttyS0', baudrate=9600, timeout=2)
if not ser.is_open:
    print('ERR: Failed to open serial port')
    sys.exit(1)


# Отваряне на HTTP режима:
for cmd in OPEN_SESSION_COMMANDS_LIST:
    # Изпращане на команда
    ser.write(str.encode(cmd+'\r\n'))
    # Четене на отговора
    time.sleep(5)
    response =  ser.read(ser.inWaiting()).decode(errors='ignore')  # Read response
    print('CMD:', cmd, '  RESP:', response)

# Изпращане на данни към ThingsSpeak с GET заявкa
cmd = 'AT+HTTPPARA="URL","http://postman-echo.com/time/now"'
ser.write(str.encode(cmd + '\r\n'))
# Четене на отговора
time.sleep(5)
response = ser.read(ser.inWaiting()).decode(errors='ignore')  # Read response
print('CMD:', cmd, '  RESP:', response)
cmd = 'AT+HTTPACTION=0'
ser.write(str.encode(cmd + '\r\n'))
# Четене на отговора
time.sleep(7)
response = ser.read(ser.inWaiting()).decode(errors='ignore')  # Read response
print('CMD:', cmd, '  RESP:', response)
time.sleep(5)
cmd = 'AT+HTTPREAD'
ser.write(str.encode(cmd + '\r\n'))
# Четене на отговора
time.sleep(5)
dt_response = ser.read(ser.inWaiting()).decode(errors='ignore')  # Read response
print('CMD:', cmd, '  RESP:', response)

# Затваряне на HTTP режима:
for cmd in CLOSE_SESSION_COMMANDS_LIST:
    # Изпращане на команда
    ser.write(str.encode(cmd+'\r\n'))
    # Четене на отговора
    time.sleep(5)
    response =  ser.read(ser.inWaiting()).decode(errors='ignore')  # Read response
    print('CMD:', cmd, '  RESP:', response)
# Затваряне на порта
ser.close()

print('--------------------------------')
print('type(dt_response):', type(dt_response))
print('dt_respoce ----START----')
print(dt_response)
print('dt_response ----END----')

resp_list = dt_response.split('\n')
print('DATE-TIME:', resp_list[3])
with open(log_file, "a") as file:
    file.write(f"API responce: {resp_list[3]}\n")
# Parse the string into a datetime object
dt_object = datetime.strptime(resp_list[3].strip("\r\n"), '%a, %d %b %Y %H:%M:%S GMT')
print('dttyme type:', type(dt_object))

# Format the datetime object into the required format for the `date` command
formatted_date = dt_object.strftime('%Y-%m-%d %H:%M:%S')

# Construct the command to set the system clock
command = f"sudo date -s '{formatted_date}'"

# Execute the command
subprocess.run(command, shell=True)

print(f"Command to set the clock: {command}")
now = datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
with open(log_file, "a") as file:
    file.write(f"New date-time: {timestamp}\n")
    file.write(f"================================\n")

