import csv, time, datetime, os

def write_raw_csv(listener, file):
    try:
        with open(file, 'a', newline='') as fileHandle:
            cwriter = csv.writer(fileHandle)
            
            while not listener.messageQueue.empty():
                message = listener.messageQueue.get()
                line = message.topic.split("/")
                line.append(str(message.payload.decode("utf-8")))
                cwriter.writerow(line)         

        print(f"Data appended at {file}")
    except:
        print("Write_raw_csv failed")

    finally: 
        print("Write_raw_csv() end")
        now = datetime.datetime.now()
        if now.day == 1 and now.hour == 0: # if it is first day of month and midnight, rename old datafile and move it to raw_logs folder
            try:
                os.rename(file, f"raw_logs/{file.strip('.csv')}-{datetime.datetime.strftime(now, '%Y-%m-%d_%H-%M')}.csv")
                print("Datafile renamed, new file will be started")
            except Exception as e:
                print("Datafile renaming failed:", e)

        
def write_exceptions_csv(exception, folder):
    try:
        with open(folder+"exceptions.csv", 'a', newline='') as f2:
            cwriter = csv.writer(f2)
            cwriter.writerow([time.strftime('%Y-%m-%d', time.localtime()), time.strftime('%H-%M-%S', time.localtime())])
            cwriter.writerow([exception])         
        f2.close()
        print("Exception appended at 'exceptions.csv'")
    except:
        pass
    finally: print("Write_exceptions_csv() end")

def write_stats_csv(once=False, caller="main"):    
    global up_list, down_list, empty_lists_flag, last_time_stamp, stats_interval 
    empty_lists_flag = False
    if caller != "main": print(f"{caller}: Write_stats_csv called")
    while True:
        time_stamp_now = datetime.datetime.now()
        time_diff = time_stamp_now - last_time_stamp
        while not once and time_diff.total_seconds() < stats_interval:
            wait_time = stats_interval - time_diff.total_seconds()
            wait_time_timedelta = datetime.timedelta(seconds = wait_time)
            print(f"{caller}: Waiting for {wait_time_timedelta} until next stats_data.csv write")
            time.sleep(wait_time) # loop wait until stats_interval amount of time has passed from last stats_data.csv mark
            time_stamp_now = datetime.datetime.now()
            time_diff = time_stamp_now - last_time_stamp

        if not once and time_diff.total_seconds() >= stats_interval:
            last_time_stamp = datetime.datetime.now()

        try:
            print(f"{caller}: Writing stats_data.csv")
            with open(folder+"stats_data.csv", 'a', newline='') as f1:
                write_up_list = up_list[:]
                write_down_list = down_list[:]
                empty_lists_flag = True
                print("Write csv raised empty_lists_flag: ", empty_lists_flag)
                time_stamp = [time.strftime('%Y-%m-%d', time.localtime()), time.strftime('%H-%M-%S', time.localtime())]
                cwriter = csv.writer(f1)
                
                cwriter.writerow([""])
                cwriter.writerow(["report time"] + time_stamp)
                cwriter.writerow(["Direction"] + [classNames[key] for key in required_class_index])
                write_up_list.insert(0, up_direction)
                write_down_list.insert(0, down_direction)
                cwriter.writerow(write_up_list)
                cwriter.writerow(write_down_list)

            f1.close()
            #if empty_lists_flag:
            #    time.wait(10)
            print(f"{caller}: Data saved at 'stats_data.csv'")
            if once: 
                print("Called only once, terminating stats_data.csv writing loop")
                break 
            #time.sleep(stats_interval)
        except:
            print(f"{caller}: Failed writing stats_data.csv")
        finally: print(f"{caller}: Write_stats_csv() end")
