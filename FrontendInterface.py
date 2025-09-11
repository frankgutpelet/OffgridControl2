from MyLogging import Logging
import socket

class FrontendInterface():

    def __init__(self, logger : Logging):
        self.handle = None
        self.logger = logger

    def write(self, message: str):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('localhost', 23456))
                s.sendall(message.encode())
                self.logger.Debug("Send to Frontend: " + message)
        except ConnectionRefusedError:
            s.close()
            self.logger.Error("Connection to Frontend refused, reconnecting ...")