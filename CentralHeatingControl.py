import json
import logging
import threading
from pathlib import Path
import xml.etree.ElementTree as ET
import traceback
import time, datetime
import requests

from TempPuller import TempPuller
from TempReader import TempReader
from Types import *

class TimeSlot(BaseModel):  # Von BaseModel erben!
    room: Room
    id : int
    time: str  # Im XML war es ein String "06:00"
    temp: float
    day: str
    active : bool
    heating: bool

class Actor(BaseModel):
    on : str
    off : str

class CentralHeatingControl:

    weekday = {
        'Mo' : 0,
        'Di' : 1,
        'Mi' : 2,
        'Do' : 3,
        'Fr' : 4,
        'Sa' : 5,
        'So' : 6
    }
    temps = dict()
    rooms : list[dict]
    actors : dict
    def __init__(self, xmlfile, logger, datetimeMock = None):
        logger.Info("CentralHeatingControl start..")
        self.xml_file = Path(xmlfile)
        self.actors = dict()
        self.logger = logger
        self.tempPuller = TempPuller(self.logger)
        self.rooms = list()# Für dein Dictionary
        self.loadXml()
        self.tempReader = TempReader()
        self.controlThread = threading.Thread(target=self.controlThread, daemon=True)
        self.controlThread.start()
        self.logger.Info("CentralHeatingControl started")
        #{room : [actor1, actor2]}
        if not datetimeMock:
            self.dateTime = datetime.datetime
        else:
            self.dateTime = datetimeMock

    def updateTemps(self):
        for room in self.rooms:
            # 1. Hol dir den Channel-Namen aus dem Profil
            channel = room.get('channel')
            # 2. Prüfen ob Channel existiert (nicht None und nicht leerer String)
            if channel:
                try:
                    values = self.tempReader.getValues()
                # 3. Prüfen ob der Channel auch im TempReader vorhanden ist
                    room_data = values.get(channel)
                    if room_data:
                        self.temps[room['name']] = float(room_data.get("temperature", "99.0"))
                except Exception:
                    self.logger.Error(f"Error getting temperature for channel {channel}, {traceback.format_exc()}")


    def setTemp(self, room_name: str, temp: float):
        self.temps[room_name] = temp

    def getTemp(self, room_name: str,):
        if room_name in self.temps:
            return self.temps[room_name]
        return 99.0

    def loadXml(self):

        if not self.xml_file.exists():
            self.logger.Info(f"{self.xml_file} nicht gefunden")
            return
        self.logger.Info("Reload XML file")
        tree = ET.parse(self.xml_file)
        root = tree.getroot()

        # Listen vor dem Laden leeren, um Duplikate bei erneutem Aufruf zu vermeiden
        self.timeslots = []
        self.temps = dict()
        self.tempPuller.sensors = []
        self.rooms = list()


        for room_el in root.findall("room"):
            name = room_el.get("name")
            channel = room_el.get("channel")
            url = room_el.get("url")
            self.temps[name] = 99.0
            self.rooms.append({'name' : name, 'channel' : channel, 'url' : url})

            # Instanziierung über die Klasse
            current_room = Room(name=name, url=url, channel=channel)

            if url:
                self.tempPuller.addSensor(url, self.setTemp, name)

            room_slots = []
            for slot_el in room_el.findall("slot"):
                new_slot = TimeSlot(
                    room=current_room,
                    id= slot_el.get("id"),
                    time=slot_el.get("time"),
                    temp=float(slot_el.get("temp")),
                    day=slot_el.get("days", "1-7"),
                    active = False,
                    heating=False
                )
                self.timeslots.append(new_slot)
                room_slots.append(new_slot)
            self.actors[name] = list()
            for actor in room_el.findall("actor"):
                new_actor = Actor(
                    on=actor.get("on"),
                    off=actor.get("off"),
                )
                self.actors[name].append(new_actor)

    def controlThread(self):
        logging.debug("Control thread started")
        while True:
            activeSlots = list()
            self.updateTemps()
            try:
                for slot in self.timeslots:
                    slot : TimeSlot
                    if self.isActive(slot):
                        self.logger.Debug(f"Slot {slot.room.name} {slot.time} ({slot.day}) is active")
                        activeSlots.append(slot)
                    else:
                        pass
                        #self.logger.Debug(f"Slot{slot.room.name} {slot.time} is not active")
                self.handleActiveSlots(activeSlots)
            except:
                #self.logger.Error(f"Error in controlThread: {traceback.format_exc()}")
                pass
            time.sleep(10)

    def isActive(self, slot: TimeSlot) -> bool:
        now = self.dateTime.now()
        if not self.isToday(slot, now):
            slot.active = False
            return False
        if now.time() <= datetime.time.fromisoformat(slot.time):
            slot.active = False
            return False
        if self.laterSlotActive(slot, now):
            slot.active = False
            return False
        slot.active = True
        return True



    def laterSlotActive(self, slot: TimeSlot, now : datetime.datetime) -> bool:
        for elem in self.timeslots:
            if elem == slot:
                continue
            if elem.room.name != slot.room.name:
                continue
            if not self.isToday(elem, now):
                continue
            elemTime = datetime.time.fromisoformat(elem.time)
            slotTime = datetime.time.fromisoformat(slot.time)
            if elemTime < slotTime:
                continue
            if elemTime > now.time():
                continue
            return True
        return False

    def isToday(self, slot : TimeSlot, now : datetime.datetime) -> bool:
        #self.logger.Debug(f"Today: {str(now.weekday())} , slot: {slot.day}")
        if slot.day == "1-7":
            return True
        if slot.day == "1-5":
            if now.weekday() <= 4:
                return True
            return False
        if slot.day == "6-7":
            if now.weekday() > 4:
                return True
            return False
        if now.weekday() == self.weekday[slot.day]:
            return True
        return False

    def handleActiveSlots(self, slots):
        heatReq = False

        for slot in slots:
            slot : TimeSlot
            if slot.temp > self.getTemp(slot.room.name):
                heatReq = True
                self.switchActors(slot.room.name, True)
                self.logger.Debug(f"Room {slot.room.name} needs to be heat")
                slot.heating = True
            else:
                self.switchActors(slot.room.name, False)
                self.logger.Debug(f"Room {slot.room.name} doesn't need to be heat  {str(slot.temp)} <= {str(self.getTemp(slot.room.name))}")
                slot.heating = False
        if heatReq:
            self.heatPump(True)
            return
        self.heatPump(False)

    def isOn(self, roomName : str, slotId):
        for slot in self.timeslots:
            if slot.room.name == roomName and slot.id == slotId:
                return slot.heating, slot.active

    def switchActors(self, roomName : str, on : bool):
        for actor in self.actors[roomName]:
            if on:
                self.logger.Debug(f"Switch actor {actor.on} ")
                requests.get(actor.on)
            else:
                self.logger.Debug(f"Switch actor {actor.off} ")
                requests.get(actor.off)

    def heatPump(self, on : bool):
        try:
            if on:
                requests.get("http://zentralheizung/cm?cmnd=Power%20On")
            else:
                requests.get("http://zentralheizung/cm?cmnd=Power%20Off")
        except:
            self.logger.Error(f"no connection to Zentralheizung: {traceback.format_exc}")
            




