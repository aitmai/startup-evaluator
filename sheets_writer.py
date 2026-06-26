"""
Google Sheets writer for startup evaluator
"""
import gspread
from google.oauth2.service_account import Credentials


def get_sheet(sheet_name):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    return client.open(sheet_name).sheet1


def write_all_results(sheet, results):
    sheet.clear()
    headers = [
        "Company", "Stage", "Sector", "Investment Grade", "Overall Score",
        "Market Score", "Team Score", "Financial Score", "Pitch Score",
        "Runway (months)", "Revenue/Burn", "Recommendation",
        "Pitch Verdict", "Key Strengths", "Key Risks"
    ]
    rows = [headers]
    for r in results:
        rows.append([
            r["company"],
            r["stage"],
            r["sector"],
            r["investment_grade"],
            r["overall_score"],
            r["market_score"],
            r["team_score"],
            r["financial_score"],
            r["pitch_score"],
            r["runway_months"],
            r["revenue_burn_ratio"],
            r["recommendation"],
            r["pitch_verdict"],
            r["key_strengths"],
            r["key_risks"],
        ])
    sheet.update(rows, "A1")
    print(f"Written {len(results)} startups to Google Sheets")
