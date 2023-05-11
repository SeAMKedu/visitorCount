# Import necessary packages
import base64
from mqtt_class import mqttClass
from drawing_functions import *
from disk_functions import *
import cv2, os
import numpy as np
import datetime
import time
import signal
import sys
from configparser import ConfigParser

import os
import numpy as np
import cv2
from motpy import Detection, MultiObjectTracker
from motpy.testing_viz import draw_detection, draw_track

folder = os.getcwd()+'/'
config = ConfigParser()
config_file = 'configuration.ini'
config.read(config_file)

setup_local_screen = config.getboolean('main', 'setup_local_screen')
save_detection_frames = config.getboolean('main','save_detection_frames')
camera_number = config.getint('main', 'camera_number')
camera_rotate_set = config.getint('main', 'camera_rotate')
resolution = eval(config.get('main', 'resolution'))
crop_square = config.getint('main', 'crop_square')
model_tiny = config.getboolean('main', "model_tiny") # False uses yolov4, True yolov4-tiny network
confThreshold = config.getfloat('main', 'confThreshold')
nmsThreshold = config.getfloat('main', 'nmsThreshold')
#path_length = config.getint('main', 'path_length')
tracers = config.getboolean('main', 'tracers') # Shall we show tracked objects' tracers
lines = config.getboolean('main', 'lines') # Shall we show dividing lines used to determine direction of motion
show_stats = config.getboolean('main', 'show_stats') # Shall we show stats box
required_classes = eval(config.get('main', 'required_classes'))
up_direction = eval(config.get('main', 'directions'))[0] 
down_direction = eval(config.get('main', 'directions'))[1]

mqttClient = eval(config.get('mqtt', 'detectionPublishers'))[0]
setupMqttVideo = config.getboolean('mqtt', 'setupMqttVideo')
mqttVideoInterval = config.getfloat('mqtt', 'mqttVideoInterval')
mqttVideoResolution = config.getint('mqtt', 'mqttVideoResolution')
publish_stats = config.getboolean('mqtt', 'publishMqttStats')

direction = config.get('main', 'direction')
middle_line = config.getfloat('main', 'middle_line')
line_difference = config.getfloat('main', 'line_difference')

model_spec = eval(config.get('main', 'model_spec'))
matching_fn_kwargs = eval(config.get('main', 'matching_fn_kwargs'))
active_tracks_kwargs = eval(config.get('main', 'active_tracks_kwargs'))
tracker_kwargs = eval(config.get('main', 'tracker_kwargs'))
dt = 1 / config.getint('main', 'FPSforDt')
tracker2 = MultiObjectTracker(dt=dt, model_spec=model_spec, matching_fn_kwargs = matching_fn_kwargs, active_tracks_kwargs=active_tracks_kwargs, tracker_kwargs=tracker_kwargs)

# Initialize the videocapture object
camera_rotate = {"set":camera_rotate_set, 0:0, 1:cv2.ROTATE_90_CLOCKWISE, 2:cv2.ROTATE_180, 3:cv2.ROTATE_90_COUNTERCLOCKWISE}
#aspectRatio = resolution[0]/resolution[1]
cap = cv2.VideoCapture(camera_number)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
input_size = 416
font_color = (255, 255, 255)
font_size = 0.4
font_thickness = 1

if crop_square == 0:
    length = min(resolution)
    crop_coord = [int(resolution[0]/2 - length/2), int(resolution[1]/2 - length/2), int(resolution[0]/2 + length/2), int(resolution[1]/2 + length/2)]
    resolution = (length, length)
elif crop_square > 0:
    length = crop_square
    crop_coord = [int(resolution[0]/2 - length/2), int(resolution[1]/2 - length/2), int(resolution[0]/2 + length/2), int(resolution[1]/2 + length/2)]
    resolution = (length, length)
else:
    crop_coord=[0,0,resolution[0],resolution[1]]
aspectRatio = (crop_coord[2]-crop_coord[0])/(crop_coord[3]-crop_coord[1])
middle_line_position, up_line_position, up_line_out_position, down_line_position, down_line_out_position = calculate_line_positions(middle_line, line_difference, resolution, direction)
print("defined cropping coordinates and aspect ratio:",crop_coord, aspectRatio)

