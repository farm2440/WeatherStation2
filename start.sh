#! /bin/bash

cd /home/svilen/ws2
# sudo date -s '2025-04-15 00:01:30'
sleep 10   # wait for network connection
# watchdog скриптовете ще пуснат sensor_reader.py и web_emit.py и ще ги рестартират ако крашнат
/bin/python3 /home/svilen/ws2/wd_sensor_reader.py &
/bin/python3 /home/svilen/ws2/wd_web_emit.py &

sudo /bin/python3 /home/svilen/ws2/web_interface.py &





