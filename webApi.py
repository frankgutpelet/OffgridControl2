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


class ConsumerBody(BaseModel):
    name: str
    mode: str

class ApiServer:

    logger : Logging
    inverter : IInverter
    sonoff : SonoffSwitch
    consumerList : list[Consumer]
    settings : Settings

    def __init__(self, logger, sonoff, consumers, inverter, settings, host="0.0.0.0", port=8001):
        """
        backend: Instanz deines bestehenden Backends
        host, port: Serverkonfiguration
        """
        self.logger = logger
        self.inverter = inverter
        self.consumerList = consumers
        self.sonoff = sonoff
        self.settings = settings
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
        self._setup_routes()


    def _setup_routes(self):
        @self.app.get("/api/inverterValues", summary="Liefert aktuelle Inverter Werte")
        def get_inverter_values():
            return {"values": self.inverter.getValues().toJson()}

        @self.app.get("/api/get_consumers", summary="Liefert aktuelle Consumers und deren Status")
        def get_werte():
            try:
                values = {'devices' : []}
                for consumer in self.consumerList:
                    values['devices'].append(consumer.toJson())
                return values
            except:
                self.logger.Error(traceback.format_exc())

        @self.app.get("/api/get_supplyState", summary="Liefert aktuelle Consumers und deren Status")
        def get_werte():
            return {"supplyState": self.sonoff.getSwitchStateAsString()}

        @self.app.post("/api/consumer/", summary="Fügt neuen Wert hinzu")
        def set_consumerState(body : ConsumerBody):
            if not body.status in ["ON", "AUTO", "OFF"]:
                return {"status": "Error - wrong status"}
            self.logger.Debug(f"Set consumer {body.name} to {body.mode}")
            for app in self.settings.apps:
                if body.name == app.name:
                    app.mode = body.mode
                    self.settings.to_xml_file()
                    return {"status": "ok"}
            return {"status": "error"}

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

    def getTemperatures(self):
        # TempReader liefert lokale Sensorwerte
        tempReader = TempReader()
        values = tempReader.getValues()

        table_data = []

        # config.json laden
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
        except Exception as e:
            print("Fehler beim Laden der config.json:", e)
            return []

        # Lokale Sensoren
        for setting in config:
            temp = None
            if "id" in config[setting] and config[setting]["id"] in values:
                val = values[config[setting]["id"]].get("temperature")
                if val != "":
                    try:
                        temp = float(val)
                    except:
                        temp = None

            # Externe Sensoren über URL
            if "url" in config[setting]:
                try:
                    res = requests.get(config[setting]["url"], timeout=2)
                    temp = float(res.text.replace(",", "."))
                except:
                    temp = None

            table_data.append({"name": setting, "temp": temp})

        return table_data

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
