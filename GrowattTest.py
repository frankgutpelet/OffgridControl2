from GrowattInverter import SPF6000Inverter
from IInverter import IInverter

class Logging(object):
    def __init__(self):
        pass
    def Debug(self, message):
        print("DEBUG: " + message)
    def Error(self, message):
        print("ERROR: " + message)
    def Info(self, message):
        print("INFO: " + message)

logger = Logging()
values: IInverter.InverterValues

inverter = SPF6000Inverter(logger)

while True:
    values = inverter.getValues()
    print(values.toString())

    print("\nPower Save Mode? Y/N")
    print("Charge Enable? C (on) / D (off)")
    print("Quit: Q")

    answer = input().lower()

    if answer == "n":
        print("\nDisable Power save mode")
        inverter.setPowerSave(False)

    elif answer == "y":
        print("\nEnable Power save mode")
        inverter.setPowerSave(True)

    elif answer == "c":
        print("\nEnable Charging")
        inverter.setChargeEnable(True)

    elif answer == "d":
        print("\nDisable Charging")
        inverter.setChargeEnable(False)

    elif answer == "q":
        exit(0)

    else:
        print("Unknown command")

    continue