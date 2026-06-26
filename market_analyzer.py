"""
Market Analyzer Agent
Scores market size, competition, and growth potential
"""


# Sector growth rates (annual %)
SECTOR_GROWTH = {
    "AI": 38, "Fintech": 18, "Healthcare": 12, "SaaS": 22,
    "B2B": 15, "Consumer": 10, "Marketplace": 14, "Climate": 28,
    "Deep Tech": 20, "Biotech": 16,
}

# Competition intensity by sector (lower = less competition = better score)
SECTOR_COMPETITION = {
    "AI": 75, "Fintech": 80, "Healthcare": 55, "SaaS": 85,
    "B2B": 65, "Consumer": 90, "Marketplace": 80, "Climate": 45,
    "Deep Tech": 40, "Biotech": 50,
}


class MarketAnalysis:
    def __init__(self, tam_score, growth_score, competition_score,
                 market_heat, total_score):
        self.tam_score = tam_score
        self.growth_score = growth_score
        self.competition_score = competition_score
        self.market_heat = market_heat
        self.total_score = total_score


class MarketAnalyzer:

    def analyze(self, startup) -> MarketAnalysis:
        tam_score         = self._score_tam(startup.tam_billions)
        growth_score      = self._score_growth(startup.sector)
        competition_score = self._score_competition(startup.sector)
        market_heat       = self._market_heat(growth_score, competition_score)
        total_score       = round(
            (tam_score * 0.4) + (growth_score * 0.35) + (competition_score * 0.25), 1
        )

        return MarketAnalysis(
            tam_score=tam_score,
            growth_score=growth_score,
            competition_score=competition_score,
            market_heat=market_heat,
            total_score=total_score,
        )

    def _score_tam(self, tam_billions: float) -> float:
        if tam_billions >= 500:  return 95
        if tam_billions >= 200:  return 85
        if tam_billions >= 100:  return 75
        if tam_billions >= 50:   return 65
        if tam_billions >= 20:   return 50
        return 35

    def _score_growth(self, sector: str) -> float:
        rate = SECTOR_GROWTH.get(sector, 15)
        if rate >= 35: return 95
        if rate >= 25: return 85
        if rate >= 18: return 75
        if rate >= 12: return 60
        return 45

    def _score_competition(self, sector: str) -> float:
        intensity = SECTOR_COMPETITION.get(sector, 70)
        # Lower competition = higher score
        return round(100 - intensity, 1)

    def _market_heat(self, growth_score, competition_score) -> str:
        avg = (growth_score + competition_score) / 2
        if avg >= 75: return "Hot"
        if avg >= 55: return "Warm"
        return "Cool"
