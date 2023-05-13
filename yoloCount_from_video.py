# Import necessary packages
import base64
from mqtt_class import mqttClass
from drawing_functions import *
from disk_functions import *
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

global model_spec, matching_fn_kwargs, active_tracks_kwargs, tracker_kwargs, confThreshold, nmsThreshold, tracker2

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
aspectRatio = resolution[0]/resolution[1]

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
up_list = [0 for x in range(len(required_class_index))]
down_list = [0 for x in range(len(required_class_index))]

def count_vehicle2(tracks, img):
    global temp_up_list, temp_down_list
    activeIDs = []
    for track in tracks:
        draw_track(img, track)
        xmin, ymin, xmax, ymax, id, index = (track.box[0], track.box[1], track.box[2], track.box[3], track.id, track.class_id)
        # Find the center of the rectangle for detection
        center = find_center2(xmin, ymin, xmax, ymax)
        ix, iy = center
        if direction == "vertical":
            control_coord = ix
        else:
            control_coord = iy
        # Find the current position of the object and determine if it has crossed the control line to some direction.
        #print("ylälistalla henkilöitä:", len(temp_up_list), end=", ")
        #print("alalistalla henkilöitä:", len(temp_down_list))
        if control_coord < middle_line_position:
            if id not in temp_up_list:
                temp_up_list.append(id)
                
        elif control_coord > middle_line_position:
            if id not in temp_down_list:
                temp_down_list.append(id)
        
        if control_coord < up_line_out_position:
            if id in temp_down_list:
                temp_down_list.remove(id)
                mqttSender.sendMessage(f"{mqttClient}/{down_direction}/{up_direction}/{classNames[index]}", str(datetime.datetime.now()), qos = 2)
                up_list[required_class_index.index(index)] += 1

        elif control_coord > down_line_out_position:
            if id in temp_up_list:
                temp_up_list.remove(id)
                mqttSender.sendMessage(f"{mqttClient}/{up_direction}/{down_direction}/{classNames[index]}", str(datetime.datetime.now()), qos = 2)
                down_list[required_class_index.index(index)] += 1

        activeIDs.append(id)
    temp_up_list = [id for id in temp_up_list if id in activeIDs] # let's clean unused IDs from temp lists
    temp_down_list = [id for id in temp_down_list if id in activeIDs]
        
    mqttSender.sendMessage(f"stats/tempUpList", str([id[:6] for id in temp_up_list]), qos = 0, printOut = False, log = False)
    mqttSender.sendMessage(f"stats/tempDownList", str([id[:6] for id in temp_down_list]), qos = 0, printOut = False, log = False)


    #drawCircle(cv2, img, center, max_distance, up_direction, temp_up_list, down_direction, temp_down_list, font_size, font_color, font_thickness)

def postProcess2(outputs, img):
    #required_class_index = [0]
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

def on_change_nms(value):
    global nmsThreshold
    nmsThreshold = value/100

def on_change_conf(value):
    global confThreshold
    confThreshold = value/100

def on_change_qvar(value):
    global model_spec, tracker2
    model_spec['q_var_pos'] = value/10
    tracker2 = MultiObjectTracker(dt=dt, model_spec=model_spec, matching_fn_kwargs = matching_fn_kwargs, active_tracks_kwargs=active_tracks_kwargs, tracker_kwargs=tracker_kwargs)
    print('q_var_pos =', value/10)
def on_change_rvar(value):
    global model_spec
    model_spec['r_var_pos'] = value/1000
    tracker2 = MultiObjectTracker(dt=dt, model_spec=model_spec, matching_fn_kwargs = matching_fn_kwargs, active_tracks_kwargs=active_tracks_kwargs, tracker_kwargs=tracker_kwargs)
    print('r_var_pos =', value/1000)

def on_change_miniou(value):
    global matching_fn_kwargs, tracker2
    matching_fn_kwargs['min_iou'] = value/100
    tracker2 = MultiObjectTracker(dt=dt, model_spec=model_spec, matching_fn_kwargs = matching_fn_kwargs, active_tracks_kwargs=active_tracks_kwargs, tracker_kwargs=tracker_kwargs)
    print('min_iou =', value/100)

def on_change_multiminiou(value):
    global matching_fn_kwargs, tracker2
    matching_fn_kwargs['multi_match_min_iou'] = value/100
    tracker2 = MultiObjectTracker(dt=dt, model_spec=model_spec, matching_fn_kwargs = matching_fn_kwargs, active_tracks_kwargs=active_tracks_kwargs, tracker_kwargs=tracker_kwargs)
    print('multi_match_min_iou =', value/100)
    
