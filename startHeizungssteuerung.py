import sys

import Heizungssteuerung
from MyLogging import Logging

class StreamToMyLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        message = message.strip()
        if not message:
            return

        if self.level == Logging.LOGGLEVEL_INFO:
            self.logger.Info(message)
        elif self.level == Logging.LOGGLEVEL_ERROR:
            self.logger.Error(message)
        elif self.level == Logging.LOGGLEVEL_DEBUG:
            self.logger.Debug(message)

    def flush(self):
        pass

    def isatty(self):
        return False

def main():

    
    print("started")
    logger = Logging(logfile="log/Heizungssteuerung_")
    logger.setLogLevel("DEBUG")
    sys.stdout = StreamToMyLogger(logger, Logging.LOGGLEVEL_INFO)
    sys.stderr = StreamToMyLogger(logger, Logging.LOGGLEVEL_ERROR)
    backend = Heizungssteuerung.HeizungsPage(logger)
    backend.start()


if __name__ == "__main__":
    main()