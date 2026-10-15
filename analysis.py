"""Analyse delivery delays: load the CSV into SQLite, query it, and draw charts.

Run generate_data.py first (or put your own deliveries.csv in data/), then:

    python analysis.py
"""

import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to files, no window needed
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "data" / "deliveries.csv"
DB_PATH = ROOT / "data" / "deliveries.db"
CHARTS_DIR = ROOT / "charts"
RESULTS_PATH = ROOT / "results.txt"

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Each query reports shipments, the share that arrived late, and how late on average.
# delayed is 1 when the shipment was late, so AVG(delayed) is the delay rate.
QUERIES = {
    "overall": """
        SELECT COUNT(*) AS shipments,
               ROUND(100.0 * AVG(delayed), 1) AS delay_pct,
               ROUND(AVG(actual_days - promised_days), 2) AS avg_days_vs_promise
        FROM deliveries
    """,
    "route": """
        SELECT route,
               COUNT(*) AS shipments,
               ROUND(100.0 * AVG(delayed), 1) AS delay_pct,
               ROUND(AVG(actual_days - promised_days), 2) AS avg_days_vs_promise
        FROM deliveries
        GROUP BY route
        ORDER BY delay_pct DESC
    """,
    "carrier": """
        SELECT carrier,
               COUNT(*) AS shipments,
               ROUND(100.0 * AVG(delayed), 1) AS delay_pct,
               ROUND(AVG(actual_days - promised_days), 2) AS avg_days_vs_promise
        FROM deliveries
        GROUP BY carrier
        ORDER BY delay_pct DESC
    """,
    "weather": """
        SELECT weather,
               COUNT(*) AS shipments,
               ROUND(100.0 * AVG(delayed), 1) AS delay_pct,
               ROUND(AVG(actual_days - promised_days), 2) AS avg_days_vs_promise
        FROM deliveries
        GROUP BY weather
        ORDER BY delay_pct DESC
    """,
    "weekday": """
        SELECT CAST(strftime('%w', order_date) AS INTEGER) AS dow_sun0,
               COUNT(*) AS shipments,
               ROUND(100.0 * AVG(delayed), 1) AS delay_pct
        FROM deliveries
        GROUP BY dow_sun0
    """,
    "weight_band": """
        SELECT CASE
                   WHEN weight_kg < 5  THEN '1: under 5 kg'
                   WHEN weight_kg < 15 THEN '2: 5-15 kg'
                   WHEN weight_kg < 30 THEN '3: 15-30 kg'
                   ELSE '4: 30 kg and over'
               END AS weight_band,
               COUNT(*) AS shipments,
               ROUND(100.0 * AVG(delayed), 1) AS delay_pct
        FROM deliveries
        GROUP BY weight_band
        ORDER BY weight_band
    """,
    "month": """
        SELECT strftime('%Y-%m', order_date) AS month,
               COUNT(*) AS shipments,
               ROUND(100.0 * AVG(delayed), 1) AS delay_pct
        FROM deliveries
        GROUP BY month
        ORDER BY month
    """,
}


def load_into_sqlite() -> None:
    """Read the CSV and write it to a SQLite table named deliveries."""
    df = pd.read_csv(CSV_PATH)
    with sqlite3.connect(DB_PATH) as con:
        df.to_sql("deliveries", con, if_exists="replace", index=False)


def run_queries() -> dict:
    """Run every query and return the results as DataFrames."""
    with sqlite3.connect(DB_PATH) as con:
        results = {name: pd.read_sql_query(sql, con) for name, sql in QUERIES.items()}

    # SQLite's %w gives 0 for Sunday; reorder so the week starts on Monday
    weekday = results["weekday"]
    weekday["weekday"] = weekday["dow_sun0"].map(lambda d: WEEKDAYS[(d - 1) % 7])
    weekday = weekday.set_index("weekday").loc[WEEKDAYS].reset_index()
    results["weekday"] = weekday[["weekday", "shipments", "delay_pct"]]
    return results


def bar_chart(df: pd.DataFrame, label_col: str, title: str, filename: str) -> None:
    """Draw a horizontal bar chart of delay rate and save it as a PNG."""
    fig, ax = plt.subplots(figsize=(7, 0.6 * len(df) + 1.6))
    bars = ax.barh(df[label_col], df["delay_pct"], color="#0b6b5d")
    ax.invert_yaxis()  # first row at the top
    ax.set_xlabel("Shipments delivered late (%)")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.bar_label(bars, fmt="%.1f%%", padding=4)
    ax.set_xlim(0, df["delay_pct"].max() * 1.18)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / filename, dpi=150)
    plt.close(fig)


def line_chart(df: pd.DataFrame, title: str, filename: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.plot(df["month"], df["delay_pct"], marker="o", color="#0b6b5d")
    ax.set_ylabel("Shipments delivered late (%)")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_ylim(0, df["delay_pct"].max() * 1.25)
    ax.tick_params(axis="x", rotation=45)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / filename, dpi=150)
    plt.close(fig)


def make_charts(results: dict) -> None:
    CHARTS_DIR.mkdir(exist_ok=True)
    bar_chart(results["route"], "route", "Delay rate by route", "delay_by_route.png")
    bar_chart(results["carrier"], "carrier", "Delay rate by carrier", "delay_by_carrier.png")
    bar_chart(results["weather"], "weather", "Delay rate by weather", "delay_by_weather.png")
    bar_chart(results["weekday"], "weekday", "Delay rate by order weekday", "delay_by_weekday.png")
    # Drop the "1: " sort prefix from the labels before drawing
    weight = results["weight_band"].copy()
    weight["weight_band"] = weight["weight_band"].str.replace(r"^\d: ", "", regex=True)
    bar_chart(weight, "weight_band", "Delay rate by package weight", "delay_by_weight.png")
    line_chart(results["month"], "Delay rate by month", "delay_by_month.png")


def write_summary(results: dict) -> None:
    lines = []
    for name, df in results.items():
        lines.append(f"== {name} ==")
        lines.append(df.to_string(index=False))
        lines.append("")
    text = "\n".join(lines)
    RESULTS_PATH.write_text(text)
    print(text)


def main() -> None:
    if not CSV_PATH.exists():
        raise SystemExit("data/deliveries.csv not found. Run generate_data.py first.")
    load_into_sqlite()
    results = run_queries()
    make_charts(results)
    write_summary(results)
    print(f"Charts saved to {CHARTS_DIR}")


if __name__ == "__main__":
    main()
