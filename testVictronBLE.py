#!/usr/bin/env python3
"""Read one configured Victron charger with victron-ble and print decoded data."""

import argparse
import asyncio
import logging
import re
import sys
import time
import xml.etree.ElementTree as ET

try:
    from victron_ble.scanner import Scanner
except ImportError as error:
    print(
        "victron-ble/bleak fehlen in dieser Python-Umgebung. "
        "Installiere requirements-mqtt.txt mit demselben Python wie dieses Skript.",
        file=sys.stdout,
    )
    print(f"Importfehler: {error}", file=sys.stdout)
    raise SystemExit(2)


def load_charger(name, settings_file):
    root = ET.parse(settings_file).getroot()
    chargers = root.find("VictronLaders")
    if chargers is None:
        raise ValueError("Settings.xml enthält keinen Abschnitt <VictronLaders>.")
    for charger in chargers.findall("Lader"):
        if charger.get("name") == name:
            address = (charger.get("address") or "").strip()
            key = (charger.get("key") or "").strip()
            if not address:
                raise ValueError(f"Für {name} ist keine Bluetooth-Adresse eingetragen.")
            if not re.fullmatch(r"[0-9a-fA-F]{32}", key):
                raise ValueError(
                    f"Der Advertisement Key für {name} muss aus 32 Hex-Zeichen bestehen."
                )
            return address, key
    available = ", ".join(charger.get("name", "") for charger in chargers.findall("Lader"))
    raise ValueError(f"Lader {name!r} nicht gefunden. Konfiguriert: {available or '(keine)'}")


async def scan(address, key, duration):
    scanner = Scanner(device_keys={address.lower(): key}, indent=2)
    print(f"Starte BLE-Scan für Adresse {address}. Schlüssel wird nicht ausgegeben.", flush=True)
    print("Dekodierte victron-ble Messdaten erscheinen unten als JSON.", flush=True)
    await scanner.start()
    started = time.monotonic()
    try:
        if duration > 0:
            await asyncio.sleep(duration)
        else:
            while True:
                await asyncio.sleep(3600)
    finally:
        await scanner.stop()
        elapsed = time.monotonic() - started
        print(f"BLE-Scan nach {elapsed:.1f} Sekunden beendet.", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Victron SmartSolar BLE-Test; gibt dekodierte Anzeigen auf stdout aus."
    )
    parser.add_argument("charger", help="Name eines <Lader>-Eintrags aus Settings.xml")
    parser.add_argument(
        "--settings",
        default="Settings.xml",
        help="Pfad zur Settings.xml (Standard: ./Settings.xml)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=60,
        help="Scan-Dauer in Sekunden; 0 scannt bis Strg+C (Standard: 60)",
    )
    args = parser.parse_args()
    if args.duration < 0:
        parser.error("--duration darf nicht negativ sein")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    try:
        address, key = load_charger(args.charger, args.settings)
        asyncio.run(scan(address, key, args.duration))
    except KeyboardInterrupt:
        print("Scan durch Benutzer beendet.", flush=True)
    except Exception as error:
        print(f"Victron-BLE-Test fehlgeschlagen: {type(error).__name__}: {error}", flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
