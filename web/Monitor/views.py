from django.shortcuts import render
from html import unescape
from Settings import Settings
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from TempReader import TempReader
import requests
import json
import socket
from IInverter import IInverter
import time

# Create your views here.
socketConnection = None

def makeTableEntry(key, state, mode):
    return "<tr>\n" + \
           "<td class=\"auto-style2\" style=\"width: 484px\"><strong>" + key + "</strong></td>\n" + \
           "<td class=\"auto-style2\"><strong>" + state + "</strong></td>\n" + \
           "<td class=\"auto-style2\"><strong>" + mode + "</strong></td>\n" + \
           "<td> <button class=\"device-button\" data-device=\"" + key + "\" data-mode=\"ON\">ON</button> </td>\n" + \
           "<td> <button class=\"device-button\" data-device=\"" + key + "\" data-mode=\"AUTO\">AUTO</button> </td>\n" + \
           "<td> <button class=\"device-button\" data-device=\"" + key + "\" data-mode=\"OFF\">OFF</button> </td>\n" + \
           "</tr>"

def getDeviceTable(devices : list):
    deviceTable = "<tr>\n" + \
           "<td class=\"auto-style2\" style=\"width: 484px\"><strong>CONSUMER</strong></td>\n" + \
           "<td class=\"auto-style2\"><strong>Status</strong></td>\n" + \
           "<td class=\"auto-style2\"><strong>Modus</strong></td>\n"
    for device in devices:
        state = 'OFF'
        if device['isOn']:
            state = 'ON'
        deviceTable += makeTableEntry(device['name'], state, device['mode'].upper())
    return deviceTable

def index(request):
    print("Monitor triggered")


    if 'mode' in request.GET:
        ChangeSettings(request.GET['device'], request.GET['mode'])

    return render(request, 'Monitor/base.html',
                      {'batV': 'unknown', 'batI': 'unknown', 'solV': 'unknown',
                       'solarSupply': 'Mains', 'chargingState': 'unknown',
                       'solarPower': 'unknown', 'today' : '',
                       'yesterday' : '', 'panI' : 'unknown', 'soc' : 'unknown',
                       'deviceTable': 'unknown', 'temperaturTable' : getTemperatures()})

def ChangeSettings(device : str, mode : str):
    settings = Settings.from_xml_file("../Settings.xml")
    for app in settings.apps:
        if app.name == device:
            app.mode = mode
            print("Change " + device + " to mode: " + mode )
    settings.to_xml_file("../Settings.xml")


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


# überträgt die daten zyklisch zum frontend
def monitor_data(request):
    global socketConnection
    print("Wait for socket values...")
    socketResponse = ""
    try:
        values = ReadSocketValues()
        print("Parse json string: " + values)
        socketResponse = json.loads(values)
        print("Socket Values: " + json.dumps(socketResponse))
        inverterValues = IInverter.InverterValues.from_json(socketResponse['data']['inverter'])
    except:
        print("Cannot parse string as json: " + socketResponse)
        try:
            socketConnection.close()
        except:
            pass
        socketConnection.connect(('localhost', 23456))
        return  JsonResponse(data = {})


    data = {
        'batV': str(inverterValues.BatteryVoltage),
        'batI': str(inverterValues.BatteryCurrent),
        'solV': str(inverterValues.VoltageSolar2),
        'solarSupply': socketResponse['data']['switch'],
        'solarPower': str(inverterValues.PowerSolar1 + inverterValues.PowerSolar2),
        'today': '',
        'yesterday': '',
        'panI': str(inverterValues.CurrentSolar2 + inverterValues.CurrentSolar1),
        'soc': str(inverterValues.SOC),
        'sumP': str(-inverterValues.BatteryPower),
        'consP' : str(inverterValues.InverterOutputPower),
        'deviceTable': getDeviceTable(socketResponse['data']['devices'])
    }
    return JsonResponse(data)


def ReadSocketValues():
    global socketConnection
    data = None
    if not socketConnection:
        print("reconnect Socket")
        socketConnection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socketConnection.connect(('localhost', 23456))
    try:
        data = socketConnection.recv(8192)
        if data:
            print("Received Data " + data.decode())
            return data.decode()
        else:
            raise Exception()
    except:
        print("Server nicht erreichbar - neuverbinden")
        socketConnection = None
        if data:
            print("Received Data after reconnect: " + data.decode())
            return data.decode()
        else:
            raise Exception("Could not reconnect to server")

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

