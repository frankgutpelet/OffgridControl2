import datetime
import threading
import time


class Logging:
    LOGGLEVEL_NONE = 0
    LOGGLEVEL_ERROR = 1
    LOGGLEVEL_INFO = 2
    LOGGLEVEL_DEBUG = 3

    def __init__(self):
        self.__loglevel = 0
        self.__logToCVS = False
        self.__lock_logBuffer = threading.Lock()
        self.logBuffer = list()
        self.loggingThread = threading.Thread(target=self.__ThreadFunc, args=())
        self.loggingThread.start()

    def __ThreadFunc(self):
        while True:
            if (len(self.logBuffer) >= 1):
                self.__lock_logBuffer.acquire()
                try:
                    logfile = open("log/OffgridControl_" + datetime.datetime.today().strftime("%Y-%m-%d") + ".log", "a")
                    for entry in self.logBuffer:
                        logfile.write(entry)
                    logfile.close()
                    self.logBuffer.clear()
                except Exception as e:  # logging should not lead to an exception
                    print(e)
                self.__lock_logBuffer.release()

            time.sleep(5)

    def Debug(self, string):
        if self.LOGGLEVEL_DEBUG > self.__loglevel:
            return
        self.__Log("DEBUG - " + string)

    def Info(self, string):
        if self.LOGGLEVEL_INFO > self.__loglevel:
            return
        self.__Log("INFO  - " + string)

    def Error(self, string):
        if self.LOGGLEVEL_ERROR > self.__loglevel:
            return
        self.__Log("ERROR - " + string)

    def __Log(self, string):
        self.__lock_logBuffer.acquire()
        self.logBuffer.append(datetime.datetime.now().strftime("%H:%M:%S") + ": " + string + "\n")
        self.__lock_logBuffer.release()

    def setLogLevel(self, loglevel):
        if "DEBUG" == loglevel:
            self.__loglevel = Logging.LOGGLEVEL_DEBUG
        elif "INFO" == loglevel:
            self.__loglevel = Logging.LOGGLEVEL_INFO
        elif "ERROR" == loglevel:
            self.__loglevel = Logging.LOGGLEVEL_ERROR
        elif "NONE" == loglevel:
            self.__loglevel = Logging.LOGGLEVEL_NONE
        else:
            self.__loglevel = Logging.LOGGLEVEL_ERROR
            self.Error("Loglevel wrong: " + loglevel)
            loglevel = "DEBUG"