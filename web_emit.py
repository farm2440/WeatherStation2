# https://github.com/MaxHalford/flask-sse-no-deps !!!!!
import time
from datetime import datetime
import requests
import threading
import os
import redis

test_counter = 1

# web_emit.py извлича от Redis параметри и ги изпраща по SSE към уеб интерфейса

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

wind_dir_dictionary = {
    0: "N",
    1: "NNE",
    2: "NE",
    3: "ENE",
    4: "E",
    5: "ESE",
    6: "SE",
    7: "SSE",
    8: "S",
    9: "SSW",
    10: "SW",
    11: "WSW",
    12: "W",
    13: "WNW",
    14: "NW",
    15: "NNW"
}

def posting_thread(msg):
    try:
        requests.post('http://127.0.0.1:80/stream', data=msg)
    except Exception as expost:
        print('ERR:Post failed! Exception:', expost.__class__.__name__)


if __name__ == '__main__':
    pid = os.getpid()
    print("web_emit.py PID:", pid)
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    log_file = "./log/web_emit.log"
    with open(log_file, "a") as file:
        file.write(f"PID:{pid}\n")
        file.write(f"Current date-time: {timestamp}\n")

    while True:
# ============ Изпращане на метео данни =============
        # Извличане на записите на дъжд за последните 24 часа
        # Всеки път когато има отчет за импулси от сензора за дъжд се правят два записа в БД. Единия е с трайност
        # един часи и втория с трайност 24 часа. При извличане записите се сумират за получаване на резултата за валежа.
        # При извличане на множество записи от БД се вика функцията scan като първоначално се задава параметъра
        # cursor=0 . Функцията връща нова стойност за cursor с която става следващото извикване. Не е гарантирано
        # с едно викане на scan колко записа ще се извлекат наведнъж. Извикването става до връщане на стойност
        # за cursor нула. Това показва, че всички записи са извлечени.
        # Сензорът на DF Robots отчита един импулс за 0.28мм/м2 дъжд.
        # https://www.dfrobot.com/product-2689.html
        # https://wiki.dfrobot.com/SKU_SEN0575_Gravity_Rainfall_Sensor
        print()
        print(datetime.now())
        # Дъжд за последните 24 часа
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
            v = rds.get(k)
            if v is None:
                continue
            rain24 += int(v)  # брой импулси от сензора
        rain24_mm = round(float(rain24)*0.28)
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
            v = rds.get(k)
            if v is None:
                continue
            rain1 += int(v)   # брой импулси от сензора
        rain1_mm = round(float(rain1)*0.28)            
        # Други метео данни
        int_or_none = lambda x: None if x is None else int(x)
        temp = int_or_none(rds.get('WX:temp'))
        hum = int_or_none(rds.get('WX:hum'))
        pressure = int_or_none(rds.get('WX:pressure'))
        wind_dir = int_or_none(rds.get('WX:wind:dir'))
        wind_speed = int_or_none(rds.get('WX:wind:speed'))
        wind_gusts = int_or_none(rds.get('WX:wind:gusts'))
        ubat = rds.get('WX:UBAT')
        # Посоката на вятъра се показва като градуси и букви : 160(SSE)
        if wind_dir is not None:
            s_wind_dir = str(wind_dir * 22.5) + ' (' + wind_dir_dictionary[wind_dir] + ')'
        else:
            s_wind_dir = 'None'
        print('WX: rain1h:{}mm/{}pulses rain24h:{}mm/{}pulses T={} Rh={} P={} Ubat={}V'.format(rain1_mm, rain1, rain24_mm, rain24, temp, hum, pressure, ubat))
        print('WX: wind dir:{} speed:{} gusts:{}'.format(s_wind_dir, wind_speed, wind_gusts))
        # Подготовка на JSON съобщението с метео данни
        meteo_json = '''{{ "type":"meteo", "rain24":"{}", "rain1":"{}", "T":"{}", "Rh":"{}", "P":"{}", "Ubat":"{}", "dir":"{}", "speed":"{}", "gusts":"{}" }}'''.format(rain24_mm, rain1_mm, temp, hum, pressure, ubat, s_wind_dir, wind_speed, wind_gusts)
        print('METEO JSON: ', meteo_json)
        # Изпращане на съобщението
        try:
            thr = threading.Thread(target=posting_thread, args=(meteo_json,))
            thr.start()
        except Exception as ex:
            print('ERR: Unable to stream data to web server! Exception:', ex.__class__.__name__)
# ============ Изпращане на дата и час =============
        now_json = '''{{ "type":"now", "now":"{}" }}'''.format(str(datetime.now())[:19])
        print('DATETIME JSON: ', now_json)
        # Изпращане на съобщението
        try:
            thr = threading.Thread(target=posting_thread, args=(now_json,))
            thr.start()
        except Exception as ex:
            print('ERR: Unable to stream data to web server! Exception:', ex.__class__.__name__)
        
