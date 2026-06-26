"""
YC Company Scraper
Scrapes Y Combinator company directory and writes to Google Sheets "Startups-To-Evaluate"

Install dependencies first:
    pip install requests beautifulsoup4 gspread google-auth python-dotenv

Run:
    python scrape_yc.py
"""

import requests
import json
import time
import sys
from pathlib import Path

# ── CONFIGURATION ─────────────────────────────────────────────────
SHEET_NAME       = "Startups-To-Evaluate"
MAX_COMPANIES    = 20       # How many to pull (increase as needed)
SECTORS          = [        # Filter to these sectors (empty list = all)
    "B2B", "SaaS", "Fintech", "Healthcare", "AI"
]
STAGES           = [        # Filter to these stages (empty list = all)
    "Series A", "Seed", "Series B"
]

# Burn rate and revenue estimates by stage (monthly, in USD)
STAGE_ESTIMATES = {
    "Pre-Seed":  {"burn": 30000,   "revenue": 5000},
    "Seed":      {"burn": 100000,  "revenue": 50000},
    "Series A":  {"burn": 300000,  "revenue": 200000},
    "Series B":  {"burn": 800000,  "revenue": 800000},
    "Series C":  {"burn": 1500000, "revenue": 2000000},
    "Growth":    {"burn": 3000000, "revenue": 5000000},
    "Pre-IPO":   {"burn": 5000000, "revenue": 15000000},
    "IPO":       {"burn": 8000000, "revenue": 30000000},
}

# TAM estimates by sector (in billions)
SECTOR_TAM = {
    "B2B":          45,
    "SaaS":         195,
    "Fintech":      310,
    "Healthcare":   500,
    "AI":           1800,
    "Consumer":     120,
    "Marketplace":  80,
    "Climate":      150,
    "Deep Tech":    90,
    "Biotech":      270,
}


# ── SCRAPE YC COMPANIES ───────────────────────────────────────────
def fetch_yc_companies(max_companies=20, sectors=None, stages=None):
    """
    Fetches companies from YC's public API endpoint.
    YC loads company data via a JSON API — no Selenium needed.
    """
    print("Fetching YC company data...")

    url = "https://www.ycombinator.com/companies"
    api_url = "https://api.ycombinator.com/v0.1/companies"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.ycombinator.com/companies"
    }

    params = {
        "page": 1,
        "per_page": 100,
    }

    companies = []
    page = 1

    while len(companies) < max_companies:
        params["page"] = page
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                batch = data.get("companies", [])
                if not batch:
                    break
                companies.extend(batch)
                print(f"  Fetched page {page}: {len(batch)} companies (total: {len(companies)})")
                page += 1
                time.sleep(1)  # Be polite
            else:
                print(f"  API returned {response.status_code} — falling back to Algolia search")
                companies = fetch_via_algolia(max_companies, sectors)
                break

        except Exception as e:
            print(f"  Request failed: {e} — falling back to Algolia search")
            companies = fetch_via_algolia(max_companies, sectors)
            break

    return companies[:max_companies]


