# Quick Start Guide

Get up and running in 10 minutes.

---

## Prerequisites

- Python 3.10+
- A Google account
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

---

## 5-Step Setup

### Step 1 — Install dependencies

```bash
pip install anthropic gspread google-auth pymupdf reportlab rich requests python-dotenv
```

### Step 2 — Add your Anthropic API key

Rename `.env.example` to `.env` and fill it in:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Step 3 — Set up Google Sheets credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → create a project
2. Enable **Google Sheets API** and **Google Drive API**
3. Create a Service Account → download the JSON key → rename it `credentials.json` → put it in this folder
4. Create two Google Sheets: `Startups-To-Evaluate` and `Startup-Evaluator`
5. Share both sheets with the service account email in `credentials.json` (Editor access)

> Full instructions in README.md → Setup Instructions

### Step 4 — Pull startup data from YC

```bash
python scrape_yc.py
```

Writes 20 YC companies to your `Startups-To-Evaluate` sheet automatically.

### Step 5 — Run the evaluator

```bash
python evaluate_startup.py
```

---

## What You'll See

```
Analyzing: Stripe
  ✓ Market Score: 85 | Heat: Hot
  ✓ Team Score: 92 | Signal: Strong
  ✓ Financial Score: 88 | Runway: 75mo
  ✓ Pitch: No deck provided
  ✓ Grade: A | Score: 88.4 | Strong Buy
```

Results appear in your `Startup-Evaluator` Google Sheet.

---

## Common Commands

```bash
# Pull fresh YC data into input sheet
python scrape_yc.py

# Run full analysis
python evaluate_startup.py

# Check all files are present
ls -a
```

---

## Adding Pitch Decks (Optional)

1. Download a PDF pitch deck (try [slidebean.com/blog](https://slidebean.com/blog))
2. Drop it in the `pitch_decks/` folder
3. Add the full path in the `Pitch Deck Path` column of your sheet:
   ```
   C:\projects\python\startup-evaluator\pitch_decks\airbnb_pitch.pdf
   ```
4. Re-run `evaluate_startup.py`

Leave the column blank to skip pitch analysis.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `credentials.json not found` | Move file to project root folder |
| `SpreadsheetNotFound` | Check sheet name + share with service account |
| `Pitch deck file not found` | Use full path with backslashes, or leave blank |
| `ANTHROPIC_API_KEY not set` | Check `.env` file exists with correct key |
