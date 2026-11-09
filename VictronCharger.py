"""Read Victron SmartSolar Instant Readout advertisements over Bluetooth LE."""

import asyncio
import re
import threading
import time
import traceback

try:
    from bleak import BleakScanner
    from victron_ble.devices import detect_device_type
except ImportError:
    BleakScanner = None
    detect_device_type = None


class VictronCharger:
    def __init__(self, name, address, key, logger):
        self.name = name
        self.address = address.lower().strip()
        self.key = key.strip()
        self.logger = logger
        self._lock = threading.Lock()
        self._values = {
            "charging_current": 0.0,
            "solar_power": 0.0,
            "online": False,
            "last_seen": None,
        }

    def getValues(self):
        with self._lock:
            values = dict(self._values)
        if values["last_seen"] is not None and time.time() - values["last_seen"] > 30:
            values["online"] = False
        values.pop("last_seen", None)
        return values

    def update(self, payload):
        with self._lock:
            if payload.get("battery_charging_current") is not None:
                self._values["charging_current"] = float(payload["battery_charging_current"])
            if payload.get("solar_power") is not None:
                self._values["solar_power"] = float(payload["solar_power"])
            self._values.update(online=True, last_seen=time.time())


class VictronChargerManager:
    MANUFACTURER_ID = 0x02E1

    def __init__(self, chargers, logger):
        self.chargers = chargers
        self.logger = logger
        self._by_address = {charger.address: charger for charger in chargers if charger.address}
        self._valid_keys = {}
        self._decoded_addresses = set()
        self._decode_errors = set()
        self._unknown_addresses_logged = set()
        self._stats_lock = threading.Lock()
        self._stats = self._new_stats()
        self._scan_windows = 0

        for charger in chargers:
            if not re.fullmatch(r"[0-9a-fA-F]{32}", charger.key):
                logger.Error(
                    f"Victron {charger.name}: Advertisement Key hat ein ungueltiges Format "
                    "(erwartet werden 32 Hex-Zeichen; Schluesselinhalt wird nicht protokolliert)"
                )
                continue
            if not charger.address:
                logger.Error(f"Victron {charger.name}: Bluetooth-Adresse fehlt")
                continue
            self._valid_keys[charger.address] = charger.key
            logger.Info(f"Victron {charger.name}: BLE konfiguriert, Adresse {charger.address}, Schluessel-Format OK")

        if not chargers:
            logger.Info("Victron BLE: keine Laderegler konfiguriert")
            return
        if BleakScanner is None or detect_device_type is None:
            logger.Error("Victron BLE: Bibliotheken fehlen; bleak und victron-ble muessen in der Laufzeitumgebung installiert sein")
            return
        if not self._valid_keys:
            logger.Error("Victron BLE: Scan nicht gestartet, kein gueltiger Laderegler konfiguriert")
            return

        logger.Info(f"Victron BLE: Scanner wird fuer {len(self._valid_keys)} Laderegler gestartet")
        threading.Thread(target=self._run, daemon=True, name="VictronBLE").start()

    @staticmethod
    def _new_stats():
        return {
            "ble_advertisements": 0,
            "victron_manufacturer": 0,
            "instant_readout": 0,
            "configured_address": 0,
            "decoded": 0,
            "record_types": {},
            "configured_record_types": {},
        }

    def getValues(self):
        return [dict(name=charger.name, **charger.getValues()) for charger in self.chargers]

    def getTotalPower(self):
        return sum(values["solar_power"] for values in self.getValues())

    def _count(self, name):
        with self._stats_lock:
            self._stats[name] += 1

    def _count_record_type(self, record_type, configured):
        with self._stats_lock:
            self._stats["record_types"][record_type] = self._stats["record_types"].get(record_type, 0) + 1
            if configured:
                configured_types = self._stats["configured_record_types"]
                configured_types[record_type] = configured_types.get(record_type, 0) + 1

    def _take_stats(self):
        with self._stats_lock:
            stats = self._stats
            self._stats = self._new_stats()
        return stats

    def _run(self):
        try:
            asyncio.run(self._scan())
        except Exception:
            self.logger.Error("Victron BLE Scanner beendet: " + traceback.format_exc())

    async def _scan(self):
        def callback(device, advertisement):
            address = device.address.lower()
            self._count("ble_advertisements")

            charger = self._by_address.get(address)
            if charger is not None:
                self._count("configured_address")

            raw = advertisement.manufacturer_data.get(self.MANUFACTURER_ID)
            if not raw:
                return
            self._count("victron_manufacturer")
            self._count_record_type(f"0x{raw[0]:02X}", address in self._valid_keys)

            if raw[0] != 0x10:
                return
            self._count("instant_readout")

            if address not in self._valid_keys:
                if address not in self._unknown_addresses_logged and len(self._unknown_addresses_logged) < 5:
                    self._unknown_addresses_logged.add(address)
                    self.logger.Info(
                        f"Victron Instant Readout von nicht konfigurierter BLE-Adresse {device.address}; "
                        "MAC-Adresse in Settings.xml pruefen"
                    )
                return

            try:
                device_type = detect_device_type(raw)
                if device_type is None:
                    self.logger.Error(
                        f"Victron {charger.name}: Instant-Readout empfangen, Geraetetyp wird von victron-ble nicht erkannt"
                    )
                    return
                parsed = device_type(self._valid_keys[address]).parse(raw)
                payload = getattr(parsed, "_data", parsed)
                charger.update(payload)
                self._count("decoded")

                if address not in self._decoded_addresses:
                    self._decoded_addresses.add(address)
                    self.logger.Info(f"Victron {charger.name}: BLE-Daten erfolgreich entschluesselt und gelesen")
            except Exception as error:
                if address not in self._decode_errors:
                    self._decode_errors.add(address)
                    self.logger.Error(
                        f"Victron {charger.name}: Entschluesselung/Parsing fehlgeschlagen "
                        f"({type(error).__name__}: {error}); Adresse und Advertisement Key pruefen"
                    )

        scanner = BleakScanner(detection_callback=callback)
        first_scan = True
        while True:
            try:
                await scanner.start()
                if first_scan:
                    self.logger.Info("Victron BLE: Bluetooth-Scan aktiv")
                    first_scan = False
                await asyncio.sleep(10)
                await scanner.stop()
                self._scan_windows += 1
                if self._scan_windows % 3 == 0:
                    stats = self._take_stats()
                    charger_values = self.getValues()
                    charger_summary = "; ".join(
                        f"{charger['name']}={charger['charging_current']:.1f} A "
                        f"/ {charger['solar_power']:.0f} W "
                        f"({'online' if charger['online'] else 'offline'})"
                        for charger in charger_values
                    ) or "keine konfigurierten Lader"
                    self.logger.Info(
                        f"Victron Messwerte: {charger_summary}"
                    )
                    self.logger.Info(
                        "Victron BLE Diagnose (letzte 30 s): "
                        f"BLE-Anzeigen={stats['ble_advertisements']}, "
                        f"Victron-Herstellerdaten={stats['victron_manufacturer']}, "
                        f"Instant-Readout={stats['instant_readout']}, "
                        f"konfigurierte Adressen={stats['configured_address']}, "
                        f"erfolgreich entschluesselt={stats['decoded']}, "
                        f"Pakettypen gesamt={stats['record_types']}, "
                        f"Pakettypen konfigurierte Geraete={stats['configured_record_types']}"
                    )
                    if stats["ble_advertisements"] == 0:
                        self.logger.Error(
                            "Victron BLE: keinerlei Bluetooth-Anzeigen empfangen; Bluetooth-Adapter, "
                            "Berechtigungen und Reichweite auf dem Rechner pruefen"
                        )
                    elif stats["victron_manufacturer"] == 0:
                        self.logger.Error(
                            "Victron BLE: Bluetooth funktioniert, aber keine Victron-Anzeigen empfangen; "
                            "Geraete in Reichweite und Instant Readout in VictronConnect pruefen"
                        )
                    elif stats["instant_readout"] == 0:
                        self.logger.Error(
                            "Victron BLE: Victron erkannt, aber kein Instant Readout; "
                            "Instant Readout in VictronConnect aktivieren"
                        )
                    elif stats["configured_address"] == 0:
                        self.logger.Error(
                            "Victron BLE: Instant Readout empfangen, aber keine konfigurierte Adresse passt; "
                            "MAC-Adressen in Settings.xml pruefen"
                        )
                    elif stats["decoded"] == 0:
                        self.logger.Error(
                            "Victron BLE: konfigurierte Adresse gesehen, aber keine Daten entschluesselt; "
                            "Advertisement Key pruefen"
                        )
            except Exception:
                self.logger.Error("Victron BLE Scan fehlgeschlagen: " + traceback.format_exc())
                try:
                    await scanner.stop()
                except Exception:
                    pass
                await asyncio.sleep(5)
