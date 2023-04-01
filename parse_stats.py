# Collect statistics from raw data
# Send it to MQTT broker and email
# Parametric time interval reports (one function to collect wanted time range data?)
# Either pure text in email or CSV/excel file as attachement
# raw data without log data
# charts as images
from configparser import ConfigParser
import csv
import datetime
import json
import time
import threading
from mqtt_class import mqttClass
import sys

config = ConfigParser()
langConfig = ConfigParser()
config_file = 'configuration.ini'
languageConfigFile = 'language.txt'
config.read(config_file)
langConfig.read(languageConfigFile, encoding="utf-8")

class parseDataToJSON():
    def __init__(self, rawFile, publishers, fromAreas, timeRangeType, pollTime, language = "suomi", publisherName = "statsPublisher", topic = "stats"):
        self.publisherName = publisherName
        self.topic = topic
        self.mqttPublisher = mqttClass(self.publisherName, qos = 2)
        self.mqttPublisher.client.loop_start()
        self.rawFile = rawFile
        self.publishers = publishers
        self.fromAreas = fromAreas
        self.timeRangeType = timeRangeType
        self.started = datetime.datetime.now()
        self.reportCount = 0
        self.statsJSON = {}
        self.timeRanges = {"daily":0, "weekly":1, "monthly": 2}
        self.pollTime = pollTime
        self.language = language
        self.words = json.loads(langConfig.get("parse_stats","languageString").replace("\\\n", "")) # read language versions
        self.conditionDict = json.loads(config.get("parseStats", "parseStatsConditionDict").replace("\\\n", ""))
        self.thread = threading.Thread(target = self.triggerTimedParsing, name = self.timeRangeType, daemon=True)
        self.thread.start()
        
    def triggerTimedParsing(self):
        #define dictionary that contains a triggering condition for each report type
        time.sleep(self.pollTime)
        if len(sys.argv)>1:
            if str(sys.argv[1]) == "debug": # if debug activated from command line parameter #1, create new daily condition according to parameters #2 and #3
                self.conditionDict["daily"]=f"now.hour == {str(sys.argv[2])} and now.minute == {str(sys.argv[3])} and now.second < 60"
                print(self.conditionDict["daily"])

        while True: # Loop forever
            now = datetime.datetime.now()

            if eval(self.conditionDict[self.timeRangeType]):
                self.readData(self.rawFile, self.publishers, self.fromAreas, self.timeRangeType)
                self.mqttPublisher.sendMessage(self.topic, self.statsJSON, qos=2, printOut = True, log = True)

                time.sleep(60)

            else:
                print("Condition", self.conditionDict[self.timeRangeType], "Not true, going to sleep for", str(self.pollTime)+"\n")
                time.sleep(self.pollTime)
 
    def readData(self, rawFile, publishers, fromAreas, timeRangeType):
        reportType = self.timeRanges[timeRangeType]
        self.reportCount += 1
        totalLang = self.words[self.language]["total"]
        typesLang = self.words[self.language]["types"]
        timeSpanLang = self.words[self.language]["time span"]
        directionLang = self.words[self.language]["direction"]
        amountLang = self.words[self.language]["amount"]
        infoLang = self.words[self.language]["report info"]
        publisherLang = self.words[self.language]["publishers"]

        def avoidHeader(item):
            """
            key function for sorted()
            """
            if type(item) == str:
                return 0
            else:
                return item

        while True:
            
            #try:
            with open(rawFile, "r") as csvFile:
                data = [line for line in csv.reader(csvFile)]
            dataTable = {infoLang:{\
                        self.words[self.language]["statsPollStartTime"]:str(self.started), \
                        self.words[self.language]["statsCurrentTime"]:str(datetime.datetime.now()), \
                        #self.words[self.language]["reportSpan"]:self.parseTimeRangeString(reportType), \
                        self.words[self.language]["statsCountFromStart"]:str(self.reportCount), \
                        self.words[self.language]["statsType"]:[self.words[self.language][timeRangeType],self.parseTimeRangeString(reportType)],\
                        publisherLang:[],\
                        typesLang:[]},\
                        totalLang:{}}
            
            #topic: mqqtClient/from/to/type, message: timestamp
            #{type_1:{timeRange_1:{from-to_1:int, from-to_2:int, ..., from-to_n:int}, timeRange_2:{}, ..., timeRange_n:{}}, type_2:{}, ..., type_n:{}}
            #{timeRange_1:{type_1:{from-to_1:int, from-to_2:int, ..., from-to_n:int}, type_2:{}, ..., type_n:{}}, timeRange_2:{}, ..., timeRange_n:{}}
            for line in data:
                if line[0] in publishers: # client name of publisher
                    dataTable[infoLang][publisherLang].append(line[0]) if line[0] not in dataTable[infoLang][publisherLang] else ""
                    if line[1] in fromAreas: # second topic must be in "from area" names
                        timeStamp = line[-1]
                        if self.timeStampIsInRange(reportType, timeStamp):
                            typeID = f"{line[3]}"
                            from_to = f"{line[1]}->{line[2]}"
                            timeRange = self.parseTimeStamp(reportType, timeStamp) # 
                            typeIDlang = f"{line[0]}:{self.words[self.language][typeID]}"

                            if typeIDlang not in dataTable.keys():
                                dataTable[typeIDlang] = {timeSpanLang[reportType]:{directionLang:amountLang}}
                                dataTable[totalLang].update({typeIDlang:{}})
                                dataTable[infoLang][typesLang].append(typeIDlang)
                            if timeRange not in dataTable[typeIDlang].keys(): # first appearance of such time range
                                dataTable[typeIDlang][timeRange] = {}
                                if from_to not in dataTable[totalLang][typeIDlang].keys():
                                    dataTable[totalLang][typeIDlang].update({from_to:0})
                                
                            if from_to not in dataTable[typeIDlang][timeRange].keys():
                                dataTable[typeIDlang][timeRange][from_to] = 1 # first appearance of such typeID from area to area
                                if from_to not in dataTable[totalLang][typeIDlang].keys():
                                    dataTable[totalLang][typeIDlang].update({from_to:1})
                                else:
                                    dataTable[totalLang][typeIDlang][from_to] += 1
                            else:
                                dataTable[typeIDlang][timeRange][from_to] += 1 # next appearance of such typeID
                                dataTable[totalLang][typeIDlang][from_to] += 1
            # sort time slots into ascending order (in case they were not sorted in data csv)
            keys = {}
            for typeID in dataTable:
                #if typeID != self.words[self.language]["report info"]:
                if typeID in dataTable[infoLang][typesLang]:
                    keys[typeID] = sorted(dataTable[typeID].keys(), key=avoidHeader)
            dataTableFinal = {infoLang:dataTable[infoLang], totalLang:dataTable[totalLang]}
            for typeID in dataTable:
                #if typeID != self.words[self.language]["report info"]:
                if typeID in dataTable[infoLang][typesLang]:
                    if typeID not in dataTableFinal:
                        dataTableFinal[typeID] = {}
                    for timeslot in keys[typeID]:
                        print(dataTable,"\n\n", timeslot, "\n\n", typeID)
                        dataTableFinal[typeID][timeslot] = dataTable[typeID][timeslot]
                        directionKeys = sorted(dataTableFinal[typeID][timeslot])
                        dataTableFinal[typeID][timeslot] = {x:dataTableFinal[typeID][timeslot][x] for x in directionKeys}
            self.statsJSON = json.dumps(dataTableFinal, sort_keys = False)                
            break
            """
            except Exception as e:
                    print(self.thread.name,"An error occured during opening and parsing datafile", rawFile)
                    print(e)
                    print("Trying to read datafile", rawFile, "again")
            """
        time.sleep(10)
    def parseTimeRangeString(self, reportType):
        """
        parse a string that depicts timerange of raport:
        reportType == 0 => "[last day date] hours 00-24"
        reportType == 1 => "last week days [date from - date to]
        reportType == 2 => "last month days [date from - date to]
        """
        if reportType == 0:
            yesterday = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(days=1), "%Y/%m/%d")
            timeRangeString = f"{yesterday} 00:00-24:00"
        elif reportType == 1:
            thisDayWeekDay = (datetime.datetime.now()).isocalendar()[2]
            firstDayOfLastWeek = datetime.datetime.now()-datetime.timedelta(days=(thisDayWeekDay+6))
            lastDayOfLastWeek = datetime.datetime.now()-datetime.timedelta(days=thisDayWeekDay)
            timeRangeString = f"{datetime.datetime.strftime(firstDayOfLastWeek, '%Y/%m/%d')} - {datetime.datetime.strftime(lastDayOfLastWeek, '%Y/%m/%d')}"
        elif reportType == 2:
            monthNow = datetime.datetime.now().month
            lastMonth = (monthNow-2)%12+1
            if lastMonth == 12:
                lastMonthYear = datetime.datetime.now().year - 1
                yearNow = lastMonthYear + 1
            else:
                lastMonthYear = datetime.datetime.now().year
                yearNow = lastMonthYear
            firstDayOfLastMonth = datetime.datetime(lastMonthYear, lastMonth, 1)
            firstDayOfThisMonth = datetime.datetime(yearNow, monthNow, 1)
            lastDayOfLastMonth = firstDayOfThisMonth - datetime.timedelta(days=1)
            timeRangeString = f"{datetime.datetime.strftime(firstDayOfLastMonth, '%Y/%m/%d')} - {datetime.datetime.strftime(lastDayOfLastMonth, '%Y/%m/%d')}"

        return timeRangeString
    
    def timeStampIsInRange(self, reportType, timeStamp):
        """
        Checks is the parameter timestamp within proper time range:
        reportType = 0 => timestamps from previous full day are eligible
        reportType = 1 => timestamps from previous full week are eligible
        reportType = 2 => timestamps form previous full month are eligible

        returns True or False accordingly
        """
        if reportType == 0:
            stampDayNum = (datetime.datetime.fromisoformat(timeStamp)).day
            previousDayNum = (datetime.datetime.now() - datetime.timedelta(days = 1)).day
            if stampDayNum == previousDayNum:
                return True
            else:
                return False

        elif reportType == 1:
            stampWeekNum = (datetime.datetime.fromisoformat(timeStamp)).isocalendar()[1]
            thisWeekNum = (datetime.datetime.now()).isocalendar()[1]
            if (thisWeekNum - stampWeekNum)%52 == 1:
                return True
            else:
                return False
            
        elif reportType == 2:
            stampMonthNum = (datetime.datetime.fromisoformat(timeStamp)).month
            thisMonthNum = (datetime.datetime.now()).month
            if (thisMonthNum - stampMonthNum)%12 == 1:
                return True
            else:
                return False

    def parseTimeStamp(self, reportType, timeStamp):
        """
        Parse timeStamp to a number according to reportType:
        reportType = 0 => return "month-day hour:00"
        reportType = 1 => return number of day of week (int)
        reportType = 2 => return number of day of month (int)
        """
        if reportType == 0:
            return (datetime.datetime.fromisoformat(timeStamp)).hour
        elif reportType == 1:
            return (datetime.datetime.fromisoformat(timeStamp)).isocalendar()[2]
        elif reportType == 2:
            return (datetime.datetime.fromisoformat(timeStamp)).day

def main():
    rawData = config.get("files", "raw_log")
    detectionPublishers = eval(config.get("mqtt", "detectionPublishers"))
    statsPublishers = eval(config.get("mqtt", "reportParserPublishers"))
    topics = eval(config.get("mqtt", "statsTopics"))
    directions = eval(config.get('main', 'directions'))
    language = config.get('language', 'language')
    debugLogging = config.getboolean('debug', 'debugLogging')
    reportTypes = ["daily", "weekly", "monthly"]
    pollTimes = [7, 13, 17]
    statsParsers = []

    if len(sys.argv) > 1:
        if str(sys.argv[1]) == "debug": # if debugging activated
            pollTimes = [1]
    elif debugLogging:
        pollTimes = [1]

    for reportType, pollTime, statsPublisher, topic in zip(reportTypes, pollTimes, statsPublishers, topics):
        print(f"polltime {pollTime}")
        statsParsers.append(parseDataToJSON(rawData, detectionPublishers, directions, reportType, pollTime, language, statsPublisher, topic))


    while True:
        time.sleep(3600) # just to keep things looping.

    
if __name__ == "__main__": 
    main()

    
