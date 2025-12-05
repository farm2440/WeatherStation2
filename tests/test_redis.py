# Тестово приложение за извличане на записи от БД Redis.
# sensor_reader.py получава multicast данните от различни сензори и ги съхранява в  БД Redis като
# при това задава и времето им на живот. Така се поддържат записи само за актуални данни.
# Всички останали приложения (APRS, Web, MQTT.. ) потребяват данните като ги извличат от БД.

import redis
rds = redis.Redis(host='localhost', port=6379, decode_responses=True)

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

# Извличане на записите на дъжд за последните 24 часа
# Всеки път когато има отчет за импулси от сензора за дъжд се правят два записа в БД. Единия е с трайност
# един часи и втория с трайност 24 часа. При извличане записите се сумират за получаване на резултата за валежа.
print('Rain for the last 24 hours:')
rain24 = 0
cursor = 0
keys = []
while True:
    # При извличане на множество записи от БД се вика функцията scan като първоначално се задава параметъра
    # cursor=0 . Функцията връща нова стойност за cursor с която става следващото извикване. Не е гарантирано
    # с едно викане на scan колко записа ще се извлекат наведнъж. Извикването става до връщане на стойност
    # за cursor нула. Това показва, че всички записи са извлечени.
    result = rds.scan(cursor, match='WH:rain24h:*')
    print('cursor:{} result:{}'.format(cursor, result))
    cursor = result[0]
    keys += result[1]
    if cursor == 0:
        break
print('keys:', keys)

for k in keys:
    print('v:', int(rds.get(k)))
    rain24 += int(rds.get(k))

print('Rain for the last one hour:')
rain1 = 0
cursor = 0
keys = []
while True:
    result = rds.scan(cursor, match='WH:rain1h:*')
    print('cursor:{} result:{}'.format(cursor, result))
    cursor = result[0]
    keys += result[1]
    if cursor == 0:
        break
print('keys:', keys)

for k in keys:
    print(' ', int(rds.get(k)), end=' ')
    rain1 += int(rds.get(k))
print()
temp = rds.get('WX:temp')
hum = rds.get('WX:hum')
pressure = rds.get('WX:pressure')
wind_dir = rds.get('WH:wind:dir')
wind_speed = rds.get('WH:wind:speed')
ubat = rds.get('WH:UBAT')
print('WX: rain1h:{} rain24h:{} T={} Rh={} P={} Ubat={}V'.format( rain1, rain24, temp, hum, pressure, ubat))
if wind_dir is not None:
    if wind_speed is not None:
        print('WX: wind:dir:{} wind:speed{} '.format(wind_dir_dictionary[wind_dir], wind_speed))

# Извличане на данни от DHT сензори:
print('DHT sensors:')
print('T1:{}  Rh1:{}'.format(rds.get('T1'), rds.get('Rh1')))
print('T2:{}  Rh2:{}'.format(rds.get('T2'), rds.get('Rh2')))
print('T3:{}  Rh3:{}'.format(rds.get('T3'), rds.get('Rh3')))