Real DKV Debrecen Transport Ltd. data, copied over from the challenge-supplied
"DKV databases" folder.

`List of bus stops.xlsx` is the main one — 687 platforms, coordinates packed
into a single `Coordinates` column as `"lon, lat"`. That's where the stop
geometry comes from. We don't have a real published schedule, so
`trips_per_day` is actually built from the monthly `Summary stop
statistics/<year>/<month>.xlsx` files instead — they give per-stop
boarding/alighting counts, joined onto the stop list by name. `Service
Schedule.xlsx` and `Summary line statistics/` are also in here but nothing
reads them yet.

`src/load_dkv.py` parses all this through `_load_bus_stops_export` and
`_load_stop_passenger_frequency`. The old GTFS-style and generic-table
parsers are still in there too, just as fallbacks in case DKV ever hands
over something in a different shape — everything downstream just needs a
DataFrame with `stop_id, stop_lat, stop_lon` (and `trips_per_day` if we
have it), so it doesn't care how that DataFrame got built.

One thing deliberately left out: the "Enclod archive data" raw GPS pings
(~236MB across 17 monthly CSVs, one row per second per bus). Not needed for
the current stop-level exposure calc, and way too big to put in git. Still
sitting in the top-level `DKV databases/Enclod archive data/` folder if we
ever want real route-density heatmaps instead of the summary stats.
