"""
AI-Powered Startup Investment Evaluator
Reads from Google Sheets "Startups-To-Evaluate"
Writes results to Google Sheets "Startup-Evaluator"
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from startup import Startup
from market_analyzer import MarketAnalyzer
from team_evaluator import TeamEvaluator
from financial_analyzer import FinancialAnalyzer
from pitch_analyzer import PitchAnalyzer
from stage_engine import StageEngine
from sheets_writer import get_sheet, write_all_results

console = Console()


# ── LOAD FROM GOOGLE SHEETS ───────────────────────────────────────
def load_startups_from_sheet():
    console.print("[bold]Loading startups from Google Sheets 'Startups-To-Evaluate'...[/bold]")
    sheet = get_sheet("Startups-To-Evaluate")
    rows  = sheet.get_all_records()

    if not rows:
        console.print("[bold red]No startups found in sheet.[/bold red]")
        sys.exit(1)

    startups = []
    for i, row in enumerate(rows, start=1):
        try:
            def clean(val, default=0):
                return float(str(val).replace(",", "").replace("$", "") or default)

            s = Startup(
                company_name      = str(row.get("Company Name", f"STARTUP-{i}")),
                stage             = str(row.get("Stage", "Seed")),
                sector            = str(row.get("Sector", "SaaS")),
                founded_year      = str(row.get("Founded Year", "2021")),
                team_size         = int(row.get("Team Size", 10) or 10),
                monthly_revenue   = clean(row.get("Monthly Revenue", 0)),
                monthly_burn      = clean(row.get("Monthly Burn", 100000)),
                cash_on_hand      = clean(row.get("Cash on Hand", 1000000)),
                tam_billions      = clean(row.get("TAM (billions)", 10)),
                prior_funding     = str(row.get("Prior Funding", "Unknown")),
                notable_investors = str(row.get("Notable Investors", "Y Combinator")),
                website           = str(row.get("Website", "")),
                pitch_deck_path   = str(row.get("Pitch Deck Path", "")),
                description       = str(row.get("Description", "")),
                yc_batch          = str(row.get("YC Batch", "")),
            )
            startups.append(s)
        except Exception as e:
            console.print(f"[yellow]Skipping row {i}: {e}[/yellow]")

    console.print(f"[green]✓ Loaded {len(startups)} startups[/green]\n")
    return startups


# ── ANALYZE ONE STARTUP ───────────────────────────────────────────
def analyze_startup(startup: Startup, agents: dict) -> dict:
    console.print(f"\n[bold yellow]Analyzing: {startup.company_name}[/bold yellow]")
    console.print(f"[dim]{startup.stage} | {startup.sector} | {startup.website}[/dim]\n")

    results = {}

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as p:
        task = p.add_task("[cyan]Market Analysis...", total=None)
        time.sleep(0.5)
        results["market"] = agents["market"].analyze(startup)
        p.update(task, completed=True)
    console.print(f"  ✓ Market Score: [green]{results['market'].total_score}[/green] | Heat: [yellow]{results['market'].market_heat}[/yellow]")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as p:
        task = p.add_task("[cyan]Team Evaluation...", total=None)
        time.sleep(0.5)
        results["team"] = agents["team"].evaluate(startup)
        p.update(task, completed=True)
    console.print(f"  ✓ Team Score: [green]{results['team'].total_score}[/green] | Signal: [yellow]{results['team'].team_signal}[/yellow]")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as p:
        task = p.add_task("[cyan]Financial Analysis...", total=None)
        time.sleep(0.5)
        results["financial"] = agents["financial"].analyze(startup)
        p.update(task, completed=True)
    console.print(f"  ✓ Financial Score: [green]{results['financial'].total_score}[/green] | Runway: [yellow]{results['financial'].runway_months}mo[/yellow]")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as p:
        task = p.add_task("[cyan]Pitch Deck Analysis...", total=None)
        results["pitch"] = agents["pitch"].analyze(startup)
        p.update(task, completed=True)
    if results["pitch"].has_deck:
        console.print(f"  ✓ Pitch Score: [green]{results['pitch'].pitch_score}[/green]")
    else:
        console.print(f"  ✓ Pitch: [dim]No deck provided[/dim]")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as p:
        task = p.add_task("[cyan]Generating Recommendation...", total=None)
        results["decision"] = agents["stage"].decide(
            startup,
            results["market"], results["team"],
            results["financial"], results["pitch"]
        )
        p.update(task, completed=True)

    decision = results["decision"]
    grade_color = "green" if decision.investment_grade in ["A", "B+", "B"] else \
                  "yellow" if decision.investment_grade in ["C+", "C"] else "red"
    console.print(f"  ✓ Grade: [bold {grade_color}]{decision.investment_grade}[/bold {grade_color}] | Score: [green]{decision.overall_score}[/green] | [bold yellow]{decision.recommendation}[/bold yellow]\n")

    results["startup"] = startup
    return results


# ── DISPLAY SUMMARY TABLE ─────────────────────────────────────────
def display_summary_table(all_results: list):
    console.print("\n" + "="*90)
    console.print("[bold cyan]STARTUP INVESTMENT ANALYSIS SUMMARY[/bold cyan]".center(90))
    console.print("="*90 + "\n")

    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Company",     style="cyan",        width=16)
    table.add_column("Stage",       style="white",       width=10)
    table.add_column("Sector",      style="white",       width=12)
    table.add_column("Grade",       justify="center",    width=7)
    table.add_column("Score",       justify="right",     width=7)
    table.add_column("Market",      justify="right",     width=8)
    table.add_column("Team",        justify="right",     width=7)
    table.add_column("Financial",   justify="right",     width=10)
    table.add_column("Runway",      justify="right",     width=8)
    table.add_column("Rec",         style="bold yellow", width=14)

    sorted_results = sorted(all_results, key=lambda x: x["decision"].overall_score, reverse=True)

    for r in sorted_results:
        s  = r["startup"]
        d  = r["decision"]
        f  = r["financial"]
        m  = r["market"]
        tm = r["team"]

        grade_style = "bold green" if d.investment_grade in ["A", "B+", "B"] else \
                      "bold yellow" if d.investment_grade in ["C+", "C"] else "bold red"

        table.add_row(
            s.company_name[:15],
            s.stage,
            s.sector,
            f"[{grade_style}]{d.investment_grade}[/{grade_style}]",
            str(d.overall_score),
            str(m.total_score),
            str(tm.total_score),
            str(f.total_score),
            f"{f.runway_months}mo",
            d.recommendation,
        )

    console.print(table)
    console.print()


# ── DISPLAY DETAILED REPORT ───────────────────────────────────────
def display_detailed_report(result: dict):
    s  = result["startup"]
    d  = result["decision"]
    f  = result["financial"]
    m  = result["market"]
    p  = result["pitch"]

    console.print("\n" + "="*90)
    console.print(f"[bold cyan]TOP INVESTMENT OPPORTUNITY: {s.company_name}[/bold cyan]".center(100))
    console.print("="*90 + "\n")

    details = Table(show_header=False, box=box.SIMPLE)
    details.add_column("Field", style="cyan bold", width=22)
    details.add_column("Value", style="white",     width=55)
    details.add_row("Company",    s.company_name)
    details.add_row("Stage",      s.stage)
    details.add_row("Sector",     s.sector)
    details.add_row("Founded",    s.founded_year)
    details.add_row("Team Size",  str(s.team_size))
    details.add_row("Website",    s.website)
    details.add_row("YC Batch",   s.yc_batch)
    details.add_row("Investors",  s.notable_investors)
    console.print(Panel(details, title="[bold]Company Details[/bold]", border_style="cyan"))

    metrics = Table(show_header=False, box=box.SIMPLE)
    metrics.add_column("Metric", style="cyan bold", width=22)
    metrics.add_column("Value",  style="green",     width=55)
    metrics.add_row("Investment Grade",  f"[bold]{d.investment_grade}[/bold]")
    metrics.add_row("Overall Score",     f"{d.overall_score}/100")
    metrics.add_row("Market Score",      f"{m.total_score}/100 ({m.market_heat})")
    metrics.add_row("Team Score",        f"{result['team'].total_score}/100 ({result['team'].team_signal})")
    metrics.add_row("Financial Score",   f"{f.total_score}/100")
    metrics.add_row("Runway",            f"{f.runway_months} months")
    metrics.add_row("Revenue/Burn",      f"{f.revenue_burn_ratio}x")
    if p.has_deck:
        metrics.add_row("Pitch Score",   f"{p.pitch_score}/100")
        metrics.add_row("Pitch Verdict", p.verdict)
    console.print(Panel(metrics, title="[bold]Investment Metrics[/bold]", border_style="green"))

    console.print("\n[bold green]Key Strengths:[/bold green]")
    for strength in d.key_strengths.split(" | "):
        console.print(f"  ✓ {strength}")

    console.print("\n[bold yellow]Key Risks:[/bold yellow]")
    for risk in d.key_risks.split(" | "):
        console.print(f"  ⚠ {risk}")

    console.print(f"\n[bold cyan]Recommendation:[/bold cyan] [bold yellow]{d.recommendation}[/bold yellow]")
    console.print(f"[dim]{d.rationale}[/dim]\n")


# ── BUILD SHEET ROW ───────────────────────────────────────────────
def build_sheet_row(result: dict) -> dict:
    s = result["startup"]
    d = result["decision"]
    f = result["financial"]
    m = result["market"]
    t = result["team"]
    p = result["pitch"]

    return {
        "company":           s.company_name,
        "stage":             s.stage,
        "sector":            s.sector,
        "investment_grade":  d.investment_grade,
        "overall_score":     d.overall_score,
        "market_score":      m.total_score,
        "team_score":        t.total_score,
        "financial_score":   f.total_score,
        "pitch_score":       p.pitch_score if p.has_deck else "N/A",
        "runway_months":     f.runway_months,
        "revenue_burn_ratio": f.revenue_burn_ratio,
        "recommendation":    d.recommendation,
        "pitch_verdict":     p.verdict,
        "key_strengths":     d.key_strengths,
        "key_risks":         d.key_risks,
    }


# ── MAIN ──────────────────────────────────────────────────────────
def main():
    console.print(Panel(
        "[bold cyan]AI-Powered Startup Investment Evaluator[/bold cyan]\n"
        "[dim]Multi-Agent System | Sector Rubric Weighting | Pitch Deck Analysis[/dim]",
        box=box.DOUBLE, border_style="cyan"
    ))
    console.print()

    # Initialize agents
    console.print("[bold]Initializing AI Agents...[/bold]")
    agents = {
        "market":    MarketAnalyzer(),
        "team":      TeamEvaluator(),
        "financial": FinancialAnalyzer(),
        "pitch":     PitchAnalyzer(),
        "stage":     StageEngine(),
    }
    console.print("[green]✓ All agents initialized[/green]\n")

    # Load startups from Google Sheets
    startups = load_startups_from_sheet()
    console.print(f"[bold]Analyzing {len(startups)} startups...[/bold]")

    # Analyze each startup
    all_results = []
    for startup in startups:
        result = analyze_startup(startup, agents)
        all_results.append(result)
        time.sleep(0.3)

    # Display results
    display_summary_table(all_results)
    top = max(all_results, key=lambda x: x["decision"].overall_score)
    display_detailed_report(top)

    # Write to Google Sheets
    try:
        sheet_rows = [build_sheet_row(r) for r in all_results]
        sheet = get_sheet("Startup-Evaluator")
        write_all_results(sheet, sheet_rows)
        console.print(f"[green]✓ Results written to 'Startup-Evaluator' Google Sheet[/green]")
    except Exception as e:
        console.print(f"[red]SHEETS ERROR: {e}[/red]")

    console.print("\n[bold green]Analysis Complete![/bold green]\n")


if __name__ == "__main__":
    main()
