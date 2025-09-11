from Settings import Settings
from Settings import BatterySettings
from Settings import InverterSettings
from IInverter import IInverter
from GrowattInverter import SPF6000Inverter
from Consumer import Consumer
from MyLogging import Logging
from SonoffSwitch import SonoffSwitch
from FrontendInterface import FrontendInterface
import time


supplySwitch : SonoffSwitch
consumerIndex : int
consumers : list
inverter : IInverter
frontEnd : FrontendInterface

def main():
    global supplySwitch, consumerIndex, consumers, inverter, frontEnd

    consumerIndex = 0
    logger = Logging()
    logger.setLogLevel("DEBUG")
    settings = Settings.from_xml_file("Settings.xml")
    consumers = settings.apps
    inverter = SPF6000Inverter()
    supplySwitch = SonoffSwitch()
    frontEnd = FrontendInterface(logger)

    consumers = list()
    for app in settings.apps:
        consumers.append(Consumer(app, logger))


    while(True):
        if handleOvercurrent():
            continue
        if handleMinimalSOC():
            continue
        handleNextConsumer(settings.battery, settings.inverter)
        attentiveTimeout(10, settings.battery)

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
    global consumers, consumerIndex, inverter
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
    global inverter
    for i in range(0, minutes*60):
        inverterValues = inverter.getValues()
        sendDataToFrontend(inverterValues)
        time.sleep(1)

def attentiveTimeout(seconds : int, batterySettings : BatterySettings):
    global inverter
    for i in range(0, seconds):
        inverterValues = inverter.getValues()
        sendDataToFrontend(inverterValues)
        if handleOvercurrent(batterySettings, inverterValues.BatteryCurrent):
            return
        time.sleep(1)

def sendDataToFrontend(inverterValues : IInverter.InverterValues):
    global frontEnd
    frontEnd.write(inverterValues.toString())

if __name__ == '__main__':
    main()

