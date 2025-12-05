import subprocess
import time
import os
from datetime import datetime
import psutil  # required!

# wd_sensor_reader.py - Watchdog script.
# Тази програма стартира процеса за четене от енкодерите sensor_reader.py
# като следи да е пуснат само един процес. Ако процеса крашне тя ще
# го стартира наново. Тази програма трябва да бъде стартирана автоматично
# на Startup

SCRIPT_PATH = r'/home/svilen/ws2/sensor_reader.py'

def is_another_instance_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        # print('proc:', proc)
        # print('  proc.info[pid]=', proc.info['pid'])
        # print('  proc.info[cmdline]=', proc.info['cmdline'])
        if proc.info['pid'] == os.getpid():
            print('Continue on  proc.info[pid]=', proc.info['pid'])
            continue
        if proc.info['cmdline'] and SCRIPT_PATH in ' '.join(proc.info['cmdline']):
            print('proc:', proc)
            print('  proc.info[pid]=', proc.info['pid'])
            print('  proc.info[cmdline]=', proc.info['cmdline'])
            print('RESULT: TRUE')
            return True
    return False

def print_own_process_info():
    pid = os.getpid()
    process = psutil.Process(pid)

    print(f"🆔 PID: {process.pid}")
    print(f"📍 Executable: {process.exe()}")
    print(f"📂 Current Working Directory: {process.cwd()}")
    print(f"🧾 Command Line: {' '.join(process.cmdline())}")
    print(f"👤 Username: {process.username()}")
    print(f"🕒 Created At: {datetime.fromtimestamp(process.create_time())}")
    print(f"🧬 Parent PID: {process.ppid()}")
    print(f"🧠 Memory Usage: {process.memory_info().rss / (1024 ** 2):.2f} MB")
    print(f"⚙️ CPU Usage: {process.cpu_percent(interval=0.1)}%")

def main():
    print_own_process_info()
    while True:
        if not is_another_instance_running():
            try:
                print("Starting script encreader.py...")
                proc = subprocess.Popen(['python', SCRIPT_PATH])
                proc.wait()
                print("Script crashed or exited. Restarting in 5 seconds...")
            except Exception as e:
                print(f"Error starting script: {e}")
        else:
            print("Another instance already running. Waiting 10 seconds.")
        time.sleep(5)

if __name__ == "__main__":
    main()

