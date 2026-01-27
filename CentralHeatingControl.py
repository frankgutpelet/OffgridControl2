import json
import logging
import threading
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import xml.etree.ElementTree as ET
import traceback
import time, datetime
from enum import Enum

from Heizungssteuerung import TimeSlot


class CentralHeatingControl:
    class Room(BaseModel):
        name: str
        url: Optional[str] = None
        channel: Optional[str] = None

    class TimeSlot(BaseModel):  # Von BaseModel erben!
        room: 'CentralHeatingControl.Room'
        time: str  # Im XML war es ein String "06:00"
        stop: str
        temp: float
        day: str

    weekday = {
        'Mo' : 0,
        'Di' : 1,
        'Mi' : 2,
        'Do' : 3,
        'Fr' : 4,
        'Sa' : 5,
        'So' : 6
    }

    def __init__(self, xmlfile, logger):
        self.xml_file = Path(xmlfile)
        self.logger = logger
        self.room_profiles = {} # Für dein Dictionary
        self.loadXml()
        self.controlThread = threading.Thread(target=self.controlThread, daemon=True)
        self.controlThread.start()

    def loadXml(self):
        if not self.xml_file.exists():
            self.logger.Info(f"{self.xml_file} nicht gefunden")
            return

        tree = ET.parse(self.xml_file)
        root = tree.getroot()

        # Listen vor dem Laden leeren, um Duplikate bei erneutem Aufruf zu vermeiden
        self.timeslots = []


        for room_el in root.findall("room"):
            name = room_el.get("name")
            channel = room_el.get("channel")
            url = room_el.get("url")

            # Instanziierung über die Klasse
            current_room = self.Room(name=name, url=url, channel=channel)

            room_slots = []
            for slot_el in room_el.findall("slot"):
                new_slot = self.TimeSlot(
                    room=current_room,  # Komma war vergessen
                    time=slot_el.get("time"),
                    stop="24:00",
                    temp=float(slot_el.get("temp")),
                    day=slot_el.get("days", "1-7")
                )
                self.timeslots.append(new_slot)
                room_slots.append(new_slot)

            self.room_profiles[name] = {
                "slots": room_slots,
                "channel": channel,
                "url": url
            }
    def controlThread(self):
        logging.debug("Control thread started")
        while True:
            try:
                for slot in self.timeslots:
                    slot : TimeSlot
                    if self.isActive(slot):
                        self.logger.Debug(f"Slot {slot.room.name} {slot.time} is active")
                    else:
                        self.logger.Debug(f"Slot{slot.room.name} {slot.time} is not active")
            except:
                self.logger.Error(f"Error in controlThread: {traceback.format_exc()}")

            time.sleep(10)

    def isActive(self, slot: TimeSlot) -> bool:
        now = datetime.datetime.now()
        if not self.isToday(slot, now):
            return False
        if now.time() > datetime.time.fromisoformat(slot.time):
            return not self.laterSlotActive(slot, now)

    def laterSlotActive(self, slot: TimeSlot, now : datetime.datetime) -> bool:
        for elem in self.timeslots:
            if elem == slot:
                continue
            if elem.room.name != slot.room.name:
                continue
            elemTime = datetime.time.fromisoformat(elem.time)
            slotTime = datetime.time.fromisoformat(slot.time)
            if elemTime < slotTime:
                continue
            if slotTime > now.time():
                continue
            return True
        return False


    def isToday(self, slot : TimeSlot, now : datetime.datetime) -> bool:
        if slot.day == "1-7":
            return True
        if slot.day == "1-5" and now.weekday() <= 5:
            return True
        if slot.day == "6-7" and now.weekday() > 5:
            return True
        if now.weekday() == self.weekday[slot.day]:
            return True

        return False

