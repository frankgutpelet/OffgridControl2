from TempPuller import TempPuller
import time

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

def callback (msg, temp):
    print(f"{msg}: {str(temp)} °")
    exit(0)

puller = TempPuller(logger )
puller.addSensor("http://tempSEnsorPool/temp", callback, "Bad: " )

while True:
    time.sleep(1)