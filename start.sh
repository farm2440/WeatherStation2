#! /bin/bash

cd /home/svilen/ws2

# set clock to 00:00:01 to avoid activating sim900_bee_data.py before  clock is set
sudo date -s '2025-04-15 00:01:30'
sudo /bin/python3 /home/svilen/ws2/sim900_set_time.py 

sleep 60   # wait for network connection

/bin/python3 /home/svilen/ws2/sensor_reader.py &       
/bin/python3 /home/svilen/ws2/web_emit.py &           
sudo /bin/python3 /home/svilen/ws2/web_interface.py &  





