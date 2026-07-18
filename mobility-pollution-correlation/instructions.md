# Instructions — Mobility ↔ Pollution Correlation Pipeline

DEIK.AI Challenge 2026 project. Correlates DKV Debrecen Transport data
(stop density / trip frequency) against air quality and noise readings from
the 16-station KER sensor network, to answer: **does public transport
access measurably reduce pollution/noise exposure, and where would
transit investment help most?**

## 1. Requirements

- Python 3.10+ (tested on 3.12)
- The `monitoring_2026-05-21_2026-06-19/` folder must sit one level up from
  this project folder (i.e. as a sibling), which it already does if you
  haven't moved anything:
  ```
  AIProj/
    context.md
    monitoring_2026-05-21_2026-06-19/     <- real KER sensor data (already here)
    mobility-pollution-correlation/       <- this project
  ```

## 2. Setup

From inside `mobility-pollution-correlation/`:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Run it right now (monitoring-only mode)

You can run the pipeline immediately, even without DKV data — it will
compute and chart pollution/noise per station, and report the transit
correlation as "not yet available" rather than crashing:

```bash
python3 run_pipeline.py
```

Check the console output for `DKV data available: False` — that confirms
you're in monitoring-only mode. Outputs still get written to `outputs/`
(station summary, pollutant bar charts, station map) — everything except
the actual transit-vs-pollution correlation, which needs real DKV data.

## 4. Adding the real DKV data (the critical missing piece)

As of writing, **the actual DKV Debrecen Transport dataset file has not
been obtained** — only its existence was mentioned in the challenge brief
(exclusive to DEIK.AI Challenge 2026 participants, no public URL). Get
that file from the challenge organizers, then:

1. Drop the file(s) into `data/dkv/`.
2. The loader (`src/load_dkv.py`) auto-detects two shapes:
   - **GTFS-style**: `stops.txt` (+ optionally `routes.txt`, `trips.txt`,
     `stop_times.txt`) — the standard transit-data export format. If DKV
     hands you a GTFS zip, unzip it into `data/dkv/`.
   - **Generic CSV/XLSX**: any file with stop coordinates in columns whose
     names contain "lat" / "lon" / "lng".
3. If the real file's structure matches neither shape, open
   `src/load_dkv.py` and adjust `_load_gtfs_style` or `_load_generic_table`
   — everything downstream (`geo_utils.py`, `correlate.py`,
   `visualize.py`) only needs a DataFrame with `stop_id, stop_lat,
   stop_lon` (+ optional `trips_per_day`), so once that shape comes out of
   the loader, nothing else needs to change.
4. Re-run `python3 run_pipeline.py`. Console should now say
   `DKV data available: True` and `outputs/regressions.csv` +
   `outputs/correlations.csv` will contain real (non-NaN) numbers.

## 5. What gets generated in `outputs/`

| File | Contents |
|---|---|
| `station_summary.csv` | One row per KER station: name, lat/lon, transit exposure (stop_count, trips_per_day), mean pollutant/noise values |
| `correlations.csv` | Pearson r + p-value for every (transit metric × pollutant/noise) pair |
| `regressions.csv` | Simple linear regression (pollutant ~ transit metric): slope, intercept, r², p-value |
| `bar_<pollutant>.png` | Stations ranked by mean value of that pollutant/noise metric |
| `scatter_<transit_metric>_<pollutant>.png` | Transit exposure vs. pollutant scatter plot with per-station labels |
| `station_map.html` | Interactive map (folium) — stations colored by pollution level, DKV stops overlaid as small grey dots if available. Open directly in a browser. |

## 6. Adjusting parameters

Edit `config.yaml`:
- `radius_km` — how far around each sensor counts as "served" by a transit
  stop (default 0.5 km / ~6-7 min walk). Try 0.25 and 1.0 too to see how
  sensitive the correlation is to this choice — worth showing in the pitch.
- `pollutants` / `noise_metrics` — which metrics to analyze (must match the
  exact metric names in the KER xlsx files: PM2.5, PM10, NO2, NOx, CO, O3,
  LAEQ nappali, LAEQ éjszakai).

## 7. Project layout

```
mobility-pollution-correlation/
  config.yaml            # paths, radius, metric lists
  run_pipeline.py         # main entry point — run this
  requirements.txt
  src/
    load_monitoring.py    # reads KER air/noise xlsx -> tidy DataFrames
    load_dkv.py            # reads DKV transit data (schema-flexible, see above)
    geo_utils.py            # haversine distance + transit exposure per station
    correlate.py             # Pearson correlation + simple linear regression
    visualize.py              # bar charts, scatter plots, interactive map
  data/dkv/                  # <- put the real DKV export files here
  outputs/                    # <- generated charts/CSVs/map land here
```

## 8. Known limitations / honest caveats for the pitch

- Only 5 of the 16 KER stations have noise data (`LAEQ nappali`/`éjszakai`);
  the rest only have air quality + groundwater.
- The correlation is currently static (mean pollutant value vs. static
  transit exposure). If the real DKV data includes time-varying trip
  schedules or actual vehicle GPS/ridership, a stronger version of this
  analysis would correlate hourly pollution against hourly transit
  activity (e.g., rush-hour trip volume vs. rush-hour NO2) rather than just
  station-level averages — worth doing as a follow-up once the real data's
  shape is known.
- 16 stations is a small sample for correlation/regression — report
  p-values honestly in the pitch, don't overclaim significance.
