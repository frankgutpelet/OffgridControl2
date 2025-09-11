from django.shortcuts import render
from html import unescape
#from Settings import Settings
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from TempReader import TempReader
import requests
import json
import sys
import os
import socket

# Zwei Ebenen höher gehen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from IInverter import InverterValues


# Create your views here.

def makeTableEntry(key, value):
    return "<tr>\n" + \
           "<td class=\"auto-style2\" style=\"width: 484px\"><strong>" + key + "</strong></td>\n" + \
           "<td class=\"auto-style2\"><strong>" + value + "</strong></td>\n" + \
           "<td> <button class=\"device-button\" data-device=\"" + key + "\" data-mode=\"ON\">ON</button> </td>\n" + \
           "<td> <button class=\"device-button\" data-device=\"" + key + "\" data-mode=\"AUTO\">AUTO</button> </td>\n" + \
           "<td> <button class=\"device-button\" data-device=\"" + key + "\" data-mode=\"OFF\">OFF</button> </td>\n" + \
           "</tr>"

def getDeviceTable(inverterValues : InverterValues):
    #deviceTable = str()
    #for device in victronReader.devices:
    #    deviceTable += makeTableEntry(device['name'], device['state'])
    return list()

def index(request):

    socketResponse = ReadSocketValues()
    inverterValues = InverterValues.from_json(socketResponse.split("|"))

    deviceTable = getDeviceTable(inverterValues)

    if 'mode' in request.GET:
        ChangeSettings(request.GET['device'], request.GET['mode'])

    return render(request, 'Monitor/base.html',
                      {'batV': str(inverterValues.BatteryVoltage), 'batI': str(inverterValues.BatteryCurrent), 'solV': str(inverterValues.VoltageSolar1),
                       'solarSupply': 'Mains', 'chargingState': 'unknown',
                       'solarPower': str(inverterValues.PowerSolar1 + inverterValues.PowerSolar2), 'today' : '',
                       'yesterday' : '', 'sumI' : str(inverterValues.CurrentSolar1 + InverterValues.CurrentSolar2), 'soc' : str(InverterValues.SOC),
                       'deviceTable': unescape(deviceTable), 'temperaturTable' : unescape(getTemperatures())})

def ChangeSettings(device : str, mode : str):
    return 
    settings = Settings("../Settings.xml")
    app = settings.getApproval(device)
    app.mode = mode
    settings.changeApproval(app.name, app)
    settings.save()


def getTemperatures():
    tempReader = TempReader()
    values = tempReader.getValues()
    table = "<tbody><tr>\n" + \
       "<td class=\"auto-style1\"><strong>Name</strong></td>\n" + \
       "<td class=\"auto-style1\"><strong>Temperatur</strong></td>\n" + \
        "</tr></tbody>"
    file = open("config.json", "r")
    config = json.load(file)
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

    return table



def monitor_data(request):
    global victronReader

    deviceTable = str()
    for device in victronReader.devices:
        deviceTable += makeTableEntry(device['name'], device['state'])
    # Abrufen der aktuellen Daten
    data = {
        'batV': victronReader.batV,
        'batI': victronReader.batI,
        'solV': victronReader.solV,
        'solarSupply': victronReader.supply,
        'chargingState': victronReader.chargemode,
        'solarPower': str(round(float(victronReader.batV) * float(victronReader.batI))),
        'today': str(victronReader.today),
        'yesterday': str(victronReader.yesterday),
        'sumI': str(victronReader.sumI),
        'soc': str(victronReader.soc),
        'sumP' : str(calcSupP()),
        'deviceTable' : getDeviceTable()
    }
    return JsonResponse(data)

def ReadSocketValues():
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', 23456))
                while True:
                    s.listen()
                    conn, addr = s.accept()
                    with conn:
                        try:
                            data = ""
                            while True:
                                data += conn.recv(2048).decode()
                                if "" != data:
                                    break
                            return data
                        except:
                            conn.close()
                            s.close()
        except:
            continue

@csrf_exempt
def update_device(request):
    if request.method == 'POST':
        # Hole die POST-Daten
        data = json.loads(request.body)
        mode = data.get('mode')
        device = data.get('device')
        ChangeSettings(device, mode)

        result = {
            "status": "success",
            "message": f"Gerät {device} auf {mode} gesetzt"
        }

        return JsonResponse(result)

    return JsonResponse({"status": "error", "message": "Ungültige Anfrage"})