import os
import requests
import datetime
import time
url = "https://www.google.com"

timeout = 10

while True:
    time.sleep(timeout)
    try:

        request = requests.get(url, timeout=timeout)

        print(str(datetime.datetime.now()) + " Connected to the Internet")

    except (requests.ConnectionError, requests.Timeout) as exception:

        print(str(datetime.datetime.now()) + " No internet connection.")
        os.system('systemctl reboot -i')
        break