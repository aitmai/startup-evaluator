# AI-Powered Startup Investment Evaluator

A multi-agent Python CLI that analyzes startups from Pre-Seed to IPO using the Anthropic Claude API, Google Sheets, and PDF pitch deck parsing.


---

## What It Does

- Reads startup data from a Google Sheet (`Startups-To-Evaluate`)
- Runs 5 AI agents to score each startup across market, team, financials, and pitch deck
- Applies a **sector-specific scoring rubric** (SaaS weighted differently than Biotech, etc.)
- Adjusts weights by **funding stage** (early stage = team/market heavier; late stage = financials heavier)
- Parses **PDF pitch decks** with PyMuPDF and scores each section using Claude
- Writes results to a Google Sheet (`Startup-Evaluator`)
- Displays a rich CLI summary table and detailed report for the top-ranked startup

---

## Project Structure

```
startup-evaluator/
├── evaluate_startup.py      # Main script — run this
├── scrape_yc.py             # Scrapes YC company directory → Google Sheets
├── startup.py               # Startup data model
├── sheets_writer.py         # Google Sheets read/write
├── market_analyzer.py       # Agent 1: Market size, growth, competition
├── team_evaluator.py        # Agent 2: Team strength, investor quality
├── financial_analyzer.py    # Agent 3: Runway, burn efficiency, growth
├── pitch_analyzer.py        # Agent 4: PDF pitch deck parsing + Claude scoring
├── stage_engine.py          # Agent 5: Final grade + Claude rationale
├── pitch_decks/             # Drop PDF pitch decks here
├── credentials.json         # Google service account key (never push to GitHub)
├── .env                     # ANTHROPIC_API_KEY (never push to GitHub)
└── .gitignore
```

---

## Setup Instructions

### 1. Clone or Download the Project

```bash
cd C:\projects\python
git clone <your-repo-url> startup-evaluator
cd startup-evaluator
```

### 2. Install Dependencies

```bash
pip install anthropic gspread google-auth pymupdf reportlab rich requests beautifulsoup4 python-dotenv
```

### 3. Set Up Google Cloud Credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. `startup-evaluator`)
3. Enable these two APIs:
   - **APIs & Services → Library → Google Sheets API → Enable**
   - **APIs & Services → Library → Google Drive API → Enable**
4. Create a Service Account:
   - **APIs & Services → Credentials → Create Credentials → Service Account**
   - Name it anything, click through to finish
   - Click the service account → **Keys tab → Add Key → Create new key → JSON**
   - Rename the downloaded file to `credentials.json`
   - Move it to your project root folder
5. Copy the `client_email` from inside `credentials.json` — you'll need it in the next step

### 4. Create Google Sheets