# Store Coco Names in a list
print('Folder: '+folder+"coco.names")
classesFile = folder+"coco.names"
classNames = open(classesFile).read().strip().split('\n')

# class index for our required detection classes
required_class_index = []
for item in required_classes:
    required_class_index.append(classNames.index(item))
print("Classes to be followed: ",required_class_index)

## Model Files
if model_tiny:
    modelConfiguration = 'yolov4-tiny.cfg'
    modelWeights = 'yolov4-tiny.weights'

else:
    modelConfiguration = 'yolov4.cfg'
    modelWeights = 'yolov4.weights'

# configure the network model
net = cv2.dnn.readNetFromDarknet(modelConfiguration, modelWeights)

# Configure the network backend
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)

# Define random colour for each class
np.random.seed(42)
colors = np.random.randint(0, 255, size=(len(classNames), 3), dtype='uint8')

# Function for finding the center of a rectangle
def find_center2(xmin, ymin, xmax, ymax):
    cx = int((xmin+xmax)/2)
    cy = int((ymin+ymax)/2)
    return cx, cy

# Function for count vehicle

# List for store vehicle count information
temp_up_list = []
temp_down_list = []

def count_vehicle2(tracks, img):
    global temp_up_list, temp_down_list
    activeIDs = []
    for track in tracks:
        draw_track(img, track)
        #x, y, w, h, id, index = box_id
        xmin, ymin, xmax, ymax, id, index = (track.box[0], track.box[1], track.box[2], track.box[3], track.id, track.class_id)
        # Find the center of the rectangle for detection
        center = find_center2(xmin, ymin, xmax, ymax)
        ix, iy = center
        if direction == "vertical":
            control_coord = ix
        else:
            control_coord = iy
        # Find the current position of the object and determine if it has crossed the control line to some direction.
        print("ylälistalla henkilöitä:", len(temp_up_list), end=", ")
        print("alalistalla henkilöitä:", len(temp_down_list))
        if control_coord < middle_line_position:
            if id not in temp_up_list:
                temp_up_list.append(id)
                
        elif control_coord > middle_line_position:
            if id not in temp_down_list:
                temp_down_list.append(id)
        
        if control_coord < up_line_out_position:
            if id in temp_down_list:
                temp_down_list.remove(id)
                print("alhaalta ylös")
                mqttSender.sendMessage(f"{mqttClient}/{down_direction}/{up_direction}/{classNames[required_class_index[index]]}", str(datetime.datetime.now()), qos = 2)

        elif control_coord > down_line_out_position:
            if id in temp_up_list:
                temp_up_list.remove(id)
                print("ylhäältä alas")
                mqttSender.sendMessage(f"{mqttClient}/{up_direction}/{down_direction}/{classNames[required_class_index[index]]}", str(datetime.datetime.now()), qos = 2)
        activeIDs.append(id)
    temp_up_list = [id for id in temp_up_list if id in activeIDs] # let's clean unused IDs from temp lists
    temp_down_list = [id for id in temp_down_list if id in activeIDs]
        
    mqttSender.sendMessage(f"stats/tempUpList", str([id[:6] for id in temp_up_list]), qos = 0, printOut = False, log = False)
    mqttSender.sendMessage(f"stats/tempDownList", str([id[:6] for id in temp_down_list]), qos = 0, printOut = False, log = False)


    #drawCircle(cv2, img, center, max_distance, up_direction, temp_up_list, down_direction, temp_down_list, font_size, font_color, font_thickness)

def postProcess2(outputs, img):
    required_class_index = [0]
    height, width = img.shape[:2]
    boxes = []
    classIds = []
    confidence_scores = []
    detection = []
    for output in outputs:
        for det in output:
            scores = det[5:]
            classId = np.argmax(scores)
            confidence = scores[classId]

            if classId in required_class_index:
                if confidence > confThreshold:
                    w,h = int(det[2]*width) , int(det[3]*height)
                    x,y = int((det[0]*width)-w/2) , int((det[1]*height)-h/2)
                    boxes.append([x,y,w,h])
                    classIds.append(classId)
                    confidence_scores.append(float(confidence))

    # Apply Non-Max Suppression
    indices = cv2.dnn.NMSBoxes(boxes, confidence_scores, confThreshold, nmsThreshold)
    if len(indices) > 0:
        for i in indices.flatten():
            xmin, ymin, w, h = boxes[i][0], boxes[i][1], boxes[i][2], boxes[i][3]
            detection.append(Detection(box=[xmin, ymin, xmin+w, ymin+h], score=confidence_scores[i], class_id = classIds[i]))

    return detection

