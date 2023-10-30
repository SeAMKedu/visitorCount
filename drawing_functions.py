import numpy as np
import time

def cumulative(cv2, img, font_size, font_color, font_thickness, dir1, dir2, num1, num2):
    """
    defined in drawing_functions.py
    function opens a local openCV window in operating system.
    and prints numbers dir1 and dir2 alongside with their explanations
    """
    cv2.putText(img, f"{dir1}: {num1}", calc_coord(0.05, 0.3, img.shape), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
    cv2.putText(img, f"{dir2}: {num2}", calc_coord(0.05, 0.7, img.shape), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)

    cv2.imshow('Cumulative', img)
    if cv2.waitKey(5) == ord('q'):
        return 1
        #write_raw_csv()
        #break
    #if cv2.waitKey(1) == ord('w'):
    #    return 2
    #    #write_raw_csv()
    

def localOutput(cv2, img, font_size, font_color, font_thickness):
    """
    defined in drawing_functions.py
    function opens a local openCV window in operating system.
    returns int according to keys pressed
    """
    img3 = np.copy(img)
    cv2.putText(img3, "'q' terminate, 'w' write raw report", calc_coord(0.05, 0.9, img.shape), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
    cv2.imshow('Output', img3)
    if cv2.waitKey(5) == ord('q'):
        return 1
        #write_raw_csv()
        #break
    #if cv2.waitKey(1) == ord('w'):
    #    return 2
    #    #write_raw_csv()

def calc_coord(x_rel, y_rel, img_shape):
    y_tot, x_tot, layers = img_shape
    x = int(x_tot * x_rel)
    y = int(y_tot * y_rel)
    return (x,y)

def drawCircle(cv2, img, center, max_distance, up_direction, temp_up_list, down_direction, temp_down_list, font_size, font_color, font_thickness):
    cv2.circle(img, center, max_distance, (0, 0, 255), 2)
    cv2.putText(img,f'{up_direction}:', calc_coord(0.8, 0.04, img.shape), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
    for i in range(len(temp_up_list)):
        cv2.putText(img,f'{temp_up_list[i]}', tuple(a+b for a,b in zip(calc_coord(0.8, 0.07, img.shape),(0,20*i))), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
    cv2.putText(img,f'{down_direction}:', calc_coord(0.9, 0.04, img.shape), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
    for i in range(len(temp_down_list)):
        cv2.putText(img,f'{temp_down_list[i]}', tuple(a+b for a,b in zip(calc_coord(0.9, 0.07, img.shape),(0,20*i))), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)

def drawTraces(cv2, img, lines, colors):
    color = [int(c) for c in colors[lines[0][0]]]
    if len(lines[1]) > 2:
        for index in range(2, len(lines[1])):
            cv2.line(img, (lines[1][index-1][0], lines[1][index-1][1]), (lines[1][index][0], lines[1][index][1]), color, max(1,int(5*index/len(lines[1]))))

def drawLines(cv2, up, up_out, middle, down_out, down, img, direction):
    if direction == "vertical":
        cv2.line(img, (up,0 ), (up, img.shape[0]), (0, 0, 255), 2)
        cv2.line(img, (up_out,0), (up_out, img.shape[0]), (200, 200, 200), 1)
        cv2.line(img, (middle, 0), (middle, img.shape[0]), (255, 200, 255), 2)
        cv2.line(img, (down_out, 0), (down_out, img.shape[0]), (200, 200, 200), 1)
        cv2.line(img, (down, 0), (down, img.shape[0]), (0, 0, 255), 2)
    else:
        cv2.line(img, (0,up,), (img.shape[1], up), (0, 0, 255), 2)
        cv2.line(img, (0, up_out), (img.shape[1], up_out), (200, 200, 200), 1)
        cv2.line(img, (0, middle), (img.shape[1], middle), (255, 200, 255), 2)
        cv2.line(img, (0, down_out),  (img.shape[1], down_out), (200, 200, 200), 1)
        cv2.line(img, (0, down), (img.shape[1], down), (0, 0, 255), 2)

def drawNames(cv2, img, up_direction, down_direction, direction, font_size, font_color, font_thickness):
    if direction == "vertical":
        cv2.putText(img, up_direction, calc_coord(0.1,0.5,img.shape), cv2.FONT_HERSHEY_SIMPLEX, font_size*2, font_color, font_thickness+1)
        cv2.putText(img, down_direction, calc_coord(0.85, 0.5, img.shape), cv2.FONT_HERSHEY_SIMPLEX, font_size*2, font_color, font_thickness+1)
    else:
        cv2.putText(img, up_direction, calc_coord(0.5,0.1,img.shape), cv2.FONT_HERSHEY_SIMPLEX, font_size*2, font_color, font_thickness+1)
        cv2.putText(img, down_direction, calc_coord(0.5, 0.9, img.shape), cv2.FONT_HERSHEY_SIMPLEX, font_size*2, font_color, font_thickness+1)	

def publishStats(mqttSender):
    fpsTime = time.time()
    time.sleep(0.1) # just to evade divide by zero in calculating fps first time when script is started
    i = 0
    while True:
        i += 1
        if i == 100:
            mqttSender.sendMessage("stats/fps", round(100/(time.time()-fpsTime),1), qos = 0, printOut = False, log = False)
            fpsTime = time.time()
            i = 0
        yield
        
def drawStats(cv2, img, classNames, required_class_index, up_direction, down_direction, up_list, down_list, time1, font_size, font_color, font_thickness, conf = 0, nms = 0, q_var_pos = 0, r_var_pos = 0, min_iou = 0, multi_match_min_iou = 0, min_steps_alive = 0, max_staleness = 0):
    
    time2 = time.time()
    diff = time2 - time1
    fps = round(1 / diff,1)

    # Draw black non-opaque box beyond white text
    x1,y1 = calc_coord(0.02, 0.01, img.shape)
    x2,y2 = calc_coord(0.4, 0.01, img.shape)
    y2 += 18*len(up_list) + 50
    sub_img = img[y1:y2, x1:x2]
    black_rect = np.ones(sub_img.shape, dtype=np.uint8) * 0
    res = cv2.addWeighted(sub_img, 0.5, black_rect, 0.5, 1.0)
    img[y1:y2, x1:x2] = res

    cv2.putText(img, f"FPS: {fps}", calc_coord(0.05,0.025,img.shape), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
    cv2.putText(img, up_direction + " " + down_direction, calc_coord(0.2,0.025,img.shape), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
    for index in range(len(up_list)):
        cv2.putText(img, f"{classNames[required_class_index[index]]:<14}", tuple(a+b for a,b in zip(calc_coord(0.05, 0.04, img.shape),(0,20*index))), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
        cv2.putText(img, str(up_list[index]), tuple(a+b for a,b in zip(calc_coord(0.2, 0.045, img.shape),(0,18*index))), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
    for index in range(len(down_list)):
        cv2.putText(img, str(down_list[index]), tuple(a+b for a,b in zip(calc_coord(0.25, 0.045, img.shape),(0,18*index))), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
    
    if conf and nms and q_var_pos and r_var_pos and min_iou and multi_match_min_iou and min_steps_alive and max_staleness:
        cv2.putText(img, f"confidence:{conf}, nms:{nms}, q_var:{q_var_pos}, r_var:{r_var_pos}", tuple(a+b for a,b in zip(calc_coord(0.05, 0.075, img.shape),(0,18*index))), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
        cv2.putText(img, f"min_iou:{min_iou}, multi_min_iou:{multi_match_min_iou}, min_steps:{min_steps_alive}, max_stale:{max_staleness}", tuple(a+b for a,b in zip(calc_coord(0.05, 0.095, img.shape),(0,18*index))), cv2.FONT_HERSHEY_SIMPLEX, font_size, font_color, font_thickness)
    return time.time()

def calculate_line_positions(middle, diff, resolution, direction):
    if direction == "vertical": 
        index = 0
    else: index = 1
    middle_line_position = int(middle * resolution[index])   
    up_line_position = int(middle_line_position - diff * resolution[index])
    up_line_out_position = int(middle_line_position - 0.5 * diff * resolution[index])
    down_line_position = int(middle_line_position + diff * resolution[index])
    down_line_out_position = int(middle_line_position + 0.5 * diff * resolution[index])
    print('New values for line positions: ', middle_line_position, up_line_position, up_line_out_position, down_line_position, down_line_out_position)
    return middle_line_position, up_line_position, up_line_out_position, down_line_position, down_line_out_position
  
