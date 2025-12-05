# През зададен период извлича метео данни от БД Redis и подготвя съобщение за APRS .
# Предаването става по следния начин:
#   1. Задейства се РТТ реле
#   2. Генерира се текстов файл който се записва в изходящата папка на kissutil . Това приложение предава
#       данните на direwolf който извършва модулацията през звуковата карта.
#   3. Изчаква се файла да бъде изтрит от kissutil.
#   4. Освобождава се РТТ релето.


# TODO: Да се проверява за активни Direwolf и Kissutil преди да се активира РТТ
# релето. Ако процесите не са активни да се изпрати команда за разпадане на 
# релето и да не се пращат данни !!!!

import time
from datetime import datetime
import serial
import socket
from datetime import timedelta, datetime
import redis
import os
import RPi.GPIO as GPIO

# TX20 връща число от 0 до 15 за посока. За да се получи в градуси се умножава по 22.5.
# Със следния речник може да се конветира в низ:
wind_dir_dictionary = {
    0:  "N",
    1:  "NNE",
    2:  "NE",
    3:  "ENE",
    4:  "E",
    5:  "ESE",
    6:  "SE",
    7:  "SSE",
    8:  "S",
    9:  "SSW",
    10: "SW",
    11: "WSW",
    12: "W",
    13: "WNW",
    14: "NW",
    15: "NNW"
}

SERIAL_PORT_NAME = '/dev/ttyUSB0' # Локално реле за РТТ, управлява се по сериен порт с команда
log_file = "./log/send_aprs_ws.log" 

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
    print('send_aprs_ws: APRS not enabled! Check the switch position!')
    exit(0)

print()
print(datetime.now(), "  Sending WS APRS...")
# Извличане на записите на дъжд за последните 24 часа
# Всеки път когато има отчет за импулси от сензора за дъжд се правят два записа в БД. Единия е с трайност
# един часи и втория с трайност 24 часа. При извличане записите се сумират за получаване на резултата за валежа.
# При извличане на множество записи от БД се вика функцията scan като първоначално се задава параметъра
# cursor=0 . Функцията връща нова стойност за cursor с която става следващото извикване. Не е гарантирано
# с едно викане на scan колко записа ще се извлекат наведнъж. Извикването става до връщане на стойност
# за cursor нула. Това показва, че всички записи са извлечени.
# Дъжд за последните 24 часа
# https://wiki.dfrobot.com/SKU_SEN0575_Gravity_Rainfall_Sensor
    
rain24 = 0
cursor = 0
keys = []
while True:
    result = rds.scan(cursor, match='WX:rain24h:*')
    cursor = result[0]
    keys += result[1]
    if cursor == 0:
        break
for k in keys:
    rain24 += int(rds.get(k))
# Дъжд за последния час
rain1 = 0
cursor = 0
keys = []
while True:
    result = rds.scan(cursor, match='WX:rain1h:*')
    cursor = result[0]
    keys += result[1]
    if cursor == 0:
        break
for k in keys:
    rain1 += int(rds.get(k))

int_or_none = lambda x: None if x is None else int(x)
float_or_none = lambda x: None if x is None else float(x)
temp = int_or_none(rds.get('WX:temp'))
hum = int_or_none(rds.get('WX:hum'))
pressure = int_or_none(rds.get('WX:pressure'))
wind_dir = int_or_none(rds.get('WX:wind:dir'))
wind_speed = float_or_none(rds.get('WX:wind:speed'))
wind_gusts = float_or_none(rds.get('WX:wind:gusts'))
ubat = rds.get('WX:UBAT')

# test
print('wind_speed={}  type={}'.format(wind_speed, type(wind_speed)))
print('wind_gusts={}  type={}'.format(wind_gusts, type(wind_gusts)))


wind_dir_str = ''
if wind_dir is not None:
    if wind_dir in wind_dir_dictionary:
        wind_dir_str = wind_dir_dictionary[wind_dir]

print('WX: rain1h:{} rain24h:{} T={} Rh={} P={} Ubat={}V'.format(rain1, rain24, temp, hum, pressure, ubat))
if (wind_speed is not None) and (wind_gusts is not None) and (wind_dir is not None):
    print('WX: wind dir:{}/{} speed:{}m/s gusts:{}m/s'.format(wind_dir*22.5, wind_dir_str, wind_speed, wind_gusts))
else:
    print('WX: wind dir:{} speed:{} gusts:{}'.format(wind_dir, wind_speed, wind_gusts))

# Съставяне на низа
wsmsg = ''
# Вятър - посока
if wind_dir is None:
    wsmsg += '_...'
else:
    wsmsg += '_{:03d}'.format(int(float(wind_dir) * 22.5))  # (_) посока на вятъра в градуси
# Вятър - скорост
if wind_speed is None:
    wsmsg += '/...'
else:                                                      # Числото върнато от сензора се дели на 10 за да се получат м/с
    wsmsg += '/{:03d}'.format(int(wind_speed * 2.23694))  # (/) сила на вятъра mph = ms * 2.23694
# Вятър - пориви
if wind_gusts is None:
    wsmsg += 'g...'
else:
    wsmsg += 'g{:03d}'.format(int(wind_gusts * 2.23694))  # (g) сила на поривa
# температура
if temp is None:
    wsmsg += 't...'
else:
    wsmsg += 't{:03d}'.format(int(float(temp)*9/5+32))  # (t) Фаренхайт: (1 C x 9/5) + 32 = 33.8 F
# влажност
if hum is None:
    wsmsg += 'h..'
else:
    wsmsg += 'h{:02d}'.format(hum)
# Валеж за последния час
if rain1 is None:
    wsmsg += 'r...'
else:
    # rain1 и rain24 са брой имулси от сензора разделеби на две.
    # За да се преобразуват в мм/м2 се умножават по 0.2791.
    # За да са в стотни от инча за APRS се умножават по 1.0988
    rhi = int((float(rain1) * 1.0988)/2)
    wsmsg += 'r{:03d}'.format(rhi)
    print('rain 1h pulses:{}  hundreds of a inch:{}  mm:{}'.format(rain1, rhi, float(rain1)*0.2791))
# Валеж за последните 24 часа
if rain1 is None:
    wsmsg += 'p...'
else:
    rhi = int((float(rain24) * 1.0988)/2)
    wsmsg += 'p{:03d}'.format(rhi)
    print('rain 24h pulses:{}  hundreds of a inch:{}  mm:{}'.format(rain24, rhi, float(rain1)*0.2791))
# Атмосферно налягане
if pressure is not None:
    wsmsg += 'b{:05d}'.format(pressure * 10)
    
# РТТ, запис в KISSOUT, изчакване да изчезне файла, освобождаване на РТТ.
usb_ptt_on()        
print('APRS WS messag: ', wsmsg)
wsdata = 'LZ2SMX-2>APDW14,WIDE2-2:!4307.46N/02744.14E' + wsmsg + ' Ubat={}V'.format(ubat)
file = open('/home/svilen/ws2/KISSOUT/wsdata','w')
file.write(wsdata)
file.close()
       
while True:
    if not os.listdir('/home/svilen/ws2/KISSOUT'):
        print('is empty')
        break
    else:
        print('not empty')
        time.sleep(1)            
time.sleep(3)
usb_ptt_off()
