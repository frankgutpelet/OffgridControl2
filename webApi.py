import threading
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from MyLogging import Logging
from IInverter import IInverter
from SonoffSwitch import SonoffSwitch
from Consumer import Consumer
from Settings import Settings
import traceback, json, requests
from TempReader import TempReader
from concurrent.futures import ThreadPoolExecutor


class ConsumerBody(BaseModel):
    name: str
    mode: str

class ApiServer:

    logger : Logging
    inverter : IInverter
    sonoff : SonoffSwitch
    consumerList : list[Consumer]
    settings : Settings

    def __init__(self, logger, sonoff, consumers, inverter, settings, host="0.0.0.0", port=8000, homey=None, victron=None):
        """
        backend: Instanz deines bestehenden Backends
        host, port: Serverkonfiguration
        """
        self.logger = logger
        self.inverter = inverter
        self.consumerList = consumers
        self.sonoff = sonoff
        self.settings = settings
        self.homey = homey
        self.victron = victron
        self.host = host
        self.port = port
        self.app = FastAPI(
            title="OffgridControl REST API",
            description="OffgridControl REST API",
            version="1.0.0"
        )
        # In deiner ApiServer.__init__
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        self.templates = Jinja2Templates(directory="templates")
        self._thread = None
        self.table_data = []
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.__checkConfig()
        self.tempReader = TempReader()
        self._setup_routes()

    def getApp(self):
        return self.app
    def getThread(self):
        return self._thread

    def renewData(self):
        self.__checkConfig()
        self.__readTemperatures()

    def __checkConfig(self):
        # config.json laden
        try:
            with open("config.json", "r") as f:
                self.config = json.load(f)
        except Exception as e:
            print("Fehler beim Laden der config.json:", e)
            return []


    def _setup_routes(self):
        @self.app.get("/api/mqtt_status", summary="Liefert den MQTT-Verbindungsstatus")
        async def get_mqtt_status():
            if self.homey is None:
                return {"state": "not_configured", "connected": False, "last_error": "MQTT-Modul ist nicht initialisiert"}
            return self.homey.getStatus()

        @self.app.get("/api/victronValues", summary="Liefert aktuelle Victron Ladereglerwerte")
        def get_victron_values():
            if self.victron is None:
                return {"chargers": [], "total_solar_power": 0}
            return {"chargers": self.victron.getValues(), "total_solar_power": self.victron.getTotalPower()}

        @self.app.get("/api/inverterValues", summary="Liefert aktuelle Inverter Werte")
        async def get_inverter_values():
            return {"values": self.inverter.getValues().toJson()}

        @self.app.get("/api/get_consumers", summary="Liefert aktuelle Consumers und deren Status")
        def get_consumers():
            try:
                values = {'devices' : []}
                for consumer in self.consumerList:
                    values['devices'].append(consumer.toJson())
                return values
            except:
                self.logger.Error(traceback.format_exc())

        @self.app.get("/api/get_supplyState", summary="Liefert aktuelle Supply status")
        def get_supplyState():
            values = self.inverter.getValues()
            if SonoffSwitch.SwitchState.ON == self.sonoff.getSwitchState() and 50 > (values.PowerSolar1 + values.PowerSolar2 + (self.victron.getTotalPower() if self.victron else 0)):
                return {"supplyState": "BATTERY"}
            return {"supplyState": self.sonoff.getSwitchStateAsString()}

        @self.app.post("/api/consumer/", summary="ändert den modus eines consumers")
        def set_consumerState(body : ConsumerBody):
            data = json.loads(body.model_dump_json())
            try:
                if not data['mode'] in ["ON", "AUTO", "OFF"]:
                    return {"status": "Error - wrong status"}
                self.logger.Debug(f"Set consumer {data['name']} to {data['mode']}")
                for app in self.settings.apps:
                    if data['name'] == app.name:
                        app.mode = data['mode']
                        self.settings.to_xml_file()
                        return {"status": "ok"}
                return {"status": "error"}
            except:
                return {"status": "Error", "message": traceback.format_exc() + f"\n Parameter: {json.dumps(data)}"}

        # Route für das Frontend
        @self.app.get("/", summary="Webseite anzeigen")
        def index(request: Request):
            # Hier initiale Platzhalterwerte für Template
            context = {
                "request": request,
                "soc": 50,
                "solarPower": 1200,
                "batV": 48,
                "batI": 5,
                "panI": 10,
                "solV": 30,
                "solarSupply": "ON",
                "sumP": 500,
                "sumPM": 500,
                "chP": 100,
                "kwh": 50,
                "today": 5.2,
                "yesterday": 4.7,
                "deviceTable": "<tr><td>Dummy Device</td><td>ON</td></tr>",
                "temperaturTable": "<tr><td>Dummy Temp</td><td>25°C</td></tr>"
            }
            return self.templates.TemplateResponse("index.html", context)

        @self.app.get("/api/get_temperatures")
        def api_get_temperatures():
            return {"temperatures": self.getTemperatures()}

        @self.app.post("/api/set_mode", summary="Setzt aktuelle Mode ON/AUTO/OFF")
        def api_set_mode(body : ConsumerBody):
            data = json.loads(body.model_dump_json())
            try:
                if not data['mode'] in ["on", "auto", "off"]:
                    return {"status": "Error - wrong status"}
                self.logger.Debug(f"Set mode to {data['mode']}")
                self.inverter.setMode(data['mode'])
            except:
                self.logger.Error(traceback.format_exc())
                return {"status": "Error"}

    def getTemperatures(self):
        return self.table_data

    def __readTemperatures(self):
        values = self.tempReader.getValues()

        def process(setting):
            cfg = self.config[setting]
            temp = None

            if "id" in cfg and cfg["id"] in values:
                val = values[cfg["id"]].get("temperature")
                if val != "":
                    try:
                        temp = float(val)
                    except:
                        pass

            if "url" in cfg:
                try:
                    res = requests.get(cfg["url"], timeout=2)
                    temp = float(res.text.replace(",", "."))
                except:
                    temp = None

            return {"name": setting, "temp": temp}
        results = list(self.executor.map(process, list(self.config.keys())))

        self.table_data = results

    def start(self):
        """Startet den Server in einem separaten Thread."""
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
