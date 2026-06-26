"""
Financial Analyzer Agent
Calculates runway, burn efficiency, and unit economics
"""


class FinancialMetrics:
    def __init__(self, runway_score, burn_efficiency_score, growth_score,
                 total_score, runway_months, revenue_burn_ratio):
        self.runway_score = runway_score
        self.burn_efficiency_score = burn_efficiency_score
        self.growth_score = growth_score
        self.total_score = total_score
        self.runway_months = runway_months
        self.revenue_burn_ratio = revenue_burn_ratio


class FinancialAnalyzer:

    def analyze(self, startup) -> FinancialMetrics:
        runway_months       = startup.runway_months
        revenue_burn_ratio  = startup.revenue_to_burn_ratio

        runway_score           = self._score_runway(runway_months)
        burn_efficiency_score  = self._score_burn_efficiency(revenue_burn_ratio, startup.stage)
        growth_score           = self._score_growth_potential(startup)
        total_score            = round(
            (runway_score * 0.35) + (burn_efficiency_score * 0.40) + (growth_score * 0.25), 1
        )

        return FinancialMetrics(
            runway_score=runway_score,
            burn_efficiency_score=burn_efficiency_score,
            growth_score=growth_score,
            total_score=total_score,
            runway_months=runway_months,
            revenue_burn_ratio=revenue_burn_ratio,
        )

    def _score_runway(self, months: float) -> float:
        if months >= 24:  return 95
        if months >= 18:  return 85
        if months >= 12:  return 70
        if months >= 6:   return 50
        return 25

    def _score_burn_efficiency(self, ratio: float, stage: str) -> float:
        # Early stage companies can burn more; later stage need efficiency
        early_stages = ["Pre-Seed", "Seed", "Series A"]
        if stage in early_stages:
            if ratio >= 0.5:  return 90
            if ratio >= 0.2:  return 75
            if ratio >= 0.05: return 60
            return 45
        else:
            if ratio >= 1.5:  return 95  # Revenue exceeds burn
            if ratio >= 1.0:  return 85
            if ratio >= 0.7:  return 70
            if ratio >= 0.4:  return 55
            return 35

    def _score_growth_potential(self, startup) -> float:
        # Score based on revenue relative to stage expectations
        stage_revenue_targets = {
            "Pre-Seed": 10000,
            "Seed": 100000,
            "Series A": 500000,
            "Series B": 2000000,
            "Series C": 8000000,
            "Growth": 20000000,
            "Pre-IPO": 50000000,
            "IPO": 100000000,
        }
        target = stage_revenue_targets.get(startup.stage, 500000)
        ratio = startup.monthly_revenue / target if target > 0 else 0

        if ratio >= 2.0:  return 95
        if ratio >= 1.0:  return 85
        if ratio >= 0.5:  return 70
        if ratio >= 0.2:  return 55
        return 40