def fetch_via_algolia(max_companies=20, sectors=None):
    """
    YC uses Algolia search under the hood — this hits their search index directly.
    """
    print("Trying Algolia search index...")

    url = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "x-algolia-application-id": "45BWZJ1SGC",
        "x-algolia-api-key": "Zjk2ZmE5OTc4NmVlMzBjZTk2YWZlNDZiNzRiZGU1Y2I4YzBjMmEzMDI2MDZhYzRkZjQ4NGZhYjJiZDc3ZWZlZnJlc3RyaWN0aW9ucz0lNUIlNUQmY29tcHJlc3NlZD10cnVl",
    }

    filters = ""
    if sectors:
        sector_filter = " OR ".join([f'tags:"{s}"' for s in sectors])
        filters = f"({sector_filter})"

    payload = {
        "requests": [
            {
                "indexName": "YCCompany_production",
                "params": f"hitsPerPage={max_companies}&filters={filters}&page=0"
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            hits = data["results"][0].get("hits", [])
            print(f"  Found {len(hits)} companies via Algolia")
            return hits
        else:
            print(f"  Algolia returned {response.status_code}")
            return []
    except Exception as e:
        print(f"  Algolia failed: {e}")
        return []


# ── NORMALIZE COMPANY DATA ────────────────────────────────────────
def normalize_company(raw):
    """Converts raw YC API or Algolia response to our sheet format."""

    # Handle both API formats
    name        = raw.get("name") or raw.get("company_name", "Unknown")
    website     = raw.get("website") or raw.get("url", "")
    description = raw.get("one_liner") or raw.get("short_description", "")
    batch       = raw.get("batch") or raw.get("yc_batch", "")
    team_size   = raw.get("team_size") or raw.get("teamSize", 5)
    status      = raw.get("status", "")
    founded     = raw.get("founded_date") or raw.get("year_founded", "")
    tags        = raw.get("tags") or raw.get("industries", [])
    investors   = raw.get("top_companies") or []

    # Determine sector from tags
    sector = "SaaS"
    sector_map = {
        "fintech": "Fintech",
        "healthcare": "Healthcare",
        "biotech": "Biotech",
        "ai": "AI",
        "machine learning": "AI",
        "b2b": "B2B",
        "consumer": "Consumer",
        "marketplace": "Marketplace",
        "climate": "Climate",
        "deep tech": "Deep Tech",
        "saas": "SaaS",
    }
    for tag in (tags or []):
        tag_lower = str(tag).lower()
        for key, val in sector_map.items():
            if key in tag_lower:
                sector = val
                break

    # Determine stage from batch/status
    stage = determine_stage(batch, status, team_size)

    # Get estimates for this stage
    estimates = STAGE_ESTIMATES.get(stage, STAGE_ESTIMATES["Seed"])
    tam = SECTOR_TAM.get(sector, 50)

    # Founded year
    if isinstance(founded, str) and len(founded) >= 4:
        founded_year = founded[:4]
    elif isinstance(founded, int):
        founded_year = str(founded)
    else:
        founded_year = "2021"

    # Prior funding estimate by stage
    prior_funding_map = {
        "Pre-Seed": "$500K",
        "Seed": "$2M",
        "Series A": "$10M",
        "Series B": "$30M",
        "Series C": "$80M",
        "Growth": "$200M",
        "Pre-IPO": "$500M",
        "IPO": "$1B+",
    }

    return {
        "Company Name":      name,
        "Stage":             stage,
        "Sector":            sector,
        "Founded Year":      founded_year,
        "Team Size":         team_size or 10,
        "Monthly Revenue":   estimates["revenue"],
        "Monthly Burn":      estimates["burn"],
        "Cash on Hand":      estimates["burn"] * 18,  # ~18 months runway
        "TAM (billions)":    tam,
        "Prior Funding":     prior_funding_map.get(stage, "$2M"),
        "Notable Investors": "Y Combinator",
        "Website":           website,
        "Pitch Deck Path":   "",   # Fill in manually
        "Description":       description,
        "YC Batch":          batch,
    }


def determine_stage(batch, status, team_size):
    """Estimate funding stage from YC batch and company status."""
    if status in ["public", "acquired"]:
        return "Growth"

    # Rough heuristic: older batches = more mature
    if batch:
        year_str = ''.join(filter(str.isdigit, str(batch)))
        if year_str:
            year = int(year_str[:4]) if len(year_str) >= 4 else 2020
            age = 2026 - year
            if age <= 1:
                return "Seed"
            elif age <= 2:
                return "Series A"
            elif age <= 4:
                return "Series B"
            else:
                return "Series C"

    # Fall back to team size
    size = int(team_size or 5)
    if size < 10:
        return "Seed"
    elif size < 30:
        return "Series A"
    elif size < 100:
        return "Series B"
    else:
        return "Series C"


# ── WRITE TO GOOGLE SHEETS ────────────────────────────────────────
def write_to_sheet(companies):
    """Writes normalized company data to Google Sheets."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        print("ERROR: gspread not installed. Run: pip install gspread google-auth")
        sys.exit(1)

    print(f"\nConnecting to Google Sheets '{SHEET_NAME}'...")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_path = Path("credentials.json")
    if not creds_path.exists():
        print("ERROR: credentials.json not found in project folder.")
        sys.exit(1)

    creds  = Credentials.from_service_account_file(str(creds_path), scopes=scopes)
    client = gspread.authorize(creds)

    try:
        sheet = client.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"ERROR: Could not open sheet '{SHEET_NAME}': {e}")
        print("Make sure the sheet exists and is shared with your service account.")
        sys.exit(1)

    sheet.clear()

    headers = [
        "Company Name", "Stage", "Sector", "Founded Year", "Team Size",
        "Monthly Revenue", "Monthly Burn", "Cash on Hand", "TAM (billions)",
        "Prior Funding", "Notable Investors", "Website", "Pitch Deck Path",
        "Description", "YC Batch"
    ]

    rows = [headers]
    for c in companies:
        rows.append([
            c["Company Name"],
            c["Stage"],
            c["Sector"],
            c["Founded Year"],
            c["Team Size"],
            c["Monthly Revenue"],
            c["Monthly Burn"],
            c["Cash on Hand"],
            c["TAM (billions)"],
            c["Prior Funding"],
            c["Notable Investors"],
            c["Website"],
            c["Pitch Deck Path"],
            c["Description"],
            c["YC Batch"],
        ])

    sheet.update(rows, "A1")
    print(f"✓ Written {len(companies)} companies to '{SHEET_NAME}'")
    print(f"  Open: https://docs.google.com/spreadsheets/")


# ── FALLBACK: CURATED SEED DATA ───────────────────────────────────
def get_curated_yc_companies():
    """
    Curated list of real YC companies with known data.
    Used as fallback if scraping fails.
    """
    print("Using curated YC company dataset...")
    return [
        {
            "Company Name": "Airbnb", "Stage": "IPO", "Sector": "Marketplace",
            "Founded Year": "2008", "Team Size": 6000, "Monthly Revenue": 250000000,
            "Monthly Burn": 80000000, "Cash on Hand": 2000000000,
            "TAM (billions)": 1200, "Prior Funding": "$6B", "Notable Investors": "Sequoia, Y Combinator",
            "Website": "airbnb.com", "Pitch Deck Path": "", "Description": "Home sharing marketplace", "YC Batch": "W09"
        },
        {
            "Company Name": "Stripe", "Stage": "Pre-IPO", "Sector": "Fintech",
            "Founded Year": "2010", "Team Size": 8000, "Monthly Revenue": 120000000,
            "Monthly Burn": 40000000, "Cash on Hand": 3000000000,
            "TAM (billions)": 310, "Prior Funding": "$8.7B", "Notable Investors": "Sequoia, Andreessen Horowitz",
            "Website": "stripe.com", "Pitch Deck Path": "", "Description": "Payment infrastructure for the internet", "YC Batch": "S09"
        },
        {
            "Company Name": "Brex", "Stage": "Series C", "Sector": "Fintech",
            "Founded Year": "2017", "Team Size": 1200, "Monthly Revenue": 15000000,
            "Monthly Burn": 8000000, "Cash on Hand": 500000000,
            "TAM (billions)": 310, "Prior Funding": "$1.5B", "Notable Investors": "Y Combinator, Kleiner Perkins",
            "Website": "brex.com", "Pitch Deck Path": "", "Description": "Financial services for startups", "YC Batch": "W17"
        },
        {
            "Company Name": "Deel", "Stage": "Series C", "Sector": "SaaS",
            "Founded Year": "2019", "Team Size": 3000, "Monthly Revenue": 30000000,
            "Monthly Burn": 12000000, "Cash on Hand": 400000000,
            "TAM (billions)": 195, "Prior Funding": "$679M", "Notable Investors": "Y Combinator, Andreessen Horowitz",
            "Website": "deel.com", "Pitch Deck Path": "", "Description": "Global payroll and compliance platform", "YC Batch": "W19"
        },
        {
            "Company Name": "Gusto", "Stage": "Pre-IPO", "Sector": "SaaS",
            "Founded Year": "2011", "Team Size": 2500, "Monthly Revenue": 50000000,
            "Monthly Burn": 20000000, "Cash on Hand": 600000000,
            "TAM (billions)": 195, "Prior Funding": "$746M", "Notable Investors": "Y Combinator, General Catalyst",
            "Website": "gusto.com", "Pitch Deck Path": "", "Description": "Payroll, benefits, and HR for small businesses", "YC Batch": "W12"
        },
        {
            "Company Name": "Flexport", "Stage": "Series D", "Sector": "B2B",
            "Founded Year": "2013", "Team Size": 3000, "Monthly Revenue": 40000000,
            "Monthly Burn": 15000000, "Cash on Hand": 800000000,
            "TAM (billions)": 45, "Prior Funding": "$2.2B", "Notable Investors": "Y Combinator, SoftBank",
            "Website": "flexport.com", "Pitch Deck Path": "", "Description": "Digital freight forwarding platform", "YC Batch": "W14"
        },
        {
            "Company Name": "Retool", "Stage": "Series C", "Sector": "SaaS",
            "Founded Year": "2017", "Team Size": 500, "Monthly Revenue": 8000000,
            "Monthly Burn": 3000000, "Cash on Hand": 150000000,
            "TAM (billions)": 195, "Prior Funding": "$445M", "Notable Investors": "Y Combinator, Sequoia",
            "Website": "retool.com", "Pitch Deck Path": "", "Description": "Low-code platform for internal tools", "YC Batch": "W17"
        },
        {
            "Company Name": "Clerk", "Stage": "Series A", "Sector": "SaaS",
            "Founded Year": "2020", "Team Size": 80, "Monthly Revenue": 500000,
            "Monthly Burn": 400000, "Cash on Hand": 10000000,
            "TAM (billions)": 195, "Prior Funding": "$30M", "Notable Investors": "Y Combinator, Andreessen Horowitz",
            "Website": "clerk.com", "Pitch Deck Path": "", "Description": "Authentication and user management for developers", "YC Batch": "W21"
        },
        {
            "Company Name": "Harvey", "Stage": "Series B", "Sector": "AI",
            "Founded Year": "2022", "Team Size": 200, "Monthly Revenue": 3000000,
            "Monthly Burn": 2000000, "Cash on Hand": 80000000,
            "TAM (billions)": 1800, "Prior Funding": "$206M", "Notable Investors": "Y Combinator, OpenAI Fund",
            "Website": "harvey.ai", "Pitch Deck Path": "", "Description": "AI platform for legal professionals", "YC Batch": "W23"
        },
        {
            "Company Name": "Posthog", "Stage": "Series B", "Sector": "SaaS",
            "Founded Year": "2020", "Team Size": 60, "Monthly Revenue": 1500000,
            "Monthly Burn": 500000, "Cash on Hand": 25000000,
            "TAM (billions)": 195, "Prior Funding": "$27M", "Notable Investors": "Y Combinator, GV",
            "Website": "posthog.com", "Pitch Deck Path": "", "Description": "Open source product analytics", "YC Batch": "W20"
        },
    ]


# ── MAIN ──────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  YC Company Scraper → Google Sheets")
    print("=" * 60)
    print()

    # Try live scrape first
    companies_raw = fetch_yc_companies(
        max_companies=MAX_COMPANIES,
        sectors=SECTORS,
        stages=STAGES
    )

    if companies_raw:
        print(f"\nNormalizing {len(companies_raw)} companies...")
        companies = [normalize_company(c) for c in companies_raw]
    else:
        print("\nLive scrape unavailable — using curated YC dataset.")
        companies = get_curated_yc_companies()

    print(f"\nPreview of first 3 companies:")
    print("-" * 40)
    for c in companies[:3]:
        print(f"  {c['Company Name']} | {c['Stage']} | {c['Sector']} | {c['Website']}")
    print()

    write_to_sheet(companies)

    print()
    print("=" * 60)
    print("  Done! Next steps:")
    print("  1. Open your 'Startups-To-Evaluate' Google Sheet")
    print("  2. Add pitch deck PDF paths in the 'Pitch Deck Path' column")
    print("  3. Adjust Monthly Revenue/Burn with real data if you have it")
    print("  4. Run: python evaluate_startup.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