# ============= Изпращане на телеметрия =============
# Извличане на данни от DHT сензори:
        T1 = rds.get('T1')
        T2 = rds.get('T2')
        T3 = rds.get('T3')
        T4 = rds.get('T4')
        T5 = rds.get('T5')
        T6 = rds.get('T6')
        T7 = rds.get('T7')
        T8 = rds.get('T8')
        T9 = rds.get('T9')
        T10 = rds.get('T10')
        Rh1 = rds.get('Rh1')
        Rh2 = rds.get('Rh2')
        Rh3 = rds.get('Rh3')
        Rh4 = rds.get('Rh4')
        Rh5 = rds.get('Rh5')
        Rh6 = rds.get('Rh6')
        Rh7 = rds.get('Rh7')
        Rh8 = rds.get('Rh8')
        Rh9 = rds.get('Rh9')
        Rh10 = rds.get('Rh10')
        L1 = rds.get('L1')
        # Подготовка на JSON съобщението с телеметрия данни
        tele_json = '''{{ "type":"tele", "T1":"{}", "Rh1":"{}", "T2":"{}", "Rh2":"{}", "T3":"{}", "Rh3":"{}", "T4":"{}", "Rh4":"{}", "T5":"{}", "Rh5":"{}" }}'''.format(
            T1, Rh1, T2, Rh2, T3, Rh3, T4, Rh4, T5, Rh5)
        print('TELEMETRY JSON: ', tele_json)
        # Изпращане на съобщението
        try:
            thr = threading.Thread(target=posting_thread, args=(tele_json,))
            thr.start()
        except Exception as ex:
            print('ERR: Unable to stream data to web server! Exception:', ex.__class__.__name__)

        # Подготовка на JSON съобщението с телеметрия данни
        tele_json = '''{{ "type":"tele", "T6":"{}", "Rh6":"{}", "T7":"{}", "Rh7":"{}", "T8":"{}", "Rh8":"{}", "T9":"{}", "Rh9":"{}", "T10":"{}", "Rh10":"{}" }}'''.format(
            T6, Rh6, T7, Rh7, T8, Rh8, T9, Rh9, T10, Rh10)
        print('TELEMETRY JSON: ', tele_json)
        # Изпращане на съобщението
        try:
            thr = threading.Thread(target=posting_thread, args=(tele_json,))
            thr.start()
        except Exception as ex:
            print('ERR: Unable to stream data to web server! Exception:', ex.__class__.__name__)

        # Подготовка на JSON съобщението с телеметрия данни
        tele_json = '''{{ "type":"tele", "L1":"{}" }}'''.format(L1)
        print('TELEMETRY JSON: ', tele_json)
        # Изпращане на съобщението
        try:
            thr = threading.Thread(target=posting_thread, args=(tele_json,))
            thr.start()
        except Exception as ex:
            print('ERR: Unable to stream data to web server! Exception:', ex.__class__.__name__)
# ============= Изпращане на данни от APRS =============
        # TODO: Данните се вземат от KISSIN папка: kissutil -o KISSIN -f KISSOUT
        aprs_rx_files = os.listdir('./KISSIN')
        for rxfile_name in aprs_rx_files:
            try:
                rxfile = open('./KISSIN/' + rxfile_name,'r')
                aprs_line = rxfile.readline()
                aprs_json = '{{ "type":"aprs", "msg":"{}"}}'.format(aprs_line.strip())
                print(aprs_json)
                # oбработения файл се изтрива
            except Exception as ex:
                print('ERR: Failed reading APRS Rx file ' + rxfile_name)
                print('ERR: exception: ', str(ex))
            finally:                
                rxfile.close()
                os.remove('./KISSIN/' + rxfile_name)
            # Изпращане на съобщението
            try:
                thr = threading.Thread(target=posting_thread, args=(aprs_json,))
                thr.start()
            except Exception as ex:
                print('ERR: Unable to stream data to web server! Exception:', ex.__class__.__name__)

# ============= Изпращане на данни от кошерите =============
        # Кошер 1
        h1_temp = rds.get('h1_temp')
        h1_hum = rds.get('h1_hum')
        h1_weight = rds.get('h1_weight')
        # Кошер 2
        h2_temp = rds.get('h2_temp')
        h2_hum = rds.get('h2_hum')
        h2_weight = rds.get('h2_weight')
        # Кошер 3
        h3_temp = rds.get('h3_temp')
        h3_hum = rds.get('h3_hum')
        h3_weight = rds.get('h3_weight')
        # Подготовка на JSON съобщението с данни за кошер 1
        bees_json = '''{{ "type":"bees", "h1_temp":"{}", "h1_hum":"{}", "h1_weight":"{}" }}'''.format(
            h1_temp, h1_hum, h1_weight)
        print('BEES JSON: ', bees_json)
        # Изпращане на съобщението
        try:
            thr = threading.Thread(target=posting_thread, args=(bees_json,))
            thr.start()
        except Exception as ex:
            print('ERR: Unable to stream data to web server! Exception:', ex.__class__.__name__)
        # Подготовка на JSON съобщението с данни за кошер 2
        bees_json = '''{{ "type":"bees", "h2_temp":"{}", "h2_hum":"{}", "h2_weight":"{}" }}'''.format(
            h2_temp, h2_hum, h2_weight)
        print('BEES JSON: ', bees_json)
        # Изпращане на съобщението
        try:
            thr = threading.Thread(target=posting_thread, args=(bees_json,))
            thr.start()
        except Exception as ex:
            print('ERR: Unable to stream data to web server! Exception:', ex.__class__.__name__)
        # Подготовка на JSON съобщението с данни за кошер 3
        bees_json = '''{{ "type":"bees", "h3_temp":"{}", "h3_hum":"{}", "h3_weight":"{}" }}'''.format(
            h3_temp, h3_hum, h3_weight)
        print('BEES JSON: ', bees_json)
        # Изпращане на съобщението
        try:
            thr = threading.Thread(target=posting_thread, args=(bees_json,))
            thr.start()
        except Exception as ex:
            print('ERR: Unable to stream data to web server! Exception:', ex.__class__.__name__)
        time.sleep(5)
