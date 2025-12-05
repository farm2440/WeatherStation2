# sensor_reader.py получава multicast данните от различни сензори и ги съхранява в  БД Redis като
# при това задава и времето им на живот. Така се поддържат записи само за актуални данни.
# Всички останали приложения (APRS, Web, MQTT.. ) потребяват данните като ги извличат от БД.

import json
import time
from socket import *
import datetime
import redis
import statistics
from statistics import mode  # For wind direction calculation
import os

# Redis records are strings in format  key:value like T1:23  Rh1:43
db_record_expire = 30 * 60   # Expire time for records in Redis. 
dht_sensors = {
#    "48:55:19:0C:4A:54": {"id": "0C4A54", "temp": "T1", "hum": "Rh1", "flag": "B0"}, # Т1  Гараж - има и сензор за светлина 0-осветен, 1-тъмен
    "2C:F4:32:49:D4:9B": {"id": "0B72BE", "temp": "T1", "hum": "Rh1", "flag": "B0"}, # Т1  Гараж - има и сензор за светлина 0-осветен, 1-тъмен
    "48:55:19:0B:6C:C6": {"id": "0B6CC6", "temp": "T2", "hum": "Rh2"}, # Т2 Маза * 
    "C8:C9:A3:54:BC:0F": {"id": "54BC0F", "temp": "T3", "hum": "Rh3"}, # Т3 Стая етаж 1
    "48:55:19:12:C6:BE": {"id": "12C6BE", "temp": "T4", "hum": "Rh4"}, # (Rh too high) Т4 Предверие етаж 1 * # Сива кутия, бял адаптер 48:55:19:12:C6:BE
    "48:55:19:0C:41:C3": {"id": "0C41C3", "temp": "T5", "hum": "Rh5"}, # (Rh too low) Т5 Кухня *
#    "48:55:19:0C:4A:54": {"id": "0C4A54", "temp": "T6", "hum": "Rh6", "flag": "B1"},  # Т6 Баня , флагът В1 не се ползва и сензора не изпраща флаг
#   "n.a.": {"id": "", "temp": "T7", "hum": "Rh7"}, # Т7 Коридор
    "E8:9F:6D:87:E3:B6": {"id": "87E3B6", "temp": "T8", "hum": "Rh8"}  # Т8 Таван *
#   "n.a.": {"id": "", "temp": "T9", "hum": "Rh9"}, # Т9 спалня юг
#   "n.a.": {"id": "", "temp": "T10", "hum": "Rh10"}, # Т10 спалня изток
# * - Telemetry
}

weight_sensors = {
    "64:E8:33:B5:A5:90": "h1_weight",  # Тегло на кошер 1
    "64:E8:33:B6:B3:3C": "h2_weight"  # Тегло на кошер 2
}

rain_sample_counter = 0
# average wind direction and speed over last WIND_AVERAGED values stored in wind_dir_samples[] and wind_speed_samples[]
WIND_SPEED_AVERAGED = 10 # метео сензора (платка с PSoC) предава на ~ 30 сек.
WIND_DIR_AVERAGED = 30
wind_speed_samples = []
wind_dir_samples = []

# prepare for multicast receive
mcast_port = 8888
mcast_grp = "224.0.0.120"
#interface_ip = str(INADDR_ANY)
#interface_ip = str("0.0.0.0")
interface_ip = str("192.168.152.90")
s = socket(AF_INET, SOCK_DGRAM)
s.bind(("", mcast_port))
mreq = inet_aton(mcast_grp) + inet_aton(interface_ip)
s.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP, mreq)

pid = os.getpid()
print("sensor_reader.py PID:", pid)
now = datetime.datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
log_file = "./log/sensor_reader.log"
with open(log_file, "a") as file:
    file.write(f"PID:{pid}\n")
    file.write(f"Current date-time: {timestamp}\n")

# Connect to Redis - database for buffer store of sensor data
rds = redis.Redis(host='localhost', port=6379, decode_responses=True)
# Не тръгва докато няма връзка с БД
while True:
    try:
        rds.ping()
        break
    except (redis.exceptions.ConnectionError, ConnectionRefusedError):
        print("Redis connection error!")
        time.sleep(5)
        continue
# rds.flushall()

