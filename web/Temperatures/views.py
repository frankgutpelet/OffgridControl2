from django.shortcuts import render
from TempReader import TempReader
import json
import requests


# Create your views here.


def index(request):

    tempReader = TempReader()
    values = tempReader.getValues()
    table = "<tbody><tr>\n" + \
       "<td class=\"auto-style1\"><strong>Name</strong></td>\n" + \
       "<td class=\"auto-style1\"><strong>Temperatur</strong></td>\n" + \
        "</tr></tbody>"
    file = open("config.json", "r")
    config = json.load(file)
    print("geöffnet")
    file.close()

    for value in values:
        if "temperature" in values[value]:
            temp = values[value]["temperature"]
            if temp == "":
                continue
            for setting in config:
                if "id" in config[setting] and value == config[setting]['id']:
                    table += "<tr>\n" + \
                   "<td class=\"auto-style1\"><strong>" + setting + "</strong></td>\n" + \
                   "<td class=\"auto-style1\"><strong>" + temp + "°C</strong></td>\n" + \
                    "</tr>"

    for setting in config:
        if "url" in config[setting]:
            try:
                temp = requests.get(config[setting]['url']).text
            except:
                temp = "unknown"
            table += "<tr>\n" + \
                     "<td class=\"auto-style1\"><strong>" + setting + "</strong></td>\n" + \
                     "<td class=\"auto-style1\"><strong>" + temp + "°C</strong></td>\n" + \
                     "</tr>"

    return render(request, 'Temperatures/base.html',
              {'batteryTable': table})

