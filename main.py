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
from webApi import ApiServer


supplySwitch : SonoffSwitch
consumerIndex : int
consumers : list
inverter : IInverter
frontEnd : FrontendInterface
inverterValues : IInverter.InverterValues
logger : Logging
opened_time_Settings : float
settings : Settings


def main():
    global supplySwitch, consumerIndex, consumers, inverter, frontEnd, frontEndThread, inverterValues, logger, opened_time_Settings, settings
    consumerIndex = 0
    logger = Logging()
    logger.setLogLevel("DEBUG")
    opened_time_Settings = os.path.getmtime("Settings.xml")
    settings = Settings.from_xml_file("Settings.xml")
    consumers = settings.apps
    inverter = SPF6000Inverter(logger)
    supplySwitch = SonoffSwitch(logger)
    frontEnd = FrontendInterface(logger)

    consumers = list()
    for app in settings.apps:
        consumers.append(Consumer(app, logger))

    api = ApiServer(logger, supplySwitch, consumers, inverter, settings)
    api.start()

    inverterValues = inverter.getValues()
    frontEndThread = threading.Thread(target=frontEndThreadFunc, daemon=True)
    frontEndThread.start()
    logger.Debug("Thread started")


    while(True):
        try:
            inverterValues = inverter.getValues()
            if handleOvercurrent(settings.battery, inverterValues.BatteryCurrent):
                continue
            if handleMinimalSOC(settings.battery, inverterValues.SOC):
                continue
            if (SonoffSwitch.SwitchState.OFF == supplySwitch.getSwitchState()):
                logger.Debug("SwitchState is OFF")
            handleNextConsumer(settings.battery, settings.inverter)
            attentiveTimeout(10, settings.battery)
        except:
            logger.Error("Exception in maintread: " + traceback.format_exc())

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
        logger.Debug("Settings wurden geändert. Reload")
        settings = None
        settings = Settings.from_xml_file("Settings.xml")

        for consumer in consumers:
            app = settings.getAppByName(consumer.name)
            if app:
                consumer.updateSettings(app)


def handleOvercurrent(batterySettings : BatterySettings, current : float):
    global state
    if batterySettings.maxCurrentA < (-current):
        switchSolarSupply(False)
        switchOffConsumers()
        timeout(15)
        return True
    return False

def handleMinimalSOC(batterySettings : BatterySettings, soc : int):
    global state, logger
    logger.Debug("Check SOC")
    if batterySettings.minimumSOC > soc:
        logger.Debug("SOC to low: " + str(soc) + "% < " + str(batterySettings.minimumSOC) + "%" )
        switchSolarSupply(False)
        switchOffConsumers()
        timeout(5)
        return True
    elif (SonoffSwitch.SwitchState.ON != supplySwitch.getSwitchState()
            and (settings.battery.minimumSOC + 3) > inverterValues.SOC):
                logger.Debug("Switch is OFF - treshold")
    else:
        switchSolarSupply(True)


def handleNextConsumer(batterySettings : BatterySettings, inverterSettings : InverterSettings):
    global consumers, consumerIndex, inverter, inverterValues, logger
    inverterValues = inverter.getValues()
    consumer = consumers[consumerIndex]
    # Wenn der Inverter und die Batterie noch nicht an der Obergrenze ist wird noch ein zusätzlicher Verbraucher
    # eingeschaltet, ansonsten wird einer ausgeschaltet
    #todo Dies muss noch validiert werden, nicht dass hier ein Verbraucher die ganze Zeit ein- und wieder ausgeschaltet wird
    if ((batterySettings.maxCurrentA - 30) > (-inverterValues.BatteryCurrent)):
        logger.Debug("Condition1 OK: " + str(batterySettings.maxCurrentA - 30) + ">" + str(-inverterValues.BatteryCurrent))
    if ((batterySettings.maxCurrentA - 30) > (-inverterValues.BatteryCurrent)):
        logger.Debug("Condition2 OK: " + str(inverterSettings.maxPower - 1000) + ">" + str(inverterValues.InverterOutputPower))
    if(     ((batterySettings.maxCurrentA - 30) > (-inverterValues.BatteryCurrent))
        and ((inverterSettings.maxPower - 1000) > inverterValues.InverterOutputPower)):
        consumer.approve(inverterValues.SOC)
    else:
        consumer.prohibit(True)

    consumer.push()

    consumerIndex += 1
    if consumerIndex >= len(consumers):
        consumerIndex = 0

def switchSolarSupply(on : bool):
    global supplySwitch, inverter, logger, settings
    if on:
        if SonoffSwitch.SwitchState.ON ==  supplySwitch.getSwitchState():
            return
        logger.Debug("Wake up Inverter from Standby mode")
        inverter.setPowerSave(False)
        attentiveTimeout(30, settings.battery)
        logger.Debug("Switch on Solar supply")
        supplySwitch.switch(SonoffSwitch.SwitchState.ON)
    else:
        if SonoffSwitch.SwitchState.OFF == supplySwitch.getSwitchState():
            return
        logger.Debug("Switch off inverter")
        supplySwitch.switch(SonoffSwitch.SwitchState.OFF)
        attentiveTimeout(30, settings.battery)
        logger.Debug("Set Inverter to standby")
        inverter.setPowerSave(True)

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
    global inverter, inverterValues, logger
    for i in range(0, seconds):
        inverterValues = inverter.getValues()
        checkSettings()
        if handleOvercurrent(batterySettings, inverterValues.BatteryCurrent):
            return
        time.sleep(1)

def sendDataToFrontend():
    global frontEnd, inverterValues, logger, supplySwitch
    frontendJson = {
        'data' : dict()
    }
    frontendJson['data']['inverter'] = inverterValues.toJson()
    frontendJson['data']['devices'] = list()
    state = supplySwitch.getSwitchState()
    if supplySwitch.SwitchState.OFF == state:
        frontendJson['data']['switch'] = "MAINS"
    elif supplySwitch.SwitchState.ON == state:
        frontendJson['data']['switch'] = "SOLAR"
    elif supplySwitch.SwitchState.OFFLINE == state:
        frontendJson['data']['switch'] = "OFFLINE"
    else:
        frontendJson['data']['switch'] = "ERROR"

    for consumer in consumers:
        frontendJson['data']['devices'].append(consumer.toJson())

    logger.Debug("Send Data to fronted")
    frontEnd.write(json.dumps(frontendJson))

if __name__ == '__main__':
    main()

