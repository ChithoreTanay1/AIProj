Real DKV Debrecen Transport Ltd. data files, copied from the challenge-supplied
"DKV databases" folder.

- `List of bus stops.xlsx` — 687 platforms, with a combined `Coordinates`
  column (`"lon, lat"`). Primary geometry source.
- `Summary stop statistics/<year>/<month>.xlsx` — monthly per-stop
  boarding/alighting counts (multi-row header, data starts at row 9). Joined
  onto the stop list by name to produce a `trips_per_day`-style exposure
  figure.
- `Service Schedule.xlsx`, `Summary line statistics/` — route/line-level
  schedule and stats, not currently parsed by the pipeline.

`src/load_dkv.py` reads these via `_load_bus_stops_export` /
`_load_stop_passenger_frequency`. GTFS-style and generic-table parsing are
kept as fallbacks (`_load_gtfs_style`, `_load_generic_table`) in case DKV
ever ships a different export shape — the rest of the pipeline (geo_utils,
correlate, visualize) doesn't care how the stops got loaded, only that it
ends up with a DataFrame of `stop_id, stop_lat, stop_lon` (+ optional
`trips_per_day`).

Not included here: the "Enclod archive data" raw per-second GPS pings
(~236MB across 17 monthly CSVs, `time,uuid,nick,lat,lng`). It's raw AVL
vehicle tracking data, not needed for the current stop-level exposure
calculation, and too large to check into git. It's still in the top-level
`DKV databases/Enclod archive data/` folder if a future direction needs it
(e.g. actual route-density heatmaps instead of scheduled/summary stats).