def on_change_minsteps(value):
    global active_tracks_kwargs, tracker2
    active_tracks_kwargs['min_steps_alive'] = value
    tracker2 = MultiObjectTracker(dt=dt, model_spec=model_spec, matching_fn_kwargs = matching_fn_kwargs, active_tracks_kwargs=active_tracks_kwargs, tracker_kwargs=tracker_kwargs)

def on_change_maxstale(value):
    global active_tracks_kwargs, tracker_kwargs, tracker2
    active_tracks_kwargs['max_staleness'] = value
    tracker_kwargs['max_staleness'] = value
    tracker2 = MultiObjectTracker(dt=dt, model_spec=model_spec, matching_fn_kwargs = matching_fn_kwargs, active_tracks_kwargs=active_tracks_kwargs, tracker_kwargs=tracker_kwargs)


def realTime():
    #try:
    mqttVideoTime = time.time()
    if publish_stats: publishStatsGenerator = publishStats(mqttSender)
    if setup_local_screen: # if local screen is to be opened, we must initialize it when window is opened for first time.
        init_local_screen = True
    if save_detection_frames:
        i = 0
        saving = False
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        savingStartTime = time.time()
    time1 = time.time()

    files = os.listdir("saves")
    files = [f for f in files if os.path.isfile('saves/'+f)] 
    for videoFile in files:
        cap = cv2.VideoCapture('saves/'+videoFile)
        fps = cap.get(cv2.CAP_PROP_FPS)
        delayBetweenFrames = 1/fps
        while True:
            success, img = cap.read()
            if not success: break
        
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
            tracks = tracker2.active_tracks()

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
            if show_stats: 
                timeLeft = delayBetweenFrames - (time.time()-time1)
                #print(delayBetweenFrames, timeLeft)
                if timeLeft >0 : time.sleep(timeLeft)
                time1 = drawStats(cv2, img, classNames, required_class_index, up_direction, down_direction, up_list, down_list, time1, font_size, font_color, font_thickness, confThreshold, nmsThreshold, model_spec['q_var_pos'], model_spec['r_var_pos'], matching_fn_kwargs['min_iou'], matching_fn_kwargs['multi_match_min_iou'], active_tracks_kwargs['min_steps_alive'], active_tracks_kwargs['max_staleness'])

            if save_detection_frames:
                #if len(tracks) > 0: # if active tracks exist
                if True:
                    detectionVideoStartTime = time.time() # reset timer
                    if not saving: # if not currently collecting frames for video file, instantiate new videowriter object
                        i += 1
                        outputFile = cv2.VideoWriter(f"saves/aftersaves/{i}output.avi", fourcc, 1/dt, resolution)
                        saving = True
                        savingStartTime = time.time()
                if saving: 
                    outputFile.write(img) # write current frame to video file
                    cv2.circle(img,(crop_coord[0]+40, crop_coord[1]+40), 20, (255*(i%2),20*(i%2)+200*((i+1)%2),50*((i+1)%2)), -1)
                if (saving and time.time() - detectionVideoStartTime > 5) or time.time() - savingStartTime > 30:
                    # if saving but enough time has passed and there is no active tracks, close video file
                    outputFile.release()
                    saving = False
            
            if publish_stats : 
                next(publishStatsGenerator)
            
            # if local screen is to be shown
            if setup_local_screen:
                action = localOutput(cv2, img, font_size, font_color, font_thickness)
                if init_local_screen:
                    cv2.imshow('Trackbars',np.zeros((100,500,3), dtype=np.uint8))
                    cv2.createTrackbar('confThreshold', 'Trackbars', int(confThreshold*100) ,100, on_change_conf)
                    cv2.createTrackbar('nmsThreshold', 'Trackbars', int(nmsThreshold*100) ,100, on_change_nms)
                    cv2.createTrackbar('q_var_pos', 'Trackbars', int(model_spec['q_var_pos']*10),200000, on_change_qvar)
                    cv2.createTrackbar('r_var_pos', 'Trackbars', int(model_spec['r_var_pos']*1000),10000, on_change_rvar)
                    cv2.createTrackbar('min_iou', 'Trackbars', int(matching_fn_kwargs['min_iou']*100),100, on_change_miniou)
                    cv2.createTrackbar('multi_match_min_iou', 'Trackbars', int(matching_fn_kwargs['multi_match_min_iou']*100),100, on_change_multiminiou)
                    cv2.createTrackbar('min_steps_alive', 'Trackbars', int(active_tracks_kwargs['min_steps_alive']),20, on_change_minsteps)
                    cv2.createTrackbar('max_staleness', 'Trackbars', int(tracker_kwargs['max_staleness']),30, on_change_maxstale)
                    init_local_screen = False

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
