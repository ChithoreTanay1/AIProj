Put the real DKV Debrecen Transport Ltd. data files here.

`src/load_dkv.py` auto-detects two formats:

1. **GTFS-style** (preferred if DKV provides it): `stops.txt`, `routes.txt`,
   `trips.txt`, `stop_times.txt` — standard files any transit agency using
   GTFS would export.
2. **Generic CSV/XLSX**: any file with columns identifiable as latitude/
   longitude (column names containing "lat" / "lon" or "lng"), and
   optionally a trip-count/frequency column.

If DKV's actual export doesn't match either shape, edit
`_load_gtfs_style` or `_load_generic_table` in `src/load_dkv.py` to parse
it — the rest of the pipeline (geo_utils, correlate, visualize) doesn't
care how the stops got loaded, only that it ends up with a DataFrame of
`stop_id, stop_lat, stop_lon` (+ optional `trips_per_day`).
