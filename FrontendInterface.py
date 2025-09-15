import socket
from MyLogging import Logging
import traceback

class FrontendInterface:
    def __init__(self, logger: Logging):
        self.logger = logger
        # Server-Socket dauerhaft offen halten
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.server.bind(('localhost', 23456))
        except:
            logger.Error("Server nicht verbunden: " + traceback.format_exc())
            return
        self.server.listen()
        self.logger.Debug("Server (Sender) läuft auf localhost:23456")
        self.conn = None

    def wait_for_client(self):
        if self.conn is None:
            self.conn, addr = self.server.accept()
            self.logger.Debug(f"Client verbunden: {addr}")

    def write(self, message: str):
        self.wait_for_client()
        try:
            self.conn.sendall(message.encode())
            #self.logger.Debug(f"Gesendet: {message}")
        except BrokenPipeError:
            self.logger.Error("Client hat die Verbindung getrennt")
            self.conn.close()
            self.conn = None
