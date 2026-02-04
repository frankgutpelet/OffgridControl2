import json
import logging
import traceback
from typing import Callable

import requests
import time
import threading
from MyLogging import Logging

from pydantic import BaseModel

PULL_INTERVAL = 1

class TempPuller:
    class Sensor(BaseModel):
        url : str
        callback: Callable
        param : str

    sensors : list[Sensor]
    def __init__(self, logger : Logging):
        self.sensors = list()
        self.logger = logger
        self.thread = threading.Thread(target=self.pullThread, daemon=True)
        self.thread.start()

    def addSensor(self, url : str, callback : Callable, param):
        self.sensors.append(self.Sensor(url=url, callback=callback, param=param))

    def pullThread(self):
        while True:
            for sensor in self.sensors:
                try:
                    response = requests.get(sensor.url, timeout=0.8)

                    if response.status_code == 200:
                        data = response.json()
                        self.logger.Debug(f"response from {sensor.url}: {json.dumps(data)}")
                        temp = data.get("temperature")
                        sensor.callback(sensor.param, temp)
                    else:
                        self.logger.Error(f"response from {sensor.url}:  {response.status_code}")
                except Exception:
                    self.logger.Debug(f"no response from {sensor.url}")
                    continue

            time.sleep(PULL_INTERVAL)


