#!/bin/bash
ping -c 4 192.168.152.1
let a=$?
if [ "$a" = "0" ]; then
  echo "We have connection."
else
  echo "We have lost connection.."
  sudo reboot
  #add command for reboot or restarting networking service here.
fi