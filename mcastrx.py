from socket import *
import datetime
import json

# prepare for multicast receive
mcast_port = 8888
mcast_grp = "224.0.0.120"
#interface_ip = str(INADDR_ANY)
interface_ip = str("0.0.0.0")
s = socket(AF_INET, SOCK_DGRAM)
s.bind(("", mcast_port))
mreq = inet_aton(mcast_grp) + inet_aton(interface_ip)
s.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP, mreq)


# Receive multicast data
print('Waiting for sensor data...')
while 1:
    print()
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
