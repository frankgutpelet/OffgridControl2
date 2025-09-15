from Settings import Settings
from Settings import BatterySettings
from Settings import InverterSettings
from IInverter import IInverter
from GrowattInverter import SPF6000Inverter
from Consumer import Consumer
from MyLogging import Logging
from SonoffSwitch import SonoffSwitch
from FrontendInterface import FrontendInterface
import time, json
import threading
import traceback
import os


supplySwitch : SonoffSwitch
consumerIndex : int
consumers : list
inverter : IInverter
frontEnd : FrontendInterface
inverterValues : IInverter.InverterValues
logger : Logging
opened_time_Settings : float


def main():
    global supplySwitch, consumerIndex, consumers, inverter, frontEnd, frontEndThread, inverterValues, logger, opened_time_Settings
    consumerIndex = 0
    logger = Logging()
    logger.setLogLevel("DEBUG")
    opened_time_Settings = os.path.getmtime("Settings.xml")
    settings = Settings.from_xml_file("Settings.xml")
    consumers = settings.apps
    inverter = SPF6000Inverter(logger)
    supplySwitch = SonoffSwitch()
    frontEnd = FrontendInterface(logger)

    consumers = list()
    for app in settings.apps:
        consumers.append(Consumer(app, logger))

    inverterValues = inverter.getValues()
    frontEndThread = threading.Thread(target=frontEndThreadFunc, daemon=True)
    frontEndThread.start()
    logger.Debug("Thread started")


    while(True):
        inverterValues = inverter.getValues()
        if handleOvercurrent(settings.battery, inverterValues.BatteryCurrent):
            continue
        if handleMinimalSOC(settings.battery, inverterValues.SOC):
            continue
        handleNextConsumer(settings.battery, settings.inverter)
        attentiveTimeout(10, settings.battery)

def frontEndThreadFunc():
    global logger
    logger.Debug("Frontend Tread started")
    while True:
        try:
            sendDataToFrontend()
        except:
            logger.Error("sendTo Frontend failed: " + traceback.format_exc())
        time.sleep(1)

def checkSettings():
    global opened_time_Settings, consumers
    if opened_time_Settings != os.path.getmtime("Settings.xml"):
        opened_time_Settings = os.path.getmtime("Settings.xml")
        logger.Debug("Settings wurden geändert. Relead")
        settings = None
        settings = Settings.from_xml_file("Settings.xml")

        for consumer in consumers:
            app = settings.getAppByName(consumer.name)
            if app:
                consumer.updateSettings(app)


def handleOvercurrent(batterySettings : BatterySettings, current : float):
    global supplySwitch, state
    if batterySettings.maxCurrentA < (-current):
        supplySwitch.switch(SonoffSwitch.SwitchState.OFF)
        switchOffConsumers()
        timeout(15)
        return True
    return False

def handleMinimalSOC(batterySettings : BatterySettings, soc : int):
    global state
    if batterySettings.minimumSOC > soc:
        supplySwitch.switch(SonoffSwitch.SwitchState.OFF)
        switchOffConsumers()
        timeout(10)
        return True
    pass

def handleNextConsumer(batterySettings : BatterySettings, inverterSettings : InverterSettings):
    global consumers, consumerIndex, inverter, inverterValues
    inverterValues = inverter.getValues()
    consumer = consumers[consumerIndex]
    # Wenn der Inverter und die Batterie noch nicht an der Obergrenze ist wird noch ein zusätzlicher Verbraucher
    # eingeschaltet, ansonsten wird einer ausgeschaltet
    #todo Dies muss noch validiert werden, nicht dass hier ein Verbraucher die ganze Zeit ein- und wieder ausgeschaltet wird
    if(     ((batterySettings.maxCurrentA - 30) > (-inverterValues.BatteryCurrent))
        and ((inverterSettings.maxPower - 1000) > inverterValues.InverterOutputPower)):
        consumer.approve(inverterValues.SOC)
    else:
        consumer.prohibit()

    consumer.push()

    consumerIndex += 1
    if consumerIndex >= len(consumers):
        consumerIndex = 0

def switchOffConsumers():
    global consumers, consumerIndex
    consumerIndex = 0
    for consumer in consumers:
        if "on" == consumer.mode.lower():
            continue
        consumer.prohibit(True)
        consumer.push()

def timeout(minutes : int):
    global inverter, inverterValues
    for i in range(0, minutes*60):
        inverterValues = inverter.getValues()
        checkSettings()
        time.sleep(1)

def attentiveTimeout(seconds : int, batterySettings : BatterySettings):
    global inverter, inverterValues
    for i in range(0, seconds):
        inverterValues = inverter.getValues()
        checkSettings()
        if handleOvercurrent(batterySettings, inverterValues.BatteryCurrent):
            return
        time.sleep(1)

def sendDataToFrontend():
    global frontEnd, inverterValues, logger
    frontendJson = {
        'data' : dict()
    }
    frontendJson['data']['inverter'] = inverterValues.toJson()
    frontendJson['data']['devices'] = list()
    for consumer in consumers:
        frontendJson['data']['devices'].append(consumer.toJson())

    logger.Debug("Send Data to fronted")
    frontEnd.write(json.dumps(frontendJson))

if __name__ == '__main__':
    main()

