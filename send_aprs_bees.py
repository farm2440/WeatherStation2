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
import socket
from datetime import timedelta, datetime
import redis
import os

# TODO: Да се проверява за активни Direwolf и Kissutil преди да се активира РТТ
# релето. Ако процесите не са активни да се изпрати команда за разпадане на
# релето и да не се пращат данни !!!!

tx_period = timedelta(minutes=20, seconds=13)  # Период на изпращане на APRS в секунди
SERIAL_PORT_NAME = '/dev/ttyUSB0'  # Локално реле за РТТ, управлява се по сериен порт с команда
sequence_number = 21

# Коефициенти за APRS EQNS съобщението (0 - 255)
EQA = 0
EQB = 4
EQC = 0  # офсет тегло на празен кошер - плодник, дъно, капак, 10 празни рамки


def weight_to_aprs_parm(weight):
    # Преобразува параметъра weight предаден като низ, който е стойността за теглото на кошера от БД .
    # Ако няма информация то weight  е None. Тогава ще се предаде тегло 0
    # Върнатия параметър е коефициента който се залага в PARM съобщението
    float_weight = 0
    if weight is not None:
        float_weight = float(weight)
    parm = int(((float_weight - EQC) * 10) / EQB)
    return parm


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
    file = open('KISSOUT/telemetrymsg', 'w')
    file.write(msg)
    file.close()
    while True:
        if not os.listdir('KISSOUT'):
            print('KISSOUT is empty')
            break
        else:
            print('KISSOUT not empty')
            time.sleep(1)
    time.sleep(2)
    usb_ptt_off()
    time.sleep(5)


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

dt = datetime.now() - tx_period

while True:
    s_next_bees_tm_tx = str(tx_period - (datetime.now() - dt))[:-7]
    #    print('Time untill next telemetry TX:', s_next_bees_tm_tx)
    rds.set('s_next_bees_tm_tx', value=s_next_bees_tm_tx, ex=5)
    if (datetime.now() - dt) < tx_period:
        time.sleep(1)
        continue

    sequence_number += 1
    if sequence_number > 999:
        sequence_number = 1

    dt = datetime.now()
    print()
    print(datetime.now(), "  Sending bees telemetry APRS... Sequence number:", sequence_number)

    h1_weight = weight_to_aprs_parm(rds.get('h1_weight'))
    h2_weight = weight_to_aprs_parm(rds.get('h2_weight'))
    h3_weight = weight_to_aprs_parm(rds.get('h3_weight'))
    h4_weight = weight_to_aprs_parm(rds.get('h4_weight'))
    h5_weight = weight_to_aprs_parm(rds.get('h5_weight'))


    print('h1_weight:{} h2_weight:{} h3_weight={} '.format(h1_weight, h2_weight, h3_weight))
    print('h4_weight:{} h5_weight:{} '.format(h4_weight, h5_weight))

    # Съставяне на низа
    crdmsg = 'LZ2SMX-3>APDW16,WIDE2-2:!4306.72N/02744.14Ey'
#    parmmsg = 'LZ2SMX-3>APDW16,WIDE2-2::LZ2SMX-3 :PARM.BeeBox1,BeeBox2,BeeBox3,BeeBox4,BeeBox5,B7,B6,B5,B4,B3,B2,B1,B0'
#    unitmsg = 'LZ2SMX-3>APDW16,WIDE2-2::LZ2SMX-3 :UNIT.x100g,x100g,x100g,x100g,x100g,B7,B6,B5,B4,B3,B2,B1,B0'
#    eqnsmsg = 'LZ2SMX-3>APDW16,WIDE2-2::LZ2SMX-3 :EQNS.{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}'.format(EQA,EQB,EQC, EQA,EQB,EQC, EQA,EQB,EQC, EQA,EQB,EQC, EQA,EQB,EQC)
#    bitsmsg = 'LZ2SMX-3>APDW16,WIDE2-2::LZ2SMX-3:BITS.11111111,Internal telemetry'
#    valmsg = 'LZ2SMX-3>APDW16,WIDE2-2:T#{},{},{},{},{},{},00000000'.format(sequence_number, h1_weight, h2_weight, h3_weight, h4_weight, h5_weight)
    parmmsg = 'LZ2SMX-3>APDW16,WIDE2-2::LZ2SMX-3 :PARM.BeeBox1,BeeBox2'
    unitmsg = 'LZ2SMX-3>APDW16,WIDE2-2::LZ2SMX-3 :UNIT.x100g,x100g'
    eqnsmsg = 'LZ2SMX-3>APDW16,WIDE2-2::LZ2SMX-3 :EQNS.{},{},{},{},{},{}'.format(EQA,EQB,EQC, EQA,EQB,EQC)
    bitsmsg = 'LZ2SMX-3>APDW16,WIDE2-2::LZ2SMX-3:BITS.11111111,Internal telemetry'
    valmsg = 'LZ2SMX-3>APDW16,WIDE2-2:T#{},{}'.format(sequence_number, h1_weight, h2_weight)

    print('APRS TM coordinates message: ', crdmsg)
    print('APRS TM PARM message: ', parmmsg)
    print('APRS TM UNIT message: ', unitmsg)
    print('APRS TM EQNS message: ', eqnsmsg)
    print('APRS TM  message: ', valmsg)
    print('Sending APRS messages...')
    send_aprs(crdmsg)
    send_aprs(parmmsg)
    send_aprs(unitmsg)
    send_aprs(eqnsmsg)
    send_aprs(valmsg)
    print('Done! \r\n')
