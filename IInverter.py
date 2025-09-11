from abc import ABC, abstractmethod
from dataclasses import dataclass
import json

class IInverter(ABC):

    @dataclass
    class InverterValues:
        #Solar String Values
        VoltageSolar1 : float
        CurrentSolar1 : float
        PowerSolar1 : int
        VoltageSolar2 : float
        CurrentSolar2 : float
        PowerSolar2 : float

        #Battery values
        SOC : int
        BatteryVoltage : float
        BatteryCurrent : float
        BatteryPower : int

        #Inverter Values
        InverterInputVoltage: float
        InverterInputCurrent : float
        InverterInputPower : int
        InverterOutputPower : int

        def toString(self):
            return json.dumps({
                # Solar String Values
                "VoltageSolar1": self.VoltageSolar1,
                "CurrentSolar1": self.CurrentSolar1,
                "PowerSolar1": self.PowerSolar1,
                "VoltageSolar2": self.VoltageSolar2,
                "CurrentSolar2": self.CurrentSolar2,
                "PowerSolar2": self.PowerSolar2,

                # Battery values
                "SOC": self.SOC,
                "BatteryVoltage": self.BatteryVoltage,
                "BatteryCurrent": self.BatteryCurrent,
                "BatteryPower": self.BatteryPower,

                # Inverter Values
                "InverterInputVoltage": self.InverterInputVoltage,
                "InverterInputCurrent": self.InverterInputCurrent,
                "InverterInputPower": self.InverterInputPower,
                "InverterOutputPower": self.InverterOutputPower
            })

    @abstractmethod
    def getValues(self) -> "IInverter.InverterValues":
        raise NotImplementedError
