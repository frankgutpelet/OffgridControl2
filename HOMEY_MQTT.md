# Homey MQTT setup

## Voraussetzungen

- A reachable MQTT broker on the local network (for example Mosquitto).
- Install the MQTT Client and MQTT Hub apps in Homey. Connect MQTT Client to the same broker used by OffgridControl.
- Install paho-mqtt on the OffgridControl computer:

```sh
pip3 install -r requirements-mqtt.txt
```

## Broker config

Copy `homey_mqtt.json.example` to `homey_mqtt.json` and set the broker address, port and credentials. `topic_prefix` must be `offgrid` for the topic map below.

## Homey MQTT Device

Add an MQTT Device in MQTT Hub and choose device class `sensor`. Under **Settings -> Topics**, use this mapping. `displayName` sets the label shown in Homey. Solar and grid consumption are instant power readings in W; SoC is sent as 0-100 percent.

```json
{
  "measure_battery": {"capability": "measure_battery", "displayName": "SoC", "stateTopic": "offgrid/soc"},
  "measure_string": {"capability": "measure_string", "displayName": "Versorgung", "stateTopic": "offgrid/versorgung"},
  "measure_power": {"capability": "measure_power", "displayName": "Gesamtverbrauch Solar", "stateTopic": "offgrid/gesamtverbrauch_solar"},
  "measure_power.1": {"capability": "measure_power", "displayName": "Gesamtverbrauch Netz", "stateTopic": "offgrid/gesamtverbrauch_netz"},
  "measure_power.2": {"capability": "measure_power", "displayName": "Solarleistung Ost", "stateTopic": "offgrid/solarleistung_ost"},
  "measure_power.3": {"capability": "measure_power", "displayName": "Solarleistung West", "stateTopic": "offgrid/solarleistung_west"},
  "measure_power.4": {"capability": "measure_power", "displayName": "Solarleistung Gesamt", "stateTopic": "offgrid/solarleistung_gesamt"}
}
```

In MQTT Hub settings, use percentage scaling `int` so the incoming SoC value (for example `35`) is converted to Homey's internal 0-1 percentage range.

The solar consumption topic publishes inverter `InverterOutputPower` in W. The grid topic publishes Wattwaechter `MainsPower` in W, preserving its sign. PV east, west and total are also in W.
