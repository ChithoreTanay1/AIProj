# DEIK.AI Challenge 2026 — Project Context

## Competition Overview
The Faculty of Informatics, University of Debrecen (with the Innovation Ecosystem Center) is running the **DEIK.AI Challenge 2026**, open to University of Debrecen students (individually or in teams of 2–4).

**Structure:**
- **AI Idea Competition** — innovative AI concepts solving real-world problems, deadline **September 4, 2026**. Prizes: HUF 200,000 / 150,000 / 100,000.
- **AI Demo Competition** — functional or advanced-stage AI projects, deadline **September 25, 2026**. Prizes: HUF 300,000 / 225,000 / 150,000 per category. Focus areas explicitly called out: urban environment monitoring, environmental/mobility data processing, and AI-based generation of PR/communication content.
- **AI Sprint final** — best demos invited to a two-day in-person sprint evaluating problem-solving, creativity, algorithmic thinking, and teamwork. Additional prizes.

**Registration/info:** https://inf.unideb.hu/en/deikai-challenge-2026

## Where We Landed: Project Direction

We're doing the **Demo Competition**, specifically the **urban/environmental monitoring** and **environmental/mobility data processing** focus areas (both explicitly named in the brief).

### Chosen Project: Mobility ↔ Pollution Correlation (using DKV transport data)

**Core question:** Does Debrecen's public transport network (routes, stop density, service frequency) measurably reduce air pollution and noise exposure in the areas it serves — and where would transit investment have the most environmental payoff?

**Why this was chosen over the alternatives** (land-use/historical-map diffing, biodiversity/green-corridor resilience — both still viable, deprioritized for now):
- It's the only idea built around the **DKV Debrecen Transport Ltd. dataset**, which is exclusive to this challenge (no public URL, not otherwise accessible) — using it seriously is a strong differentiator with judges.
- It directly hits the brief's separately-named **"environmental/mobility data processing"** focus area, not just general urban monitoring.
- It has a real, already-in-hand measurement backbone: the 16-station KER sensor network (air quality + noise, hourly/daily, May–June 2026) gives concrete pollution/noise readings to correlate against transit exposure per location.

**Approach:**
1. Geocode the 16 KER monitoring stations (already has lat/lon per station from `monitoring_2026-05-21_2026-06-19/`).
2. Load DKV transport data (stops, routes, trip frequency) — **schema not yet known, see Open Questions**.
3. Compute transit exposure per station: stop density and scheduled trip frequency within a radius of each sensor.
4. Correlate transit exposure against air quality (PM2.5, PM10, NO2, CO, O3, NOx) and noise (day/night dB) readings per station.
5. Fit a simple regression to quantify the relationship and rank stations/zones by "transit access vs. pollution burden."
6. Visualize as a station-ranked map + scatter plots + correlation summary — demo and PR material.

**Implementation:** `mobility-pollution-correlation/` project folder in this directory. See `mobility-pollution-correlation/instructions.md` for how to run it. The pipeline runs end-to-end on real data now: real KER monitoring readings, and (as of 2026-07-19) the real DKV export — "List of bus stops.xlsx" (687 platforms, lat/lon) joined with monthly "Summary stop statistics" (per-stop passenger frequency, used as a trips_per_day proxy). Both live in `mobility-pollution-correlation/data/dkv/`. `src/load_dkv.py` still keeps GTFS-style and generic CSV/XLSX parsing as fallbacks. Not wired in: the 236MB "Enclod archive data" raw GPS pings (left in the top-level `DKV databases/` folder, too large for git, not needed for the current stop-level exposure calc) and `Service Schedule.xlsx` / `Summary line statistics` (route/line-level, not yet parsed).

### Other data sources discovered (not yet all wired into the pipeline)
- **Cívis GIStory** (civisgistory.hu) — historical GIS maps/data of Debrecen, 19th century onward (Time Trail, Timeframes Comparator, Thematic Walks, 1870 Thematic Database). Held in reserve for the land-use-change alternative.
- **Zöld Őrszem** (zoldorszem.debrecen.hu/measurements) — Debrecen's own "Green Guardian" environmental monitoring platform; exact metrics not yet confirmed, worth checking as a possible second live-sensor source or cross-check against the KER network.
- **Debrecen Regulatory Plan** (envimap.hu) — current zoning/land-use map, orthophotos, digital terrain model. Informational only, not for official use.
- **Biodiversity**: OpenBioMaps Debrecen Bird Atlas (15k+ geocoded local bird records), MME/RTM colonial-bird monitoring (national grid, includes Debrecen), PADAPT (Pannonian plant traits, built by UDebrecen Ecology Dept), iNaturalist (global, filterable).
- **National reference/baseline data**: HungaroMet air quality network (legszennyezettseg.met.hu), OVF groundwater well network with 30-year baseline (geoportal.vizugy.hu/talajvizkutak), HungaroMet climate/weather archive (odp.met.hu), soil data hub incl. historical Kreybig soil maps (talaj-teradat.hu).

## Open Questions / Next Steps
- ~~Get the actual DKV dataset file and its schema~~ — done 2026-07-19. Real export loaded and pipeline verified end-to-end (16 stations, all with non-trivial stop_count/trips_per_day; correlations computing real r/p values, e.g. trips_per_day vs PM10 r=0.83, p<0.001 — worth digging into whether that's a genuine signal or confounded by station siting before it goes in the pitch).
- Consider parsing `Service Schedule.xlsx` for a true scheduled-trips-per-stop count, as a cross-check against the passenger-frequency proxy currently used for `trips_per_day`.
- Decide whether to pull in HungaroMet's national air-quality data as an external baseline/sanity-check for the KER station readings.
- Define concrete, measurable output claims for the pitch (e.g., "stations within Xm of Y+ daily transit trips show Z% lower NO2").
- Decide track: submit as Idea (concept-only, due Sept 4) vs. Demo (working prototype, due Sept 25) — currently building toward Demo.
- Draft pitch structure: problem statement → why AI → methodology → data sources → expected output → feasibility/timeline.

## Team Constraints (fill in once known)
- Team size / members:
- Technical skills available (CV/ML experience, GIS experience, etc.):
- Time budget before deadline:
- Access to compute / tools:
