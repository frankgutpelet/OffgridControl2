from GrowattInverter import SPF6000Inverter
import json

inverter = SPF6000Inverter()

values = inverter.getValues()

print(json.dumps(values))