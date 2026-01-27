import Heizungssteuerung
from MyLogging import Logging

def main():
    print("started")
    logger = Logging(logfile="log/Heizungssteuerung_")
    logger.setLogLevel("DEBUG")
    backend = Heizungssteuerung.ApiServer(logger)
    backend.start()


if __name__ == "__main__":
    main()