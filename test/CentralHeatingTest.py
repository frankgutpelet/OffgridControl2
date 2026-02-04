import sys
import os
import time
import datetime


parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from CentralHeatingControl import CentralHeatingControl

class LoggerMock():
    def __init__(self):
        pass
    def Debug(self, msg):
        print("DEBUG: " + msg)
    def Error(self, msg):
        print("ERROR: " + msg)
    def Info(self, msg):
        print("INFO: " + msg)

class dateTimeMock():
    class Now():
        def __init__(self):
            self.timestamp = datetime.datetime.now().time()
            self.weekDay = 1
        def time(self):
            return self.timestamp
        def weekday(self):
            return self.weekDay
    def __init__(self):
        self.timestamp = self.Now()
        pass
    def now(self):
        return self.timestamp


logger = LoggerMock()
datetimeMock = dateTimeMock()
control = CentralHeatingControl("../rooms.xml", logger, datetimeMock=datetimeMock)

while(True):
    time.sleep(1)