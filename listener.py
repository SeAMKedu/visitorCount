import mqtt_class
import datetime
from disk_functions import write_raw_csv
import time, datetime
from configparser import ConfigParser
import sys

config = ConfigParser()
configFile = 'configuration.ini'
config.read(configFile)


pubList = eval(config.get("mqtt", "detectionPublishers"))
mqttClientSelf = config.get("mqtt", "listener")
reportDelaySeconds = config.getint("files", "writeCSVtoDiskDelay")
dataFile = config.get("files", "raw_log")
debugLogging = config.getboolean('debug', 'debugLogging')
    
subscribedClientIDs = pubList + [mqttClientSelf]
listener = mqtt_class.mqttClass(subscribedClientIDs[-1], qos=2)
if len(sys.argv) > 1:
    if sys.argv[1] == "debug":
        print("Starting in debug mode, subscribing all topics ('#') ")
        listener.startListen("#")
elif debugLogging:
    print("Starting in debug mode, subscribing all topics ('#') ")
    listener.startListen("#")
else:
    for client in subscribedClientIDs:
        listener.startListen(f"{client}/#")
print("Subscribed topics:",listener.topics)
time.sleep(1)

while True:
    write_raw_csv(listener, dataFile)

    time.sleep(reportDelaySeconds)
    
