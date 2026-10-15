"""Generate a synthetic delivery dataset for the analysis.

The data is made up. It is seeded, so every run produces the same file.
To analyse real data instead, replace data/deliveries.csv with your own file
that has the same columns (see README.md).
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_SHIPMENTS = 5000

# Route name -> distance in km
ROUTES = {
    "Hyderabad-Bengaluru": 570,
    "Hyderabad-Chennai": 630,
    "Hyderabad-Mumbai": 710,
    "Hyderabad-Pune": 560,
    "Hyderabad-Delhi": 1550,
    "Hyderabad-Kolkata": 1500,
}
CARRIERS = ["SwiftLine", "RoadRunner", "BlueFreight"]
CARRIER_PROBS = [0.40, 0.35, 0.25]
WEATHER = ["Clear", "Rain", "Storm"]
WEATHER_PROBS = [0.70, 0.22, 0.08]

# Extra chance of delay added by each factor
CARRIER_RISK = {"SwiftLine": 0.00, "RoadRunner": 0.08, "BlueFreight": -0.03}
WEATHER_RISK = {"Clear": 0.00, "Rain": 0.15, "Storm": 0.35}


def build_dataset() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)

    order_date = pd.Timestamp("2025-01-01") + pd.to_timedelta(
        rng.integers(0, 365, N_SHIPMENTS), unit="D"
    )
    route = rng.choice(list(ROUTES), N_SHIPMENTS)
    distance_km = np.array([ROUTES[r] for r in route])
    carrier = rng.choice(CARRIERS, N_SHIPMENTS, p=CARRIER_PROBS)
    weather = rng.choice(WEATHER, N_SHIPMENTS, p=WEATHER_PROBS)
    weight_kg = np.round(rng.gamma(2.0, 6.0, N_SHIPMENTS) + 0.5, 1)

    # Promised delivery time grows with distance: about one day per 450 km, plus one day
    promised_days = np.ceil(distance_km / 450).astype(int) + 1

    # Probability that a shipment arrives late
    weekend_dispatch = (order_date.dayofweek >= 5).astype(float)
    p_delay = (
        0.12
        + np.array([CARRIER_RISK[c] for c in carrier])
        + np.array([WEATHER_RISK[w] for w in weather])
        + 0.00008 * distance_km
        + 0.004 * np.minimum(weight_kg, 30)
        + 0.08 * weekend_dispatch
    )
    p_delay = np.clip(p_delay, 0.02, 0.90)
    is_late = rng.random(N_SHIPMENTS) < p_delay

    # Late shipments arrive 1-3 days after the promise (up to 5 in a storm)
    max_extra = np.where(weather == "Storm", 6, 4)
    extra_days = rng.integers(1, max_extra)
    # On-time shipments arrive on the promised day or one day early
    early_days = rng.integers(0, 2, N_SHIPMENTS)
    actual_days = np.where(
        is_late, promised_days + extra_days, np.maximum(1, promised_days - early_days)
    )

    df = pd.DataFrame(
        {
            "shipment_id": [f"SHP-{i:05d}" for i in range(1, N_SHIPMENTS + 1)],
            "order_date": order_date.strftime("%Y-%m-%d"),
            "route": route,
            "carrier": carrier,
            "distance_km": distance_km,
            "weight_kg": weight_kg,
            "weather": weather,
            "promised_days": promised_days,
            "actual_days": actual_days,
        }
    )
    df["delivery_date"] = (
        pd.to_datetime(df["order_date"]) + pd.to_timedelta(df["actual_days"], unit="D")
    ).dt.strftime("%Y-%m-%d")
    df["delayed"] = (df["actual_days"] > df["promised_days"]).astype(int)
    return df


def main() -> None:
    out_path = Path(__file__).parent / "data" / "deliveries.csv"
    out_path.parent.mkdir(exist_ok=True)
    df = build_dataset()
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
