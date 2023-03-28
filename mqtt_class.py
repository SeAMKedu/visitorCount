import base64

class mqttClass():
    """
    Wrapper class for paho mqtt client.
    """
    def __init__(self, clientID, clean_session = False, qos = 0):
        import datetime
        import paho.mqtt.client as mqtt #import the client1
        import time
        from configparser import ConfigParser
        from queue import Queue
        self.ConfigParser = ConfigParser
        self.datetime = datetime
        self.mqtt = mqtt
        self.time = time
        self.clientID = clientID
        self.topics = []
        self.qos = qos
        self.messageQueue = Queue()
        self.readConfigFile()
        print(f"Creating mqtt instance {self.clientID}")
        if self.webSocket:
            transportProtocol = "websockets"
        else:
            transportProtocol = "tcp"
        print(f"Using {transportProtocol} transport protocol")

        self.client = self.mqtt.Client(self.clientID, clean_session, transport=transportProtocol)

        if self.webSocket:
            self.client.ws_set_options(path="", headers=None)
        self.client.on_message = self.onMessage
        self.client.on_connect = self.onConnect
        self.client.on_disconnect = self.onDisconnect
        self.client.username_pw_set(username=self.token,password="")
        if self.ssl:
            self.client.tls_set()
        
        print(f"{self.clientID} Connecting broker {self.brokerAddress}:{self.port}")
        self.client.connect(self.brokerAddress, self.port, 60)
        self.sendMessage(f"{self.clientID}/connect", str(self.datetime.datetime.now()))
    
    def readConfigFile(self):
        config = self.ConfigParser()
        config_file = 'configuration.ini'
        config.read(config_file)
        self.port = config.getint('mqtt', 'port')
        self.ssl = config.getboolean('mqtt', 'ssl')
        self.webSocket = config.getboolean('mqtt', 'webSocket')
        self.token = config.get('mqtt', 'token')
        self.brokerAddress = config.get('mqtt', 'brokerAddress')
        self.clean_session = config.getboolean('mqtt', 'clean_session')
        self.debugLogging = config.getboolean('debug', 'debugLogging')
       
    def sendMessage(self, topic, message, qos = 0, printOut = True, log = True):
        
        #self.client.publish(topic, message, qos)
        #print(topic, message)
        try:
            if printOut:
                if not log and topic != "pic":
                    message = "***" + str(message)
                self.client.publish(topic, message, qos)
                print(f"\n{self.clientID} \nMQTT message published: \nmessage: {message}\ntopic: {topic}\n")
            else:
                if not log and topic != "pic":
                    message = "***" + str(message)
                self.client.publish(topic, message, qos)
            
        except:
            self.client.reconnect()
            print(self.clientID, "reconnect to broker")
            #self.client.publish(topic, message, qos)
            #print(topic, message)
            """
            if topic != "pic":
                self.client.publish(topic, message, qos)
                print(f"\n{self.clientID} \nMQTT message published after reconnect: topic:{topic}, message: {message}\n")
            else:
                self.client.publish(topic, message, qos)
            """
            if printOut:
                if not log and topic != "pic":
                    message = "***" + str(message)
                self.client.publish(topic, message, qos)
                print(f"\n{self.clientID} \nMQTT message after reconnect published: \nmessage: {message}\ntopic: {topic}\n")
            else:
                if not log and topic != "pic":
                    message = "***" + str(message)
                self.client.publish(topic, message, qos)

    def onDisconnect(self, client, userdata, rc):
        print(f"client {self.clientID} \ndisconnected from broker {self.brokerAddress}\n")
        
    def onMessage(self, client, userdata, message):
        print("mqtt message received. Index of '***' in message: ", message.payload.decode('utf-8').find("***"))
        if message.topic != "pic" and message.payload.decode('utf-8').find("***") != 0: # skip messages that start with non-logging string '***'
            print(f"\n{self.clientID} \nreceived message: {message.payload.decode('utf-8')}\ntopic {message.topic}\n")
            #print(message.qos)
            if self.debugLogging:
                with open("mqttclasslog.log", 'a') as f:
                    f.write(str(self.datetime.datetime.now()) +" - " + message.topic + " - " + str(message.payload.decode('utf-8')) + "\n")

            self.messageQueue.put(message)
        
    
    def startListen(self, topic):
        if not self.client.is_connected():
            print(f"\n{self.clientID} \nwas not connected\n")
            self.client.loop_start()
            self.time.sleep(1)
            print(f"\n{self.clientID} \nloop start\n")
        self.client.subscribe(topic, self.qos)
        self.topics.append(topic)
        self.time.sleep(1)
        #print("subscribe")
        if self.client.is_connected():
            print(f"\n{self.clientID} \nis connected\n")
            #self.client.loop_start()
        
    def stopListen(self):
        self.client.loop_stop() #stop the loop
        print(f"{self.clientID} Loop stopped")
        self.client.disconnect()

    def onConnect(self, client, userdata, flags, rc):
        if rc==0:
            print(f"{self.clientID} connected OK Returned code =",rc)
            self.sendMessage(f"{self.clientID}/loop", str(self.datetime.datetime.now()))
            for topic in self.topics:
                self.client.subscribe(topic, self.qos)

        else:
            print(f"{self.clientID} Bad connection Returned code=",rc)
            
def main():
    import time
    sender = mqttClass(clientID = "Kari")
    print("olio luotu")
    sender.sendMessage("pic", base64.encodebytes(b'\x00\x04\xff\xd9'))
    #sender.sendMessage("test", "jee")
    print("viesti julkaistu")
    sender.startListen("test")
    print("looppi käynnistetty ja kanava tilattu")
    #sender.client.loop_start()
    #sender.client.subscribe("general")
    #sender.client.subscribe("test")
    input() # let's wait user's input before we stop the program
    sender.stopListen()

if __name__ == "__main__":
    main() # just for testing purposes

