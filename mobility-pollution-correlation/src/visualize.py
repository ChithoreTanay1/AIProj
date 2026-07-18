"""Generate charts and a station map from the merged mobility/pollution data."""
import os

import matplotlib

matplotlib.use("Agg")  # headless-safe, no display needed
import matplotlib.pyplot as plt
import pandas as pd


def plot_pollutant_by_station(merged: pd.DataFrame, pollutant: str, outputs_dir: str) -> str:
    if pollutant not in merged.columns:
        return ""
    data = merged[["station_id", pollutant]].dropna().sort_values(pollutant, ascending=False)
    if data.empty:
        return ""

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(data["station_id"], data[pollutant], color="#3b6ea5")
    ax.set_ylabel(pollutant)
    ax.set_xlabel("Station")
    ax.set_title(f"Mean {pollutant} by monitoring station")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    path = os.path.join(outputs_dir, f"bar_{pollutant.replace('/', '-').replace(' ', '_')}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_transit_vs_pollutant(
    merged: pd.DataFrame, transit_col: str, pollutant: str, outputs_dir: str
) -> str:
    if transit_col not in merged.columns or pollutant not in merged.columns:
        return ""
    data = merged[[transit_col, pollutant, "station_id"]].dropna()
    if len(data) < 2:
        return ""

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(data[transit_col], data[pollutant], color="#c0504d", s=60)
    for _, row in data.iterrows():
        ax.annotate(row["station_id"].replace("DEB-", ""), (row[transit_col], row[pollutant]), fontsize=8)

    if data[transit_col].nunique() > 1:
        coeffs = pd.Series(data[pollutant].values).corr(pd.Series(data[transit_col].values))
        ax.set_title(f"{pollutant} vs {transit_col}  (r = {coeffs:.2f})")
    else:
        ax.set_title(f"{pollutant} vs {transit_col}")

    ax.set_xlabel(transit_col)
    ax.set_ylabel(pollutant)
    plt.tight_layout()

    fname = f"scatter_{transit_col}_{pollutant}".replace("/", "-").replace(" ", "_")
    path = os.path.join(outputs_dir, f"{fname}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def build_station_map(merged: pd.DataFrame, stops_df: pd.DataFrame, outputs_dir: str, color_by: str) -> str:
    """Interactive folium map: stations colored by `color_by` value, DKV stops
    overlaid as small markers if available. Falls back to a plain station
    map if folium isn't installed.
    """
    try:
        import folium
    except ImportError:
        print("[visualize] folium not installed, skipping interactive map (see requirements.txt)")
        return ""

    valid = merged.dropna(subset=["lat", "lon"])
    if valid.empty:
        return ""

    center = [valid["lat"].mean(), valid["lon"].mean()]
    fmap = folium.Map(location=center, zoom_start=12, tiles="cartodbpositron")

    if color_by in valid.columns and valid[color_by].notna().any():
        vmin, vmax = valid[color_by].min(), valid[color_by].max()
    else:
        vmin, vmax = None, None

    for _, row in valid.iterrows():
        value = row.get(color_by)
        if vmin is not None and vmax is not None and pd.notna(value) and vmax > vmin:
            frac = (value - vmin) / (vmax - vmin)
            color = f"#{int(255 * frac):02x}{int(255 * (1 - frac)):02x}40"
        else:
            color = "#3b6ea5"
        popup = f"{row['station_id']} — {row.get('name', '')}<br>{color_by}: {value}"
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=popup,
        ).add_to(fmap)

    if not stops_df.empty:
        for _, stop in stops_df.iterrows():
            folium.CircleMarker(
                location=[stop["stop_lat"], stop["stop_lon"]],
                radius=2,
                color="#555555",
                fill=True,
                fill_opacity=0.5,
            ).add_to(fmap)

    path = os.path.join(outputs_dir, "station_map.html")
    fmap.save(path)
    return path
