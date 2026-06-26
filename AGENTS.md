# Agent Architecture

How each of the 5 agents works and what it scores.

---

## Overview

Each startup is analyzed by 5 agents in sequence. The Stage Engine combines all scores
using sector-specific weights and funding stage adjustments.

```
Startup Data
     │
     ├── MarketAnalyzer    → market score (TAM, growth, competition)
     ├── TeamEvaluator     → team score (investors, size, YC bonus)
     ├── FinancialAnalyzer → financial score (runway, burn, growth)
     ├── PitchAnalyzer     → pitch score (PDF parsing + Claude)
     └── StageEngine       → final grade + weighted overall score + Claude rationale
```

---

## Agent 1: MarketAnalyzer

**File:** `market_analyzer.py`

Scores the market opportunity.

| Sub-score | Weight | What it measures |
|---|---|---|
| TAM Score | 40% | Total addressable market size in billions |
| Growth Score | 35% | Annual sector growth rate |
| Competition Score | 25% | Inverse of competition intensity |

**TAM Scoring:**

| TAM | Score |
|---|---|
| $500B+ | 95 |
| $200B+ | 85 |
| $100B+ | 75 |
| $50B+ | 65 |
| $20B+ | 50 |
| Under $20B | 35 |

**Market Heat:**
- Hot: avg growth + competition score ≥ 75
- Warm: ≥ 55
- Cool: below 55

---

## Agent 2: TeamEvaluator

**File:** `team_evaluator.py`

Scores the founding team using available signals.

| Sub-score | Weight | What it measures |
|---|---|---|
| Investor Score | 50% | Tier-1 investor count in notable investors |
| Team Size Score | 50% | Appropriateness of team size for stage |
| YC Bonus | +10pts | All companies are YC-backed |

**Tier-1 Investors Recognized:**
Sequoia, Andreessen Horowitz (a16z), Kleiner Perkins, Benchmark, Accel,
Greylock, Founders Fund, General Catalyst, Lightspeed, Tiger, SoftBank, OpenAI Fund

**Team Signal:**
- Strong: score ≥ 85
- Solid: ≥ 70
- Mixed: ≥ 55
- Weak: below 55

---

## Agent 3: FinancialAnalyzer

**File:** `financial_analyzer.py`

Scores financial health and efficiency.

| Sub-score | Weight | What it measures |
|---|---|---|
| Runway Score | 35% | Months of cash remaining |
| Burn Efficiency | 40% | Revenue to burn ratio vs stage expectations |
| Growth Potential | 25% | Revenue vs stage benchmark |

**Runway Scoring:**

| Runway | Score |
|---|---|
| 24+ months | 95 |
| 18+ months | 85 |
| 12+ months | 70 |
| 6+ months | 50 |
| Under 6 months | 25 |

**Burn Efficiency** is stage-aware:
- Early stage (Pre-Seed, Seed, Series A): lower revenue/burn ratio is acceptable
- Late stage (Series B+): revenue should be approaching or exceeding burn

---

## Agent 4: PitchAnalyzer

**File:** `pitch_analyzer.py`

Parses PDF pitch decks and scores each section using Claude.

**Requires:** PyMuPDF (`pip install pymupdf`) and a PDF file path in the sheet

**Sections Scored:**

| Section | What Claude looks for |
|---|---|
| Problem | Is it clear and painful? |
| Solution | Is it differentiated and defensible? |
| Market Size | Is TAM credible and well-sourced? |
| Traction | Revenue, users, growth rate, customers |
| Team | Completeness, relevant experience |
| Business Model | Is monetization clear? |
| Ask | Is the funding amount reasonable for stage? |

**If no pitch deck:** pitch score is excluded from weighted average.
Remaining three scores are renormalized to sum to 100%.

---

## Agent 5: StageEngine

**File:** `stage_engine.py`

Combines all scores into a final investment grade using sector rubric weighting
and stage adjustments. Calls Claude to generate rationale, strengths, and risks.

### Sector Rubric Weights

| Sector | Market | Team | Financial | Pitch |
|---|---|---|---|---|
| SaaS | 25% | 25% | 30% | 20% |
| Biotech | 20% | 35% | 15% | 30% |
| Fintech | 25% | 25% | 30% | 20% |
| Consumer | 30% | 20% | 25% | 25% |
| Deep Tech | 20% | 35% | 15% | 30% |
| Marketplace | 30% | 20% | 25% | 25% |
| Climate | 25% | 30% | 20% | 25% |
| Healthcare | 20% | 35% | 20% | 25% |
| AI | 28% | 28% | 24% | 20% |
| B2B | 25% | 25% | 30% | 20% |
| Default | 25% | 25% | 25% | 25% |

### Stage Adjustments

Applied on top of sector weights:

| Stage | Market | Team | Financial | Pitch |
|---|---|---|---|---|
| Pre-Seed | +10% | +10% | -10% | -10% |
| Seed | +5% | +5% | -5% | -5% |
| Series A | 0 | 0 | 0 | 0 |
| Series B | -5% | -5% | +5% | +5% |
| Series C | -8% | -5% | +8% | +5% |
| Growth | -10% | -5% | +10% | +5% |
| Pre-IPO | -10% | -5% | +12% | +3% |
| IPO | -10% | -5% | +15% | 0 |

Weights are normalized after adjustment to always sum to 100%.

### Grading Scale

| Grade | Score Range | Recommendation |
|---|---|---|
| A | 88–100 | Strong Buy |
| B+ | 80–87 | Buy |
| B | 72–79 | Watch |
| C+ | 64–71 | Cautious Watch |
| C | 55–63 | Pass |
| D | 0–54 | Hard Pass |

### Claude Rationale

For each startup the Stage Engine calls `claude-haiku-4-5-20251001` to generate:
- 2-sentence investment thesis
- 3 key strengths
- 3 key risks

These are written to the `Startup-Evaluator` Google Sheet.
