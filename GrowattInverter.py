import logging

import requests
import time
from IInverter import IInverter
from pymodbus.client import ModbusSerialClient
from MyLogging import Logging
import traceback
import threading
import json


class SPF6000Inverter(IInverter):
    """
    Implementation for Growatt SPF 6000 ES Plus
    """
    logger : Logging
    inverterOfflineCounter : int
    _mode : str
    def __init__(self, logger : Logging, port="/dev/ttyUSB0", baudrate=9600, unit=1):
        self.logger = logger
        self.values = IInverter.InverterValues(
                VoltageSolar1=0,
                CurrentSolar1=0,
                PowerSolar1=0,
                VoltageSolar2=0,
                CurrentSolar2=0,
                PowerSolar2=0,
                SOC=0,
                BatteryVoltage=0,
                BatteryCurrent=0,
                BatteryPower=0,
                InverterOutputVoltage=0,
                InverterOutputPower=0,
                MainsPower=0,
            )
        self.client = ModbusSerialClient(
            port=port,
            framer="rtu",
            baudrate=baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=2,
        )
        self.client.connect()
        self.unit = unit
        self.inverterOfflineCounter = 0
        self._mode = "AUTO"
        try:
            self.__readValues()
        except:
            pass
        self.thread = threading.Thread(target=self.__threadFunc, daemon=True)
        self.thread.start()

    def __threadFunc(self):
        while True:
            try:
                self.__readValues()
            except:
                self.logger.Error(traceback.format_exc())
                self.logger.Info("Try reconnect to modbus")
                if not self.client.connect():
                    raise self.logger.Error("Failed to connect to modbus")
            time.sleep(10)

    def setMode(self, mode : str):
        self._mode = mode
        self.logger.Info(f"Set mode to {mode}")

    def mode(self):
        return self._mode

    def read_register(self, addr, count=1):
        if 0 != self.inverterOfflineCounter:
            return [0]
        """Hilfsfunktion zum Lesen von Input-Registers"""
        try:
            result = self.client.read_input_registers(address=addr, count=count, slave=self.unit)
        except:
            self.logger.Debug("Communication with Growatt Inverter failed ")
            self.inverterOfflineCounter = 10
            return [0]
        if result.isError():
            return [0]
        return result.registers

    def read_32bit(self, addr):
        regs = self.read_register(addr, count=2)
        if not regs or len(regs) < 2:
            return 0
        return self.client.convert_from_registers(
            regs,
            data_type=self.client.DATATYPE.UINT32,
        )
    def getValues(self):
        return self.values

    def __readValues(self) -> IInverter.InverterValues:
        #self.logger.Debug("".join(traceback.format_stack()))
        if 0 != self.inverterOfflineCounter:
            self.logger.Debug("Inverter timeout")
            self.inverterOfflineCounter -= 1
            return

        try:
            # Solar Strings
            v1 = self.read_register(1)[0] / 10
            c1 = self.read_register(7)[0] / 10
            v2 = self.read_register(2)[0] / 10
            c2 = self.read_register(8)[0] / 10
            pv_total_power = (v1 * c1) + (v2 * c2)

            # Aufteilen der Gesamtleistung proportional nach Stromstärken
            total_curr = c1 + c2
            if total_curr > 0:
                p1 = int(pv_total_power * (c1 / total_curr))
                p2 = int(pv_total_power * (c2 / total_curr))
            else:
                p1, p2 = 0, 0

            # Battery
            soc = self.read_register(18)[0]
            batt_v = self.read_register(17)[0] / 100
            batt_power = -self.read_32bit(73) / 10
            if 0 != batt_v:
                batt_c = batt_power / batt_v
            else:
                batt_c = 0

            # case batt charging
            if 0 == batt_power:
                batt_c = self.read_register(90)[0] /10
                batt_power = batt_c * batt_v



            # Inverter AC side
            inv_v = self.read_register(22)[0] / 10
            inv_load_percent = self.read_register(27)[0] / 10
            inv_power = 60 * inv_load_percent
            MainsPower = 0
            try:
                response = requests.get("http://wattwaechter/cm?cmnd=Status%208", timeout=10)
                data = response.json()
                #self.logger.Debug(f"response from Wattwaechter: {response.status_code} , Data: {json.dumps(data)}")
                if 200 != response.status_code:
                    self.logger.Error("No Power Information from Wattwaechter (Smartmeater)")
                    MainsPower = -1
                else:
                    MainsPower = data.get("StatusSNS", {}).get("MT631", {}).get("P", None)
            except Exception as e:
                self.logger.Error(traceback.format_exc())
            if not MainsPower:
                MainsPower = -1



            values =  IInverter.InverterValues(
                VoltageSolar1=v1,
                CurrentSolar1=c1,
                PowerSolar1=p1,
                VoltageSolar2=v2,
                CurrentSolar2=c2,
                PowerSolar2=p2,
                SOC=soc,
                BatteryVoltage=batt_v,
                BatteryCurrent=round(batt_c,1),
                BatteryPower=int(batt_power),
                InverterOutputVoltage=inv_v,
                InverterOutputPower=int(inv_power),
                MainsPower=int(MainsPower)
            )
            self.logger.Info("Read Inverter Data: " + values.toString())
            self.values = values

        except:
            self.logger.Error("Exception while reading inverter values: " + traceback.format_exc())

    def setPowerSave(self, on : bool):
        if not on:
            result = self.client.write_register(address=0, value=0x0000)
            print("set standby disable")
        else:
            print("set standby enable")
            result = self.client.write_register(address=0, value=0x0101)
