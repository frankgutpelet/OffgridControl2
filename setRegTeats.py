import time
from MyLogging import Logging
from GrowattInverter import SPF6000Inverter

def main():
    logger = Logging()
    inverter = SPF6000Inverter(logger, port="/dev/ttyUSB0", baudrate=9600, unit=1)

    try:
        while True:
            values = inverter.getValues()
            if values:
                print(f"SOC: {values.SOC} % | "
                      f"Ubat: {values.BatteryVoltage:.2f} V | "
                      f"Pbatt: {values.BatteryPower:.1f} W")

            cmd = input("Power-Save schalten? (ein/aus/weiter/quit): ").strip().lower()
            if cmd == "ein":
                inverter.setPowerSave(True)
                print(" Power Save eingeschaltet")
            elif cmd == "aus":
                inverter.setPowerSave(False)
                print("Power Save ausgeschaltet")
            elif cmd == "quit":
                break
            else:
                print("weiter ohne Änderung...")

            time.sleep(5)  # Pause vor nächstem SOC-Read

    except KeyboardInterrupt:
        print("Abbruch durch Benutzer")
    finally:
        inverter.client.close()
        print("Verbindung geschlossen.")

if __name__ == "__main__":
    main()
