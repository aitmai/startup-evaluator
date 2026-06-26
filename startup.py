"""
Startup data model
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Startup:
    company_name: str
    stage: str
    sector: str
    founded_year: str
    team_size: int
    monthly_revenue: float
    monthly_burn: float
    cash_on_hand: float
    tam_billions: float
    prior_funding: str
    notable_investors: str
    website: str
    pitch_deck_path: str = ""
    description: str = ""
    yc_batch: str = ""

    @property
    def runway_months(self) -> float:
        if self.monthly_burn <= 0:
            return 999
        return round(self.cash_on_hand / self.monthly_burn, 1)

    @property
    def revenue_to_burn_ratio(self) -> float:
        if self.monthly_burn <= 0:
            return 0
        return round(self.monthly_revenue / self.monthly_burn, 2)

    @property
    def company_id(self) -> str:
        return self.company_name.upper().replace(" ", "-")[:12]
