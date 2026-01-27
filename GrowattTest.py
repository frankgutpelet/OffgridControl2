from GrowattInverter import SPF6000Inverter
from IInverter import IInverter

class Logging(object):
    def __init__(self):
        pass
    def Debug(self, message):
        print("DEBUG: " + message)
    def Error(self, message):
        print("ERROR: " + message)

logger = Logging()
values : IInverter.InverterValues

inverter = SPF6000Inverter(logger)

while True:
    values = inverter.getValues()
    print(values.toString())
    print("\nPower Save Mode? Y/N Quit: Q")
    answer = input()
    if answer.lower() == "n":
        print("\nDisable Power save mode")
        inverter.setPowerSave(False)
    if answer.lower() == "y":
        print("\nEnable Power save mode")
        inverter.setPowerSave(True)
    if answer.lower() == "q":
        exit(0)
    continue