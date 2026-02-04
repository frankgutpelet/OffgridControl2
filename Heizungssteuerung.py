from xml.dom import minidom

from fastapi import Query
import threading
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import xml.etree.ElementTree as ET
from pathlib import Path
from MyLogging import Logging
from TempReader import TempReader
from Types import *
from CentralHeatingControl import CentralHeatingControl


class TimeSlot(BaseModel):  # Von BaseModel erben!
    id : int
    time: str  # Im XML war es ein String "06:00"
    temp: float
    days: str
    active : bool
    heating: bool

class RoomState(BaseModel):
    name: str
    current: float
    slots: list[TimeSlot]
    channel: Optional[str] = None
    url: Optional[str] = None


class RoomProfile(BaseModel):
    name: str
    slots: list[TimeSlot]
    channel: Optional[str] = None
    url: Optional[str] = None
# ---------------------------
# ApiServer
# ---------------------------
class HeizungsPage:

    logger: Logging

    def __init__(self, logger: Logging, host="0.0.0.0", port=8001, server = None):
        self.logger = logger
        self.host = host
        self.port = port
        self.xml_file = Path("rooms.xml")
        self.room_profiles: dict[str, dict] = {}  # { room_name: {"slots": [...], "channel": ..., "url": ...} }
        self.tempReader = TempReader()
        self.controller = CentralHeatingControl(self.xml_file, self.logger)
        self.load_xml()

        if not server:
            self.app = FastAPI(
                title="OffgridControl REST API",
                description="OffgridControl REST API",
                version="1.0.0"
            )
            self.app.mount("/static", StaticFiles(directory="static"), name="static")
            self.templates = Jinja2Templates(directory="templates")
            self._thread = None

        else:
            self.app = server.getApp()
            #self.app.mount("/static", StaticFiles(directory="static"), name="static")
            self.templates = Jinja2Templates(directory="templates")
            self._thread = server.getThread()

        self._setup_routes()


    # ---------------------------
    # XML laden
    # ---------------------------
    def load_xml(self):
        if not self.xml_file.exists():
            self.logger.Info("rooms.xml nicht gefunden")
            return

        tree = ET.parse(self.xml_file)
        root = tree.getroot()
        self.room_profiles = {}

        for room_el in root.findall("room"):
            name = room_el.get("name")
            channel = room_el.get("channel")
            url = room_el.get("url")

            slots = []
            for slot_el in room_el.findall("slot"):
                slots.append(TimeSlot(
                    id = slot_el.get("id"),
                    time=slot_el.get("time"),
                    temp=float(slot_el.get("temp")),
                    days=slot_el.get("days", "1-7"),
                    active=False,
                    heating=False
                ))

            self.room_profiles[name] = {
                "slots": slots,
                "channel": channel,
                "url": url
            }

        self.logger.Info(f"XML geladen: {list(self.room_profiles.keys())}")

    # ---------------------------
    # API-Routen
    # ---------------------------
    def _setup_routes(self):

        def getTemperature(roomname: str) -> float:

            # 1. Hol dir den Channel-Namen aus dem Profil
            channel = self.room_profiles[roomname].get('channel')
            # 2. Prüfen ob Channel existiert (nicht None und nicht leerer String)
            if channel:
                values = self.tempReader.getValues()
                # 3. Prüfen ob der Channel auch im TempReader vorhanden ist
                room_data = values.get(channel)
                if room_data:
                    return room_data.get("temperature", 0.0)
            return self.controller.getTemp(roomname)


        # Frontend
        @self.app.get("/Heizung", summary="Webseite anzeigen")
        def index(request: Request):
            context = {"request": request}
            return self.templates.TemplateResponse("rooms.html", context)

        # Alle Räume zurückgeben
        @self.app.get("/api/rooms", response_model=list[RoomState])
        def get_rooms():
            result = []
            for room_name, data in self.room_profiles.items():
                current_temp = getTemperature(room_name)
                for slot in data["slots"]:
                    slot.heating, slot.active =  self.controller.isOn(room_name, slot.id)
                result.append(RoomState(
                    name=room_name,
                    current=current_temp,
                    slots=data["slots"],
                    channel=data.get("channel"),
                    url=data.get("url"),
                ))
            return result

        # Raumprofil speichern
        @self.app.post("/api/rooms/{room_name}")
        def save_room_profile(room_name: str, profile: RoomProfile):
            if room_name != profile.name:
                return {"status": "error", "message": "Raumname stimmt nicht überein"}

            # Memory aktualisieren
            self.room_profiles[room_name] = {
                "slots": profile.slots,
                "channel": profile.channel,
                "url": profile.url
            }

            # XML aktualisieren
            tree = ET.parse(self.xml_file)
            root = tree.getroot()

            for room_el in root.findall("room"):
                if room_el.get("name") == room_name:
                    # Alte Slots löschen
                    for s in list(room_el):
                        room_el.remove(s)
                    # Neue Slots einfügen
                    for s in profile.slots:
                        ET.SubElement(room_el, "slot", id=str(profile.slots.index(s)+1), time=s.time, temp=str(s.temp), days=s.days)
                    # channel/url aktualisieren
                    if profile.channel is not None:
                        room_el.set("channel", profile.channel)
                    if profile.url is not None:
                        room_el.set("url", profile.url)
                    break
            else:
                # Neuer Raum
                room_el = ET.SubElement(root, "room", name=room_name)
                if profile.channel is not None:
                    room_el.set("channel", profile.channel)
                if profile.url is not None:
                    room_el.set("url", profile.url)
                for s in profile.slots:
                    ET.SubElement(room_el, "slot", time=s.time, temp=str(s.temp), days=s.days)

            # In einen String konvertieren
            #xml_str = ET.tostring(root, encoding="utf-8")
            # Mit minidom schön formatieren
            #pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")

            # In Datei schreiben
            #with open(self.xml_file, "w", encoding="utf-8") as f:
             #   f.write(pretty_xml)

            tree.write(self.xml_file, encoding="utf-8", xml_declaration=True)
            self.logger.Info(f"XML aktualisiert für Raum: {room_name}")
            self.controller.loadXml()
            return {"status": "ok"}

        # Temperatur melden
        @self.app.post("/api/temp/{room_name}")
        def saveTemperature(room_name: str, temperature: float = Query(...)):
            self.controller.setTemp(room_name, temperature)
            return {"status": "ok"}  # Wichtig: Immer ein JSON zurückgeben!
    # ---------------------------
    # Server starten
    # ---------------------------
    def start(self):
        if self._thread and self._thread.is_alive():
            self.logger.Debug("API-Server läuft bereits.")
            return

        def _run():
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        self.logger.Info(f"API-Server gestartet unter http://{self.host}:{self.port}")
        self.logger.Info(f"Swagger UI: http://{self.host}:{self.port}/docs")

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()
