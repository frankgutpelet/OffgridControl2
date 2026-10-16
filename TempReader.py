import requests
import json

class TempReader:
    def __init__(self):
        pass


    def getValues(self):
        try:
            ret = json.loads(requests.get('http://lmair/weather.json').text)
        except:
            ret = {}
        return ret