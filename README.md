# Mobility ↔ Pollution Correlation

DEIK.AI Challenge 2026 project. Correlates DKV Debrecen public transport
access (stop density, boarding/alighting frequency) against air quality and
noise readings from the 16-station KER sensor network, to answer: does
transit access measurably reduce pollution/noise exposure, and where would
transit investment help most?

## Repository layout

```
mobility-pollution-correlation/    the pipeline (see its instructions.md)
monitoring_2026-05-21_2026-06-19/  raw KER sensor readings (air quality, noise), one folder per station
DKV databases/                     raw DKV transport export files, as supplied by the challenge organizers
```

## Running the pipeline

```bash
cd mobility-pollution-correlation
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 run_pipeline.py
```

Outputs (station summary, correlations, regressions, ML model performance,
charts, interactive map) are written to `mobility-pollution-correlation/outputs/`.

See `mobility-pollution-correlation/instructions.md` for setup details,
config options, and known limitations.
