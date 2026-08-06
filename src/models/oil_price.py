from dataclasses import dataclass

@dataclass
class OilPrice:

    date: str

    product: str

    price_usd: float

    unit: str

    source: str