import json
import os
import threading
import time
import traceback
from datetime import datetime

import paho.mqtt.client as mqtt


class Homey:
    """Publish inverter measurements to an MQTT broker for Homey."""

    CONNECT_REASONS = {
        1: "invalid MQTT protocol version",
        2: "Client-ID vom Broker abgelehnt",
        3: "broker unavailable",
        4: "Benutzername oder Passwort abgelehnt",
        5: "Verbindung nicht autorisiert",
    }

    def __init__(self, inverter, logger, supply_switch=None, victron=None):
        self.inverter = inverter
        self.logger = logger
        self.supply_switch = supply_switch
        self.victron = victron
        self.config_path = os.path.join(os.path.dirname(__file__), "homey_mqtt.json")
        self.config, self.config_error = self._read_config(self.config_path)
        self.topic_prefix = self.config.get("topic_prefix", "offgrid")
        self.interval = max(5, int(self.config.get("publish_interval_seconds", 10)))
        self.grid_positive_import = bool(self.config.get("grid_power_positive_import", True))
        self.last_sample = None
        self._status_lock = threading.Lock()
        self._status = {
            "state": "error" if self.config_error else "connecting",
            "connected": False,
            "config_loaded": self.config_error is None,
            "config_path": self.config_path,
            "broker": self.config.get("broker"),
            "port": int(self.config.get("port", 1883)),
            "client_id": self.config.get("client_id", "offgrid-control"),
            "topic_prefix": self.topic_prefix, "publish_interval_seconds": self.interval,
            "last_error": self.config_error, "last_connected": None, "last_disconnected": None,
            "last_published": None, "published_messages": 0,
        }
        if self.config_error:
            self.logger.Error(self.config_error)
            return

        self.client = mqtt.Client(client_id=self._status["client_id"], clean_session=True)
        username = self.config.get("username")
        if username:
            self.client.username_pw_set(username, self.config.get("password"))
        if self.config.get("tls", False):
            self.client.tls_set()
        self.client.reconnect_delay_set(min_delay=2, max_delay=30)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_connect_fail = self._on_connect_fail
        self.client.on_log = self._on_mqtt_log
        self.client.connect_async(self._status["broker"], self._status["port"], keepalive=60)
        self.client.loop_start()
        self.thread = threading.Thread(target=self._publish_loop, daemon=True)
        self.thread.start()

    @staticmethod
    def _read_config(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as config_file:
                config = json.load(config_file)
            if not isinstance(config, dict) or not config.get("broker"):
                raise ValueError("Pflichtfeld 'broker' fehlt")
            return config, None
        except (OSError, ValueError) as error:
            return {}, f"MQTT-Konfiguration konnte nicht geladen werden: {path} ({error})"

    @staticmethod
    def _timestamp():
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def getStatus(self):
        with self._status_lock:
            return dict(self._status)

    def _set_status(self, **values):
        with self._status_lock:
            self._status.update(values)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            now = self._timestamp()
            self._set_status(state="connected", connected=True, last_error=None, last_connected=now)
            self.logger.Info("Connected to MQTT broker for Homey")
            return
        reason = self.CONNECT_REASONS.get(rc, "MQTT-Verbindung abgelehnt")
        message = f"Broker hat Verbindung abgelehnt (Code {rc}: {reason})"
        self._set_status(state="error", connected=False, last_error=message)
        self.logger.Error(message)

    def _on_disconnect(self, client, userdata, rc):
        now = self._timestamp()
        if rc:
            reason = f"MQTT-Verbindung unerwartet getrennt (Code {rc}; meist Verbindung verloren oder Client-ID doppelt)"
            self._set_status(state="disconnected", connected=False, last_disconnected=now, last_error=reason)
            self.logger.Error(reason)
        else:
            self._set_status(state="disconnected", connected=False, last_disconnected=now)
            self.logger.Info("MQTT disconnected")

    def _on_connect_fail(self, client, userdata):
        message = "MQTT-Verbindungsversuch fehlgeschlagen; Broker und Netzwerk pr?fen"
        self._set_status(state="error", connected=False, last_error=message)
        self.logger.Error(message)

    def _on_mqtt_log(self, client, userdata, level, buf):
        if level & (mqtt.MQTT_LOG_ERR | mqtt.MQTT_LOG_WARNING):
            message = "MQTT: " + str(buf)
            self._set_status(last_error=message)
            self.logger.Error(message)

    def _publish_loop(self):
        while True:
            try:
                values = self.inverter.getValues()
                if values is not None:
                    self.sendValues(values)
            except Exception:
                message = "MQTT/Homey publish error: " + traceback.format_exc()
                self._set_status(last_error=message)
                self.logger.Error(message)
            time.sleep(self.interval)

    def sendValues(self, values):
        if not self.client.is_connected():
            return
        supply = self.supply_switch.getSwitchStateAsString() if self.supply_switch is not None else "UNBEKANNT"
        measurements = {
            "soc": values.SOC,
            "versorgung": supply,
            "gesamtverbrauch_solar": values.InverterOutputPower,
            "gesamtverbrauch_netz": values.MainsPower,
            "solarleistung_ost": values.PowerSolar1,
            "solarleistung_west": values.PowerSolar2,
            "solarleistung_gesamt": values.PowerSolar1 + values.PowerSolar2 + (self.victron.getTotalPower() if self.victron else 0),
        }
        published = 0
        for name, value in measurements.items():
            info = self.client.publish(self.topic_prefix + "/" + name, str(value), qos=1, retain=True)
            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                published += 1
        if published:
            self._set_status(last_published=self._timestamp(), published_messages=self.getStatus()["published_messages"] + published)
        else:
            self._set_status(last_error="MQTT Publish fehlgeschlagen; check broker response")
