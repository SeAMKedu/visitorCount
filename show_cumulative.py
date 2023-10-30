import mqtt_class
import datetime
import time, datetime
from configparser import ConfigParser
import sys
import signal
config = ConfigParser()
import cv2
import numpy as np
from drawing_functions import cumulative

configFile = 'configuration.ini'
config.read(configFile)

direction_list = eval(config.get("main", "directions"))
pubList = eval(config.get("mqtt", "detectionPublishers"))
font_color = (255, 255, 255)
font_size = 0.4*8
font_thickness = 1*3

def onMessage2(self, client, userdata, message):
    if message.topic != "pic" and message.payload.decode('utf-8').find("***") != 0: # skip messages that start with non-logging string '***'
        if message.topic == "Kamera1/Sisaan/Ulos/person":
            self.dir1 += 1
        elif message.topic == "Kamera1/Ulos/Sisaan/person":      
            self.dir2 += 1
    #print(self.dir1, self.dir2)

mqtt_class.mqttClass.onMessage = onMessage2 # let's replace original onMessage method with the one given in this script
cumulative_counter = mqtt_class.mqttClass(clientID = "Cumulative")
cumulative_counter.dir1 = 0 # lets add new counter variables to instance of mqttClass
cumulative_counter.dir2 = 0

def handle_sigterm(_signo, _sigframe):
    print(datetime.datetime.now(), "Vehicle count stopped by SIGTERM")
    cumulative_counter.stopListen()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)
for publisher in pubList:
    cumulative_counter.startListen(f"{publisher}/{direction_list[0]}/{direction_list[1]}/person")
    cumulative_counter.startListen(f"{publisher}/{direction_list[1]}/{direction_list[0]}/person")

while True:
    img = np.zeros((600,800,3), dtype=np.uint8)
    cumulative(cv2, img, font_size, font_color, font_thickness,direction_list[0],direction_list[1],cumulative_counter.dir1, cumulative_counter.dir2)