# Receive multicast data
print('Waiting for sensor data...')
while 1:
    # wait for multicast packet
    data, address = s.recvfrom(1024)
    dt = datetime.datetime.now()
    print(dt, ' ', data)

    # extract data as JSON
    jsData = None
    try:
        jsData = json.loads(data)
    except ValueError as ex:
        print('Not valid JSON.')
        continue
    # Parse and store in DB
    print(jsData)
    try:
        rds.ping()
    except (redis.exceptions.ConnectionError, ConnectionRefusedError):
        print("Redis connection error!")
        # TODO: Log error and exit or reboot
        continue
    if 'device' in jsData:
        # Data from DHT sensors
        # {"device":"DHT22", "mac":"48:55:19:0B:72:BE", "hum":"36", "temp":"26"}
        if jsData['device'] == 'DHT22':
            mac = jsData['mac']
            if mac in dht_sensors:
                k = dht_sensors[mac]['temp']
                v = jsData['temp']
                if v.isdigit():
                    # Sensor may return 'n.a.' string instead of value for temp/hum
                    rds.set(k, value=v, ex=db_record_expire)
                print('{} : {}'.format(k, v))
                k = dht_sensors[mac]['hum']
                v = jsData['hum']
                if v.isdigit():
                    rds.set(k, value=v, ex=db_record_expire)
                print('{} : {}'.format(k, v))
                # flag
                if "flag" in jsData:
                    if "flag" in dht_sensors[mac]:
                        k = dht_sensors[mac]['flag']
                        v = jsData['flag']
                        rds.set(k, value=v, ex=db_record_expire)
                        print('{} : {}'.format(k, v))
                    else:
                        print("WARNING: Sensor ", dht_sensors[mac]['id'], " is sending flag but it's not used.")
            else:
                print('Device of type DHT22 is not in dht_sensors! MAC:', mac)
        # Data from weight sensor
        # {'device': 'HX711', 'mac': '08:F9:E0:75:BB:3D', 'weight': '-0.031'}
        if jsData['device'] == 'HX711':
            mac = jsData['mac']
            if mac in weight_sensors:
                k = weight_sensors[mac]
                v = jsData['weight']  # тегло в грамове
                print('{} : {}'.format(k, v))
                rds.set(k, value=v, ex=db_record_expire)
            else:
                print('Device of type HX711 is not in weight_sensors! MAC:', mac)
        # Weather station: outside temperature, humidity, rain dir/speed, rain sensor pulses
        # {"device":"WX","temp":25, "hum":28, "pressure":996 ,"wind:dir": -1, "wind:speed":-1,"rain":0,"UBAT":12.336 }
        if jsData['device'] == 'WX':
            # Temperature, humidity and atm. pressure
            # Ако сензора за влага/температура не може да бъде прочетен PSoC връща -100
            v = jsData['temp']
            if v != -100:
                rds.set('WX:temp', value=str(v), ex=db_record_expire)
            print('WX:temp : {}'.format(v))
            v = jsData['hum']
            if v != -100:
                rds.set('WX:hum', value=str(v), ex=db_record_expire)
            print('WX:hum : {}'.format(v))
            tbmp = jsData['tbmp']
            pressure = jsData['pressure']  
            patm = pressure - int(round((tbmp-20)/4))  # тази корекция се налага заради наблюдавана температурна нестабилност на показанието за налягане
            print('WX:pressure : {}  WX:tbmp : {} Atm.Pressure : {}'.format(pressure, tbmp, patm))
            if tbmp>-40 and tbmp<85:
                if patm >800 and patm<1100:
                    rds.set('WX:pressure', value=str(patm), ex=db_record_expire)
            
            # Wind - averaged speed and gusts
            v = jsData['wind:speed']
            print('WX:wind:speed : {} km/h'.format((v*3.6)/10))
            print('WX:wind:speed : {} m/s'.format(v/10))
            if v != -1:
                wind_speed_samples.append(v) # Speed is in m/s * 10
                if len(wind_speed_samples) > WIND_SPEED_AVERAGED:
                    wind_speed_samples.pop(0)
                avg_wind_speed = (sum(wind_speed_samples) / len(wind_speed_samples)) * 0.1  # avg_wind_speed in m/s
                avg_wind_speed = round(avg_wind_speed, 1)
                wind_gusts = max(wind_speed_samples) * 0.1 # in m/s
                wind_gusts = round(wind_gusts, 1)
                rds.set('WX:wind:speed', value=str(avg_wind_speed), ex=db_record_expire)
                rds.set('WX:wind:gusts', value=str(wind_gusts), ex=db_record_expire)
                print('Wind speed samples:{} . Average:{} Gusts:{}'.format(wind_speed_samples, avg_wind_speed, wind_gusts))
            # Wind - averaged direction
            v = jsData['wind:dir']
            print('WX:wind:dir : {}'.format(v))
            if v != -1:
                wind_dir_samples.append(v)
                if len(wind_dir_samples) > WIND_DIR_AVERAGED:
                    wind_dir_samples.pop(0)
                # Find the most common wind direction in the list of samples
                v = mode(wind_dir_samples)
                rds.set('WX:wind:dir', value=str(v), ex=db_record_expire)
                print('Wind dir samples:{} . Most common:{}'.format(wind_dir_samples, v))
            # Rain
            v = jsData['rain']
            print('WX:rain : ', v)
            if v != 0:
                rain_sample_counter += 1
                k = 'WX:rain1h:{}'.format(rain_sample_counter)
                rds.set(k, value=str(v), ex=60*60)
                k = 'WX:rain24h:{}'.format(rain_sample_counter)
                rds.set(k, value=str(v), ex=60*60*24)
            # Battery voltage
            v = jsData['UBAT']
            rds.set('WX:UBAT', value=str(v), ex=db_record_expire)
            print('{} : {}'.format('WX:UBAT : ', v))
 