def realTime():
    #try:
    mqttVideoTime = time.time()
    i = 0
    if publish_stats: publishStatsGenerator = publishStats(mqttSender)

    while True:
        success, img = cap.read()
        img = img[crop_coord[1]:crop_coord[3], crop_coord[0]:crop_coord[2]]
        if camera_rotate["set"] != 0:
            img = cv2.rotate(img, camera_rotate[camera_rotate["set"]])
        blob = cv2.dnn.blobFromImage(img, 1 / 255, (input_size, input_size), [0, 0, 0], 1, crop=False)
        
        # Set the input of the network
        net.setInput(blob)

        # Find out the unconnected (ie. output) layers of the network
        layersNames = net.getLayerNames()
        outputNames = [(layersNames[i - 1]) for i in net.getUnconnectedOutLayers()]
        
        # Feed data to the network
        outputs = net.forward(outputNames)
    
        # Find the objects from the network output
        detections = postProcess2(outputs, img)
        tracker2.step(detections)
        tracks = tracker2.active_tracks(min_steps_alive=5)
        
        # preview the boxes on frame
        for det in detections:
            draw_detection(img, det)
        
        count_vehicle2(tracks, img) # check possible events and draw tracks

        # Draw tracers
        #if tracers:
            #pass #not implemented


        # Draw the crossing lines
        if lines: drawLines(cv2, up_line_position, up_line_out_position, middle_line_position, down_line_out_position, down_line_position, img, direction)

        # Draw area name texts in the frame
        drawNames(cv2, img, up_direction, down_direction, direction, font_size, font_color, font_thickness)
        
        # Draw counting stats in the frame
        #if show_stats: 
        #    time1 = drawStats(cv2, img, classNames, required_class_index, up_direction, down_direction, up_list, down_list, time1, font_size, font_color, font_thickness)
        if publish_stats : 
            next(publishStatsGenerator)
            
        if save_detection_frames:
            pass #not implemented
            #if detected:
            #    cv2.imwrite(folder+'detections/'+str(datetime.datetime.now())+'.jpg', img)

        # if local screen is to be shown
        if setup_local_screen:
            action = localOutput(cv2, img, font_size, font_color, font_thickness)
            if action == 1:
                #write_raw_csv() deprecated with MQTT   
                break # stop program
            elif action == 2:
                #write_raw_csv() deprecated with MQTT
                pass

        # Convert (encode) image  into streaming data and store it in-memory cache. It is used to compress image data formats in order to make network transfer easier.
        if setupMqttVideo:
            
            if time.time() - mqttVideoTime > mqttVideoInterval:
                img2 = cv2.resize(img, (mqttVideoResolution, int(mqttVideoResolution/aspectRatio)))
                ret, buffer = cv2.imencode('.jpg', img2, [1, 60])
                if setupMqttVideo:
                    img2 = base64.encodebytes(buffer)
                    mqttSender.sendMessage("pic", img2, qos = 0, printOut=False, log = False)
                mqttVideoTime = time.time() 

    # Write the vehicle counting information in a file and save it
    """
    except Exception as ex:
        print(ex)
        write_exceptions_csv(ex, folder)

    finally:    
        # realTime() # keep running
        # Finally send disconnecting MQTT-message, disconnect from MQTT broker, release the capture object and destroy all active windows
        mqttSender.sendMessage(f"{mqttClient}/disconnect",str(datetime.datetime.now()))
        mqttSender.client.disconnect()
        cap.release()
        cv2.destroyAllWindows()"""

def handle_sigterm(_signo, _sigframe):
    print("Vehicle count stopped by SIGTERM")
    mqttSender.sendMessage(f"{mqttClient}/sigterm",str(datetime.datetime.now()))
    mqttSender.stopListen()
    cap.release()
    cv2.destroyAllWindows()
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    if setup_local_screen:
        print("Local screen activated, 'q' terminates program, 'w' writes stats csv")
    
    mqttSender = mqttClass(mqttClient, clean_session = True)
    mqttSender.client.loop_start()
    realTime()
