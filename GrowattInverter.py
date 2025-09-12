from IInverter import IInverter
from pymodbus.client import ModbusSerialClient
from MyLogging import Logging

class SPF6000Inverter(IInverter):
    """
    Implementation for Growatt SPF 6000 ES Plus
    """
    logger : Logging
    def __init__(self, logger : Logging, port="/dev/ttyUSB0", baudrate=9600, unit=1):
        self.logger = logger
        self.client = ModbusSerialClient(
            port=port,
            framer="rtu",
            baudrate=baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=2,
        )
        self.unit = unit

    def read_register(self, addr, count=1):
        """Hilfsfunktion zum Lesen von Input-Registers"""
        try:
            result = self.client.read_input_registers(address=addr, count=count, slave=self.unit)
        except:
            self.logger.Debug("Communication with Growatt Inverter failed ")
            return [0]
        if result.isError():
            return [0]
        return result.registers

    def read_32bit(self, addr):
        regs = self.read_register(addr, count=2)
        if len(regs) < 4:
            return 0
        if regs is None:
            return None
        return self.client.convert_from_registers(
            regs,
            data_type=self.client.DATATYPE.UINT32,
        )

    def getValues(self) -> IInverter.InverterValues:
        if not self.client.connect():
            raise ConnectionError("Inverter connection failed")

        try:
            # Solar Strings
            v1 = self.read_register(1)[0] / 10
            c1 = self.read_register(3)[0] / 10
            v2 = self.read_register(2)[0] / 10
            c2 = self.read_register(4)[0] / 10
            pv_total_power = self.read_32bit(5)

            # Aufteilen der Gesamtleistung proportional nach Stromstärken
            total_curr = c1 + c2
            if total_curr > 0:
                p1 = int(pv_total_power * (c1 / total_curr))
                p2 = int(pv_total_power * (c2 / total_curr))
            else:
                p1, p2 = 0, 0

            # Battery
            soc = self.read_register(15)[0]
            batt_v = self.read_register(16)[0] / 10
            batt_c = self.read_register(17)[0] / 10
            batt_power = int(batt_v * batt_c)

            # Inverter AC side
            inv_v = self.read_register(7)[0] / 10
            inv_c = self.read_register(8)[0] / 10
            inv_in_power = self.read_32bit(9)
            inv_out_power = self.read_32bit(11)  # Adresse anpassen falls anders

            return IInverter.InverterValues(
                VoltageSolar1=v1,
                CurrentSolar1=c1,
                PowerSolar1=p1,
                VoltageSolar2=v2,
                CurrentSolar2=c2,
                PowerSolar2=p2,
                SOC=soc,
                BatteryVoltage=batt_v,
                BatteryCurrent=batt_c,
                BatteryPower=batt_power,
                InverterInputVoltage=inv_v,
                InverterInputCurrent=inv_c,
                InverterInputPower=inv_in_power,
                InverterOutputPower=inv_out_power,
            )
        finally:
            self.client.close()