Create two Google Sheets at [sheets.google.com](https://sheets.google.com):

| Sheet Name | Purpose |
|---|---|
| `Startups-To-Evaluate` | Input — startup data to analyze |
| `Startup-Evaluator` | Output — analysis results |

For **each sheet**:
- Click **Share**
- Paste your service account email (from `credentials.json`)
- Set permission to **Editor**
- Click **Send**

### 5. Set Up Environment Variables

Rename `.env.example` to `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Get your API key at [console.anthropic.com](https://console.anthropic.com)

---

## How to Run

### Step 1 — Populate Input Data from YC Directory

```bash
python scrape_yc.py
```

This scrapes Y Combinator's company directory and writes 20 companies to your `Startups-To-Evaluate` sheet. Falls back to a curated dataset of 10 real YC companies (Stripe, Airbnb, Harvey, Brex, etc.) if the live scrape is unavailable.

### Step 2 — (Optional) Add Pitch Decks

Download PDF pitch decks and drop them in the `pitch_decks/` folder:
- [Slidebean Pitch Deck Library](https://slidebean.com/blog/startups-pitch-deck)
- Google: `airbnb pitch deck PDF download`

Then update the `Pitch Deck Path` column in your sheet with the full Windows path:

```
C:\projects\python\startup-evaluator\pitch_decks\airbnb_pitch.pdf
```

Leave the column blank to skip pitch analysis for that company.

### Step 3 — Run the Evaluator

```bash
python evaluate_startup.py
```

### Step 4 — View Results

Open your `Startup-Evaluator` Google Sheet to see all results, or read the CLI output directly.

---

## Scoring System

### Investment Grades

| Grade | Score | Recommendation |
|---|---|---|
| A | 88–100 | Strong Buy |
| B+ | 80–87 | Buy |
| B | 72–79 | Watch |
| C+ | 64–71 | Cautious Watch |
| C | 55–63 | Pass |
| D | 0–54 | Hard Pass |

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

### Stage Adjustments

Early stage (Pre-Seed, Seed) → team and market weighted heavier
Late stage (Series B+) → financials weighted heavier

---

## Google Sheets Column Reference

### Input Sheet: `Startups-To-Evaluate`

| Column | Description | Example |
|---|---|---|
| Company Name | Startup name | Stripe |
| Stage | Funding stage | Series B |
| Sector | Industry | Fintech |
| Founded Year | Year founded | 2010 |
| Team Size | Number of employees | 8000 |
| Monthly Revenue | Monthly revenue in USD | 120000000 |
| Monthly Burn | Monthly spend in USD | 40000000 |
| Cash on Hand | Cash available in USD | 3000000000 |
| TAM (billions) | Total addressable market | 310 |
| Prior Funding | Total raised | $8.7B |
| Notable Investors | Key investors | Sequoia, a16z |
| Website | Company website | stripe.com |
| Pitch Deck Path | Full path to PDF | C:\...\stripe.pdf |

### Output Sheet: `Startup-Evaluator`

| Column | Description |
|---|---|
| Company | Startup name |
| Stage | Funding stage |
| Sector | Industry |
| Investment Grade | A / B+ / B / C+ / C / D |
| Overall Score | Weighted score out of 100 |
| Market Score | Market analysis score |
| Team Score | Team evaluation score |
| Financial Score | Financial analysis score |
| Pitch Score | Pitch deck score (or N/A) |
| Runway (months) | Months of cash remaining |
| Revenue/Burn | Revenue to burn ratio |
| Recommendation | Strong Buy / Buy / Watch / Pass |
| Pitch Verdict | One-sentence pitch assessment |
| Key Strengths | Top 3 strengths |
| Key Risks | Top 3 risks |

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.10+ | Core language |
| Anthropic Claude API | Investment rationale + pitch deck scoring |
| gspread | Google Sheets read/write |
| PyMuPDF (fitz) | PDF text extraction |
| rich | CLI tables and progress bars |
| requests | YC directory scraping |
| python-dotenv | Environment variable management |

---

## Security

Never push these files to GitHub:

```
credentials.json   # Google service account key
.env               # Anthropic API key
```

Both are already in `.gitignore`.

---

## Troubleshooting

**`FileNotFoundError: credentials.json`**
→ Make sure `credentials.json` is in the project root folder

**`SpreadsheetNotFound`**
→ Check sheet name matches exactly (case-sensitive) and service account has Editor access

**`Pitch deck file not found`**
→ Use full Windows path with backslashes: `C:\projects\python\startup-evaluator\pitch_decks\file.pdf`
→ Or leave the Pitch Deck Path column blank to skip

**`ANTHROPIC_API_KEY not set`**
→ Check your `.env` file exists and contains the key

**`DeprecationWarning: The order of arguments in worksheet.update() has changed`**
→ Already handled — values are passed first in `sheets_writer.py`

---

## Data Sources

- **Y Combinator Directory** — [ycombinator.com/companies](https://ycombinator.com/companies)
- **Crunchbase** (free tier) — company funding and investor data
- **Slidebean** — public pitch deck PDFs for testing
- **AngelList / Wellfound** — early stage startup profiles

---

## License

MIT
