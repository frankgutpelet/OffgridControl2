from abc import ABC, abstractmethod
from dataclasses import dataclass
import json

class IInverter(ABC):

    @dataclass
    class InverterValues:
        # Solar String Values
        VoltageSolar1: float
        CurrentSolar1: float
        PowerSolar1: int
        VoltageSolar2: float
        CurrentSolar2: float
        PowerSolar2: float

        # Battery values
        SOC: int
        BatteryVoltage: float
        BatteryCurrent: float
        BatteryPower: int

        # Inverter Values
        InverterOutputVoltage: float
        InverterOutputPower: int

        def __post_init__(self):
            """Konvertiert Strings automatisch in float/int, falls nötig."""
            for field, field_type in self.__annotations__.items():
                value = getattr(self, field)
                if isinstance(value, str):  # Nur wenn Wert als String kam
                    if field_type == int:
                        setattr(self, field, int(value))
                    elif field_type == float:
                        setattr(self, field, float(value))

        def toJson(self):
            return self.__dict__

        def toString(self):
            """JSON-Export"""
            return json.dumps(self.__dict__)

        @classmethod
        def from_json(cls, data: dict):
            """Erstellt eine Instanz direkt aus JSON"""
            return cls(**data)

    @abstractmethod
    def getValues(self) -> "IInverter.InverterValues":
        raise NotImplementedError

    @abstractmethod
    def setPowerSave(self, on : bool):
        raise NotImplementedError