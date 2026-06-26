"""
Pitch Deck Analyzer Agent
Parses PDF pitch decks and scores them using Claude
"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


class PitchAnalysis:
    def __init__(self, pitch_score, verdict, section_scores, has_deck):
        self.pitch_score = pitch_score
        self.verdict = verdict
        self.section_scores = section_scores
        self.has_deck = has_deck


class PitchAnalyzer:

    def analyze(self, startup) -> PitchAnalysis:
        if not startup.pitch_deck_path:
            return PitchAnalysis(
                pitch_score=None,
                verdict="No pitch deck provided",
                section_scores={},
                has_deck=False
            )

        path = Path(startup.pitch_deck_path)
        if not path.exists():
            return PitchAnalysis(
                pitch_score=None,
                verdict=f"Pitch deck file not found: {startup.pitch_deck_path}",
                section_scores={},
                has_deck=False
            )

        text = self._extract_pdf_text(path)
        if not text.strip():
            return PitchAnalysis(
                pitch_score=None,
                verdict="Could not extract text from pitch deck",
                section_scores={},
                has_deck=False
            )

        return self._score_with_claude(startup, text)

    def _extract_pdf_text(self, path: Path) -> str:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text[:8000]  # Cap at 8000 chars to stay within token limits
        except ImportError:
            return self._extract_pdf_fallback(path)
        except Exception as e:
            print(f"  PDF extraction error: {e}")
            return ""

    def _extract_pdf_fallback(self, path: Path) -> str:
        """Fallback if PyMuPDF not installed"""
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                return "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )[:8000]
        except Exception:
            return ""

    def _score_with_claude(self, startup, text: str) -> PitchAnalysis:
        prompt = f"""You are a venture capital analyst reviewing a startup pitch deck.

Company: {startup.company_name}
Stage: {startup.stage}
Sector: {startup.sector}

Pitch deck text:
{text}

Score this pitch deck and return ONLY valid JSON with no markdown, no backticks, no explanation:
{{
  "pitch_score": <0-100 overall score>,
  "verdict": "<one sentence overall verdict>",
  "sections": {{
    "problem": {{ "score": <0-100>, "comment": "<one sentence>" }},
    "solution": {{ "score": <0-100>, "comment": "<one sentence>" }},
    "market_size": {{ "score": <0-100>, "comment": "<one sentence>" }},
    "traction": {{ "score": <0-100>, "comment": "<one sentence>" }},
    "team": {{ "score": <0-100>, "comment": "<one sentence>" }},
    "business_model": {{ "score": <0-100>, "comment": "<one sentence>" }},
    "ask": {{ "score": <0-100>, "comment": "<one sentence>" }}
  }}
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
                    "max_tokens": 800,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )

            raw = response.json()["content"][0]["text"].strip()
            # Strip markdown fences if present
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())

            return PitchAnalysis(
                pitch_score=data.get("pitch_score", 50),
                verdict=data.get("verdict", "Analysis complete"),
                section_scores=data.get("sections", {}),
                has_deck=True
            )

        except Exception as e:
            print(f"  Claude pitch analysis error: {e}")
            return PitchAnalysis(
                pitch_score=50,
                verdict="Pitch deck parsed but scoring unavailable",
                section_scores={},
                has_deck=True
            )
