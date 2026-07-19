"""Generate charts and a station map from the merged mobility/pollution data."""
import os

import matplotlib

matplotlib.use("Agg")  # headless-safe, no display needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.interpolate import idw_grid


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


def plot_interpolated_surface(merged: pd.DataFrame, pollutant: str, outputs_dir: str) -> str:
    """Static IDW-interpolated pollution surface (filled contour) with
    station points overlaid, for the report/pitch deck."""
    valid = merged.dropna(subset=["lat", "lon", pollutant])
    if len(valid) < 3:
        return ""

    grid_lats, grid_lons, grid_values = idw_grid(
        valid["lat"].to_numpy(), valid["lon"].to_numpy(), valid[pollutant].to_numpy()
    )

    fig, ax = plt.subplots(figsize=(8, 7))
    contour = ax.contourf(grid_lons, grid_lats, grid_values, levels=20, cmap="YlOrRd")
    fig.colorbar(contour, ax=ax, label=pollutant)
    ax.scatter(valid["lon"], valid["lat"], c="black", s=20, zorder=3)
    for _, row in valid.iterrows():
        ax.annotate(row["station_id"].replace("DEB-", ""), (row["lon"], row["lat"]), fontsize=7, zorder=4)
    ax.set_title(f"IDW-interpolated {pollutant} surface ({len(valid)} stations)")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    plt.tight_layout()

    path = os.path.join(outputs_dir, f"surface_{pollutant.replace('/', '-').replace(' ', '_')}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _render_surface_raster(grid_values: np.ndarray, path: str, alpha: float = 0.6) -> None:
    """Render the IDW grid to a transparent PNG for folium's ImageOverlay.
    Grid row 0 is the south edge, but image row 0 is the top of the
    picture — flip it or the map ends up upside down.
    """
    cmap = matplotlib.colormaps["YlOrRd"]
    vmin, vmax = np.nanmin(grid_values), np.nanmax(grid_values)
    norm = (grid_values - vmin) / (vmax - vmin) if vmax > vmin else np.zeros_like(grid_values)
    rgba = cmap(norm)
    rgba[..., 3] = alpha
    plt.imsave(path, np.flipud(rgba))


def build_station_map(
    merged: pd.DataFrame,
    stops_df: pd.DataFrame,
    outputs_dir: str,
    color_by: str,
    surface_pollutant: str = None,
) -> str:
    """Interactive folium map: stations colored by `color_by` value, DKV stops
    overlaid as small markers if available, plus an IDW-interpolated
    pollution surface layer (toggleable) if `surface_pollutant` is given.
    Falls back to a plain station map if folium isn't installed.
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

    surface_pollutant = surface_pollutant if surface_pollutant and surface_pollutant in valid.columns else None
    surface_valid = valid.dropna(subset=[surface_pollutant]) if surface_pollutant else valid.iloc[0:0]
    if surface_pollutant and len(surface_valid) >= 3:
        grid_lats, grid_lons, grid_values = idw_grid(
            surface_valid["lat"].to_numpy(), surface_valid["lon"].to_numpy(), surface_valid[surface_pollutant].to_numpy()
        )
        raster_path = os.path.join(outputs_dir, f"_surface_raster_{surface_pollutant.replace('/', '-').replace(' ', '_')}.png")
        _render_surface_raster(grid_values, raster_path)
        folium.raster_layers.ImageOverlay(
            image=raster_path,
            bounds=[[grid_lats.min(), grid_lons.min()], [grid_lats.max(), grid_lons.max()]],
            opacity=1.0,  # transparency is already baked into the PNG's alpha channel
            name=f"{surface_pollutant} surface (IDW estimate)",
        ).add_to(fmap)

    if color_by in valid.columns and valid[color_by].notna().any():
        vmin, vmax = valid[color_by].min(), valid[color_by].max()
    else:
        vmin, vmax = None, None

    stations_layer = folium.FeatureGroup(name="Monitoring stations", show=True)
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
        ).add_to(stations_layer)
    stations_layer.add_to(fmap)

    if not stops_df.empty:
        stops_layer = folium.FeatureGroup(name="DKV bus stops", show=True)
        for _, stop in stops_df.iterrows():
            folium.CircleMarker(
                location=[stop["stop_lat"], stop["stop_lon"]],
                radius=2,
                color="#555555",
                fill=True,
                fill_opacity=0.5,
            ).add_to(stops_layer)
        stops_layer.add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)

    path = os.path.join(outputs_dir, "station_map.html")
    fmap.save(path)
    return path
