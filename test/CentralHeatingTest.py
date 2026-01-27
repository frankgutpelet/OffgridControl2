import sys
import os
import time


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

logger = LoggerMock()
control = CentralHeatingControl("../rooms.xml", logger)

while(True):
    time.sleep(1)