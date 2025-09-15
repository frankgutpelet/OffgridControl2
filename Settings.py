import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from typing import List, Optional
from datetime import time

class Timer:
    def __init__(self, soc: int, on: time, off: time):
        self.soc = soc
        self.on = on
        self.off = off

    def __repr__(self):
        return f"Timer(soc={self.soc}, on={self.on}, off={self.off})"

    @staticmethod
    def parse_time(time_str: str) -> time:
        """Konvertiert 'HH:MM' in ein datetime.time-Objekt"""
        h, m = map(int, time_str.split(":"))
        return time(hour=h, minute=m)

class App:
    def __init__(self, name: str, dns: str, prio: int, supply: str, mode: str, soc: int,
                 minTimeRunningMinutes: Optional[int] = None, timers: Optional[List[Timer]] = None):
        self.name = name
        self.dns = dns
        self.prio = prio
        self.supply = supply
        self.mode = mode
        self.soc = soc
        self.minTimeRunningMinutes = minTimeRunningMinutes
        self.timers = timers or []

    def __repr__(self):
        return f"App(name='{self.name}', dns='{self.dns}', prio={self.prio}, mode='{self.mode}', soc={self.soc}, timers={self.timers})"

class BatterySettings:
    def __init__(self, minimumSOC: int, maxCurrentA: int):
        self.minimumSOC = minimumSOC
        self.maxCurrentA = maxCurrentA

    def __repr__(self):
        return f"BatterySettings(minimumSOC={self.minimumSOC}, maxCurrentA={self.maxCurrentA})"

class InverterSettings:
    def __init__(self, maxPower: int,):
        self.maxPower = maxPower

    def __repr__(self):
        return f"InverterSettings(maxPowerW={self.maxPower})"

class LoggingSettings:
    def __init__(self, loglevel: str, file: str):
        self.loglevel = loglevel
        self.file = file

    def __repr__(self):
        return f"LoggingSettings(loglevel='{self.loglevel}', file='{self.file}')"

class Settings:
    def __init__(self, battery: BatterySettings, inverter : InverterSettings, logging: LoggingSettings, apps: List[App]):
        self.battery = battery
        self.inverter = inverter
        self.logging = logging
        self.apps = apps

    def getAppByName(self, name : str):
        for app in self.apps:
            if name == app.name:
                return app
        return None

    @staticmethod
    def from_xml_file(xml_file: str):
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Battery settings
        battery_elem = root.find("BatterySettings")
        battery = BatterySettings(
            minimumSOC=int(battery_elem.attrib.get("minimumSOC", 0)),
            maxCurrentA=int(battery_elem.attrib.get("maxCurrentA", 0))
        )
        inverter_elem = root.find("InverterSettings")
        inverter = InverterSettings(
            maxPower=int(inverter_elem.attrib.get("maxPowerW", 0))
        )

        # Logging settings
        logging_elem = root.find("Logging")
        logging = LoggingSettings(
            loglevel=logging_elem.attrib.get("loglevel", "INFO"),
            file=logging_elem.attrib.get("file", "")
        )

        # Apps
        apps = []
        for app_elem in root.find("Approvals").findall("App"):
            timers = []
            for timer_elem in app_elem.findall("Timer"):
                timers.append(Timer(
                    soc=int(timer_elem.attrib.get("soc", 0)),
                    on=Timer.parse_time(timer_elem.attrib.get("on", "00:00")),
                    off=Timer.parse_time(timer_elem.attrib.get("off", "00:00"))
                ))
            min_time = app_elem.attrib.get("minTimeRunningMinutes")
            apps.append(App(
                name=app_elem.attrib.get("name", ""),
                dns=app_elem.attrib.get("dns", ""),
                prio=int(app_elem.attrib.get("prio", 0)),
                supply=app_elem.attrib.get("supply", ""),
                mode=app_elem.attrib.get("mode", ""),
                soc=int(app_elem.attrib.get("soc", 0)),
                minTimeRunningMinutes=int(min_time) if min_time else None,
                timers=timers
            ))

        return Settings(battery=battery, inverter=inverter, logging=logging, apps=apps)

    def __repr__(self):
        return (f"Settings(battery={self.battery}, "
                f"inverter={self.inverter}, "
                f"logging={self.logging}, "
                f"apps={self.apps})")

    def to_xml_file(self, xml_file: str):
        root = ET.Element("Settings")

        # Battery
        battery_elem = ET.SubElement(root, "BatterySettings")
        battery_elem.set("minimumSOC", str(self.battery.minimumSOC))
        battery_elem.set("maxCurrentA", str(self.battery.maxCurrentA))

        # Inverter
        inverter_elem = ET.SubElement(root, "InverterSettings")
        inverter_elem.set("maxPowerW", str(self.inverter.maxPower))

        # Logging
        logging_elem = ET.SubElement(root, "Logging")
        logging_elem.set("loglevel", self.logging.loglevel)
        logging_elem.set("file", self.logging.file)

        # Apps
        approvals_elem = ET.SubElement(root, "Approvals")
        for app in self.apps:
            app_elem = ET.SubElement(approvals_elem, "App")
            app_elem.set("name", app.name)
            app_elem.set("dns", app.dns)
            app_elem.set("prio", str(app.prio))
            app_elem.set("supply", app.supply)
            app_elem.set("mode", app.mode)
            app_elem.set("soc", str(app.soc))
            if app.minTimeRunningMinutes is not None:
                app_elem.set("minTimeRunningMinutes", str(app.minTimeRunningMinutes))

            # Timer
            for timer in app.timers:
                timer_elem = ET.SubElement(app_elem, "Timer")
                timer_elem.set("soc", str(timer.soc))
                timer_elem.set("on", timer.on.strftime("%H:%M"))
                timer_elem.set("off", timer.off.strftime("%H:%M"))

        # In einen String konvertieren
        xml_str = ET.tostring(root, encoding="utf-8")
        # Mit minidom schön formatieren
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")

        # In Datei schreiben
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(pretty_xml)