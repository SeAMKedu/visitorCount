import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mqtt_class
import json
import json2html
import time, datetime
from configparser import ConfigParser

class emailSender():
    def __init__(self, receiver_email, sender_email, smtp_server, port, user, password, messageSubject, topic, debugLogging):
        self.receiver_email = receiver_email
        self.sender_email = sender_email
        self.smtp_server = smtp_server
        self.port = port
        self.user = user
        self.password = password
        self.messageSubject = messageSubject
        self.mqttListener = mqtt_class.mqttClass(f"email_sender_{str(topic)}", qos = 2)
        self.mqttListener.client.on_message = self.onMessage2
        self.topic = topic
        self.debugLogging = debugLogging
        self.mqttListener.startListen(self.topic)
        if not debugLogging:
            self.htmlMessage = f"<html><body><h1>Emailing agent started</h1><p>Emailing agent for topic {self.topic} was started at {time.asctime()}</p></body></html>"
            self.textMessage = f"Emailing agent for topic {self.topic} was started at {time.asctime()}"
            self.buildEmailMessage()
            self.sendEmail() # Send greeting email to receiver to acknowledge the started reporting

    def onMessage2(self, client, userdata, message):
        print("\nstats message received:\n",message.payload.decode("utf-8"))
        print(f"stats message topic: {message.topic}\n")
        #if self.debugLogging:
        with open("emailinglog.log", "a", encoding="utf-8") as f:
            f.write(str(datetime.datetime.now())+" - " + str(message.topic) + " - " + str(message.payload.decode("utf-8")) + "\n")
        self.parseEmailMessage(message.payload.decode("utf-8"))
        self.buildEmailMessage()
        self.sendEmail()

    def parseTextTable(self, messageString):
        try:
            a = json.loads(messageString)
            returnText=str(a["tietoa raportista"]["tilaston tyyppi"])
            for index, timeStamp in enumerate(a["henkilö"].keys()):
                if index == 0:
                    for element in a["henkilö"][timeStamp].keys():
                        text = "\n" + timeStamp + " " + element + " " + str(a["henkilö"][timeStamp][element]) 
                        returnText += text
                else:
                    returnText += "\n\n" + timeStamp
                    for element in a["henkilö"][timeStamp].keys():
                        returnText += "\n         " + element + ": " + str(a["henkilö"][timeStamp][element])
        except Exception as e:
            print(f"In {self.topic} There was an error while parsing text email:{e}")
            returnText = "Plain text version was not parsed."        
        return(returnText)

    def buildEmailMessage(self):
        self.emailMessage = MIMEMultipart("alternative")
        self.emailMessage["Subject"] = self.messageSubject
        self.emailMessage["From"] = self.sender_email
        self.emailMessage["To"] = self.receiver_email

        # Turn these into plain/html MIMEText objects
        part1 = MIMEText(self.textMessage, "plain")
        part2 = MIMEText(self.htmlMessage, "html")
        
        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        self.emailMessage.attach(part1)
        self.emailMessage.attach(part2)
    
    def parseEmailMessage(self, messageString):
        html = json2html.json2html.convert(json = messageString)
        text = self.parseTextTable(messageString)
        self.textMessage = f"""\
        Raport \
        {text}\
        """
        self.htmlMessage = f"""\
        <html>
        <body>
            <h1>Report</h1>
            {html}
        </body>
        </html>
        """
    
    def sendEmail(self):
        # Create a secure SSL context
            context = ssl.create_default_context()

        # Try to log in to server and send email
            try:
                server = smtplib.SMTP(self.smtp_server, self.port)
                server.ehlo() # Can be omitted
                server.starttls(context=context) # Secure the connection
                server.ehlo() # Can be omitted
                server.login(self.sender_email, self.password)
                
                server.sendmail(self.sender_email, self.receiver_email, self.emailMessage.as_string())
                print(self.messageSubject, "was sent to", self.receiver_email)
            
            except Exception as e:
                print(e)
                now = datetime.datetime.now()
                with open(f"reports/{datetime.datetime.strftime(now, '%Y-%m-%d-%H_%M')}-{self.messageSubject}-error-report.txt", "w", encoding="utf-8") as f:
                    f.write(f"{str(now)} {e}")
            else:
                now = datetime.datetime.now()
                print(f"Saving {self.messageSubject} html report to disk at {now}")
                with open(f"reports/{datetime.datetime.strftime(now, '%Y-%m-%d-%H_%M')}-{self.messageSubject}-report.html", "w", encoding="utf-8") as f:
                    f.write(self.htmlMessage)
                    print(f"{self.messageSubject} Saved")

            finally:
                server.quit()     

def main():
    config = ConfigParser()
    config_file = 'configuration.ini'
    config.read(config_file)
    receiver_email = config.get('email', 'receiver_email')
    sender_email = config.get('email', 'sender_email') 
    smtp = config.get('email', 'smtp') 
    port = config.getint('email', 'port')
    user = config.get('email', 'user')
    password = config.get('email', 'password')
    debugLogging = config.getboolean('debug', 'debugLogging')
    subjects = eval(config.get("email", "subjects"))
    topics = eval(config.get("mqtt", "statsTopics"))
    emailers = []
    for i in range(len(topics) if not debugLogging else 1): # instantiate needed email sender objects
        emailers.append(emailSender(receiver_email, sender_email, smtp, port, user, password, subjects[i], topics[i], debugLogging))
        time.sleep(10)
    #input() # stop script with any key
    while True:
        time.sleep(3600) # just to keep things looping.

if __name__ == "__main__":
    main()


