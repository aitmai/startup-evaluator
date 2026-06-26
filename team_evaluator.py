"""
Team Evaluator Agent
Scores founding team strength based on available signals
"""


# Known strong investors signal team quality
TIER1_INVESTORS = [
    "sequoia", "andreessen", "a16z", "kleiner", "benchmark",
    "accel", "greylock", "founders fund", "general catalyst",
    "lightspeed", "tiger", "softbank", "openai", "y combinator"
]

# Stage-based team size expectations
EXPECTED_TEAM_SIZE = {
    "Pre-Seed": (1, 5),
    "Seed": (3, 15),
    "Series A": (10, 50),
    "Series B": (30, 150),
    "Series C": (100, 500),
    "Growth": (300, 2000),
    "Pre-IPO": (500, 5000),
    "IPO": (1000, 10000),
}


class TeamEvaluation:
    def __init__(self, investor_score, team_size_score, yc_bonus,
                 total_score, team_signal):
        self.investor_score = investor_score
        self.team_size_score = team_size_score
        self.yc_bonus = yc_bonus
        self.total_score = total_score
        self.team_signal = team_signal


class TeamEvaluator:

    def evaluate(self, startup) -> TeamEvaluation:
        investor_score   = self._score_investors(startup.notable_investors)
        team_size_score  = self._score_team_size(startup.stage, startup.team_size)
        yc_bonus         = 10  # All these are YC companies
        raw_score        = (investor_score * 0.5) + (team_size_score * 0.5) + yc_bonus
        total_score      = round(min(raw_score, 100), 1)
        team_signal      = self._team_signal(total_score)

        return TeamEvaluation(
            investor_score=investor_score,
            team_size_score=team_size_score,
            yc_bonus=yc_bonus,
            total_score=total_score,
            team_signal=team_signal,
        )

    def _score_investors(self, investors: str) -> float:
        if not investors:
            return 40
        investors_lower = investors.lower()
        tier1_count = sum(1 for inv in TIER1_INVESTORS if inv in investors_lower)
        if tier1_count >= 3:  return 95
        if tier1_count >= 2:  return 85
        if tier1_count >= 1:  return 75
        return 55

    def _score_team_size(self, stage: str, team_size: int) -> float:
        expected = EXPECTED_TEAM_SIZE.get(stage, (10, 100))
        min_size, max_size = expected
        if team_size < min_size:
            # Too small — may be understaffed
            return max(40, 60 - (min_size - team_size) * 2)
        if team_size > max_size * 2:
            # Possibly over-hired
            return 65
        if min_size <= team_size <= max_size:
            return 85
        return 75

    def _team_signal(self, score: float) -> str:
        if score >= 85: return "Strong"
        if score >= 70: return "Solid"
        if score >= 55: return "Mixed"
        return "Weak"
