from dataclasses import dataclass


@dataclass
class MeterPoint:
    contract_account: str
    meter_point: str
    description: str


@dataclass
class QuarterValue:
    timestamp: str
    value: float
    status: str
