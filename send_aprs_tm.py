# През зададен период извлича данни за телеметрия от БД Redis и подготвя съобщение за APRS .
# Предаването става по следния начин:
#   1. Задейства се РТТ реле
#   2. Генерира се текстов файл който се записва в изходящата папка на kissutil . Това приложение предава
#       данните на direwolf който извършва модулацията през звуковата карта.
#   3. Изчаква се файла да бъде изтрит от kissutil.
#   4. Освобождава се РТТ релето.
import time
from datetime import datetime
import serial
from datetime import timedelta, datetime
import redis
import os
import random
import RPi.GPIO as GPIO


# TODO: Да се проверява за активни Direwolf и Kissutil преди да се активира РТТ
# релето. Ако процесите не са активни да се изпрати команда за разпадане на 
# релето и да не се пращат данни !!!!

# 

tx_period = timedelta(minutes=20, seconds=00)  # Период на изпращане на APRS в секунди
SERIAL_PORT_NAME = '/dev/ttyUSB0' # Локално реле за РТТ, управлява се по сериен порт с команда
log_file = "./log/send_aprs_tm.log"

def usb_ptt_on():
    print('usb_ptt_on(): port openning...', end=' ')
    while True:
        try:
            sp = serial.Serial(port=SERIAL_PORT_NAME, baudrate=9600, exclusive=True)
            break
        except Exception:
            time.sleep(1)
            continue
    print(' port is open...', end=' ')
    time.sleep(3)  # Това изчакване е за да не се излъчва веднага след като релето е било освободено от друг процес
    # Turn On: A0 01 01 A2
    cmd_on = b'\xA0\x01\x01\xA2'
    sp.write(cmd_on)
    print(' PTT ON...', end=' ')
    sp.close()
    time.sleep(1)
    print('port is closed!')


def usb_ptt_off():
    print('usb_ptt_off(): port openning...', end=' ')
    while True:
        try:
            sp = serial.Serial(port=SERIAL_PORT_NAME, baudrate=9600, exclusive=True)
            break
        except Exception:
            time.sleep(1)
            continue
    print(' port is open...', end=' ')
    # Turn Off: A0 01 00 A1
    cmd_off = b'\xA0\x01\x00\xA1'
    sp.write(cmd_off)
    print(' PTT OFF...', end=' ')
    sp.close()
    time.sleep(1)
    print(' port is closed!')
    

def send_aprs(msg):
    # РТТ, запис в KISSOUT, изчакване да изчезне файла, освобождаване на РТТ.
    usb_ptt_on()
    file = open('/home/svilen/ws2/KISSOUT/telemetrymsg','w')
    file.write(msg)
    file.close()
    while True:
        if not os.listdir('/home/svilen/ws2/KISSOUT'):
            print('KISSOUT is empty')
            break
        else:
            print('KISSOUT not empty')
            time.sleep(1)
    time.sleep(2)
    usb_ptt_off()
    time.sleep(5)
    

pid = os.getpid()
print("send_aprs_tm.py PID:", pid)
now = datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
# Проверява дали е достъпен сериен порт за РТТ. 
# Ако не е, пише в log файл и излиза
if not os.path.exists(SERIAL_PORT_NAME):
    with open(log_file, "a") as file:
        file.write(f"PID:{pid}\n")
        file.write(f"Current date-time: {timestamp} ERR: PTT serial port not found!\n")
        print('ERR: PTT serial port not found!')
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

GPIO.setmode(GPIO.BCM)
GPIO_PIN = 21
GPIO.setup(GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
aprs_enable = GPIO.input(GPIO_PIN)
GPIO.cleanup()
if aprs_enable == GPIO.LOW:
    print('send_aprs_tm: APRS not enabled! Check the switch position!')
    exit(0)    

snum = rds.get('sequence_number')
if snum is None:
    sequence_number = random.randint(1, 900)
else:
    sequence_number = int(snum) + 1
    if sequence_number > 999:
        sequence_number = 1
rds.set('sequence_number', value=sequence_number)

dt = datetime.now()
print()
print(datetime.now(), "  Sending telemetry APRS... Sequence number:", sequence_number)

# s_next_tm_tx = str(datetime.now() + tx_period)[:-7]
# print('Time until next telemetry TX:', s_next_tm_tx)
# rds.set('next_tm_tx', value=s_next_tm_tx, ex=5)


int_or_none = lambda x: '' if x is None else int(x)
temp1 = int_or_none(rds.get('T2')) # Maza
hum1 = int_or_none(rds.get('Rh2'))
temp2 = int_or_none(rds.get('T4')) # Predverie et.1
hum2 = int_or_none(rds.get('Rh4'))
temp3 = int_or_none(rds.get('T5')) # Kuhnja
hum3 = int_or_none(rds.get('Rh5'))
temp4 = int_or_none(rds.get('T8')) # Tavan
hum4 = int_or_none(rds.get('Rh8'))
bit0 = int_or_none(rds.get('B0'))

print('T2:{} Rh2:{} T4={} Rh4={} T5={} Rh5={} T8={} Rh8={} B0={}'.format(temp1, hum1, temp2, hum2, temp3, hum3, temp4, hum4, bit0))

# Съставяне на низа
crdmsg  = 'LZ2SMX-4>APDW16,WIDE2-2:!4313.98N/02753.78Ey'
parmmsg = 'LZ2SMX-4>APDW16,WIDE2-2::LZ2SMX-4 :PARM.Tbsmt,Rh,Tfl1,Tktcn,Tloft,B7,B6,B5,B4,B3,B2,B1,B0'
unitmsg = 'LZ2SMX-4>APDW16,WIDE2-2::LZ2SMX-4 :UNIT.C,%,C,C,C,B7,B6,B5,B4,B3,B2,B1,B0'
eqnsmsg = 'LZ2SMX-4>APDW16,WIDE2-2::LZ2SMX-4 :EQNS.0,1,0,0,1,0,0,1,0,0,1,0,0,1,0'
bitsmsg = 'LZ2SMX-4>APDW16,WIDE2-2::LZ2SMX-4 :BITS.11111111,Internal telemetry'
valmsg  = 'LZ2SMX-4>APDW16,WIDE2-2:T#{},{},{},{},{},{},0000000{}'.format(sequence_number,temp1,hum1,temp2,temp3,temp4,bit0)

print('APRS TM coordinates message: ', crdmsg)
send_aprs(crdmsg)
print('APRS TM PARM message: ', parmmsg)
send_aprs(parmmsg)
print('APRS TM UNIT message: ', unitmsg)
send_aprs(unitmsg)
print('APRS TM EQNS message: ', eqnsmsg)
send_aprs(eqnsmsg)
print('APRS TM  message: ', valmsg)
send_aprs(valmsg)
print('APRS TM BITS messag: ', bitsmsg)
send_aprs(bitsmsg)
