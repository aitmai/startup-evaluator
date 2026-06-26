"""
Stage Engine — Final Investment Recommendation
Applies sector rubric weighting and generates Claude-powered rationale
"""
import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()


# ── SECTOR SCORING RUBRIC ─────────────────────────────────────────
SECTOR_WEIGHTS = {
    "SaaS":        {"market": 0.25, "team": 0.25, "financial": 0.30, "pitch": 0.20},
    "Biotech":     {"market": 0.20, "team": 0.35, "financial": 0.15, "pitch": 0.30},
    "Fintech":     {"market": 0.25, "team": 0.25, "financial": 0.30, "pitch": 0.20},
    "Consumer":    {"market": 0.30, "team": 0.20, "financial": 0.25, "pitch": 0.25},
    "Deep Tech":   {"market": 0.20, "team": 0.35, "financial": 0.15, "pitch": 0.30},
    "Marketplace": {"market": 0.30, "team": 0.20, "financial": 0.25, "pitch": 0.25},
    "Climate":     {"market": 0.25, "team": 0.30, "financial": 0.20, "pitch": 0.25},
    "Healthcare":  {"market": 0.20, "team": 0.35, "financial": 0.20, "pitch": 0.25},
    "AI":          {"market": 0.28, "team": 0.28, "financial": 0.24, "pitch": 0.20},
    "B2B":         {"market": 0.25, "team": 0.25, "financial": 0.30, "pitch": 0.20},
    "Default":     {"market": 0.25, "team": 0.25, "financial": 0.25, "pitch": 0.25},
}

# Stage adjustments — early stage = weight team/market more
STAGE_ADJUSTMENTS = {
    "Pre-Seed": {"market": +0.10, "team": +0.10, "financial": -0.10, "pitch": -0.10},
    "Seed":     {"market": +0.05, "team": +0.05, "financial": -0.05, "pitch": -0.05},
    "Series A": {"market": 0,     "team": 0,     "financial": 0,     "pitch": 0},
    "Series B": {"market": -0.05, "team": -0.05, "financial": +0.05, "pitch": +0.05},
    "Series C": {"market": -0.08, "team": -0.05, "financial": +0.08, "pitch": +0.05},
    "Growth":   {"market": -0.10, "team": -0.05, "financial": +0.10, "pitch": +0.05},
    "Pre-IPO":  {"market": -0.10, "team": -0.05, "financial": +0.12, "pitch": +0.03},
    "IPO":      {"market": -0.10, "team": -0.05, "financial": +0.15, "pitch": 0},
}


class InvestmentDecision:
    def __init__(self, investment_grade, overall_score, recommendation,
                 rationale, key_strengths, key_risks, weights_used):
        self.investment_grade = investment_grade
        self.overall_score = overall_score
        self.recommendation = recommendation
        self.rationale = rationale
        self.key_strengths = key_strengths
        self.key_risks = key_risks
        self.weights_used = weights_used


class StageEngine:

    def decide(self, startup, market, team, financial, pitch) -> InvestmentDecision:
        weights     = self._get_weights(startup.sector, startup.stage)
        overall     = self._weighted_score(market, team, financial, pitch, weights)
        grade       = self._grade(overall)
        rationale   = self._get_rationale(startup, market, team, financial, pitch, grade)

        return InvestmentDecision(
            investment_grade=grade,
            overall_score=overall,
            recommendation=self._recommendation(grade),
            rationale=rationale["rationale"],
            key_strengths=" | ".join(rationale["strengths"]),
            key_risks=" | ".join(rationale["risks"]),
            weights_used=weights,
        )

    def _get_weights(self, sector: str, stage: str) -> dict:
        base = SECTOR_WEIGHTS.get(sector, SECTOR_WEIGHTS["Default"]).copy()
        adj  = STAGE_ADJUSTMENTS.get(stage, {})

        for key in base:
            base[key] = max(0.05, base[key] + adj.get(key, 0))

        # Normalize to sum to 1.0
        total = sum(base.values())
        return {k: round(v / total, 3) for k, v in base.items()}

    def _weighted_score(self, market, team, financial, pitch, weights) -> float:
        if pitch.has_deck and pitch.pitch_score is not None:
            score = (
                market.total_score   * weights["market"]   +
                team.total_score     * weights["team"]     +
                financial.total_score * weights["financial"] +
                pitch.pitch_score    * weights["pitch"]
            )
        else:
            # Redistribute pitch weight proportionally across other three
            w_total = weights["market"] + weights["team"] + weights["financial"]
            score = (
                market.total_score    * (weights["market"]    / w_total) +
                team.total_score      * (weights["team"]      / w_total) +
                financial.total_score * (weights["financial"] / w_total)
            )
        return round(score, 1)

    def _grade(self, score: float) -> str:
        if score >= 88: return "A"
        if score >= 80: return "B+"
        if score >= 72: return "B"
        if score >= 64: return "C+"
        if score >= 55: return "C"
        return "D"

    def _recommendation(self, grade: str) -> str:
        return {
            "A":  "Strong Buy",
            "B+": "Buy",
            "B":  "Watch",
            "C+": "Cautious Watch",
            "C":  "Pass",
            "D":  "Hard Pass",
        }.get(grade, "Pass")

    def _get_rationale(self, startup, market, team, financial, pitch, grade) -> dict:
        prompt = f"""You are a venture capital analyst. Generate a brief investment assessment.

Company: {startup.company_name}
Stage: {startup.stage} | Sector: {startup.sector}
Grade: {grade}
Market Score: {market.total_score} | Team Score: {team.total_score}
Financial Score: {financial.total_score} | Runway: {financial.runway_months} months
Revenue/Burn: {financial.revenue_burn_ratio}
Pitch Score: {pitch.pitch_score if pitch.has_deck else "N/A"}
Investors: {startup.notable_investors}

Return ONLY valid JSON with no markdown or backticks:
{{
  "rationale": "<2 sentence investment thesis>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "risks": ["<risk 1>", "<risk 2>", "<risk 3>"]
}}"""

        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 400,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            raw = response.json()["content"][0]["text"].strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())

        except Exception as e:
            print(f"  Rationale generation error: {e}")
            return {
                "rationale": f"{startup.company_name} is a {startup.stage} {startup.sector} company with a {grade} grade.",
                "strengths": ["YC-backed", f"{market.market_heat} market", f"{financial.runway_months}mo runway"],
                "risks": ["Limited public data", "Stage risk", "Market competition"]
            }
