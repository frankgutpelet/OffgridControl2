import requests
import json

class TempReader:
    def __init__(self):
        pass


    def getValues(self):
        ret = json.loads(requests.get('http://lmair/weather.json').text)
        return ret