# Delivery Delay Analysis

A Python and SQL analysis of what makes shipments arrive late. It loads delivery records into SQLite, answers questions with SQL queries, and draws a chart for each one.

> **About the data:** the dataset in `data/deliveries.csv` is synthetic. `generate_data.py` creates 5,000 made-up shipments from Hyderabad with a fixed random seed. The patterns below come from rules built into that generator, so they show how the analysis works and are not findings about real carriers. To analyse real data, see [Using your own data](#using-your-own-data).

## Questions

1. What share of shipments arrive late, and by how many days?
2. Which routes, carriers, and weather conditions have the highest delay rate?
3. Do weekday of dispatch and package weight make a difference?
4. Does the delay rate change over the year?

## Results on the sample data

Overall, **33.7%** of the 5,000 shipments arrived later than promised, by 0.39 days on average compared with the promise (early deliveries pull this down).

| Factor | Highest delay rate | Lowest delay rate |
|---|---|---|
| Weather | Storm 61.0% | Clear 27.5% |
| Carrier | RoadRunner 41.1% | BlueFreight 28.0% |
| Route | Hyderabad-Kolkata 38.5% | Hyderabad-Bengaluru 29.9% |
| Order weekday | Sunday 38.9% (Saturday 37.2%) | Friday 30.5% |
| Package weight | 30 kg and over 36.4% | Under 5 kg 28.5% |

- Weather has the largest effect. Storm shipments are late more than twice as often as clear-weather ones.
- Orders placed on a weekend are late more often than those placed Monday to Friday.
- Long routes (Kolkata, Delhi) have higher delay rates than the shorter ones.
- Month to month the rate stays between about 30% and 40%, with no clear seasonal pattern.

All figures are in `results.txt`.

## Charts

| | |
|---|---|
| ![By weather](charts/delay_by_weather.png) | ![By carrier](charts/delay_by_carrier.png) |
| ![By route](charts/delay_by_route.png) | ![By weekday](charts/delay_by_weekday.png) |
| ![By weight](charts/delay_by_weight.png) | ![By month](charts/delay_by_month.png) |

## How to run

You need Python 3.10 or newer.

```bash
git clone https://github.com/YOUR-USERNAME/delivery-delay-analysis.git
cd delivery-delay-analysis

python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt

python generate_data.py          # creates data/deliveries.csv
python analysis.py               # builds the SQLite database, runs the queries, saves charts
```

## Project layout

```
delivery-delay-analysis/
├── generate_data.py   # creates the synthetic dataset
├── analysis.py        # SQL queries, charts, and the text summary
├── data/deliveries.csv
├── charts/            # PNG charts written by analysis.py
├── results.txt        # query results as text
└── requirements.txt
```

## How it works

1. `analysis.py` reads the CSV with pandas and writes it to a SQLite table called `deliveries`.
2. Each question is a SQL query that groups shipments by one factor and reports the delay rate, for example:

   ```sql
   SELECT carrier,
          COUNT(*) AS shipments,
          ROUND(100.0 * AVG(delayed), 1) AS delay_pct
   FROM deliveries
   GROUP BY carrier
   ORDER BY delay_pct DESC;
   ```

   `delayed` is 1 when a shipment arrived after the promised day, so its average is the delay rate.
3. The results are loaded back into pandas and drawn with matplotlib.

## Using your own data

Replace `data/deliveries.csv` with a file that has these columns, then run `python analysis.py`:

`shipment_id, order_date (YYYY-MM-DD), route, carrier, distance_km, weight_kg, weather, promised_days, actual_days, delivery_date, delayed (1 if late, else 0)`

If your dataset uses different names or lacks a column, rename the columns in the CSV or adjust the queries in `QUERIES` inside `analysis.py`.

## Limitations

- The sample data is synthetic, so the results illustrate the method and do not describe real delivery performance.
- The analysis looks at one factor at a time. A factor such as weight could look important only because heavier parcels travel on long routes, so a model that considers several factors together would be a good next step.

## Possible next steps

- Predict whether a shipment will be late with a simple model in scikit-learn.
- Add significance tests to check whether differences between groups are larger than chance.
- Build the charts into a small dashboard.
