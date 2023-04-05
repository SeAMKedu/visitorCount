from flask import Flask, render_template, Response, send_from_directory, send_file, request
import threading
import configparser
import time
import os

config = configparser.ConfigParser()
config_file = "configuration.ini"
config.read(config_file)
web_server = config.getboolean('web', 'web_server')
port = config.getint('web', 'port')
template_dir = os.path.abspath('webMQTT')
static_dir = os.path.abspath('webMQTT')
print(template_dir)
app = Flask(__name__, template_folder = template_dir, static_folder = static_dir)

@app.route('/')
def index_page():
    """Video streaming home page."""
    host = request.headers.get('Host').split(":")[0]
    return render_template('index.html', host=host)
    #return 'web app with python flask!'

def main():
    start_web = threading.Thread(target = app.run, kwargs={'host':'0.0.0.0', 'port':port})
    start_web.daemon = True
    if web_server: 
        start_web.start()
    while True:
        time.sleep(3600) # keep script alive


if __name__ == "__main__":
    main()
