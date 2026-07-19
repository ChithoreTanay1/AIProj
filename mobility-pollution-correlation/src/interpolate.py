"""Inverse-distance weighting: turn 16 point sensor readings into a
continuous pollution surface over the city, instead of just colored dots
on a map.

Went with IDW over kriging. Kriging needs a variogram fit, and with only
~16 unevenly-spaced points that fit would be shaky without someone who
actually knows geostatistics tuning it. IDW skips that step entirely —
closer stations count for more, `power` controls how much more — and it's
easy to explain honestly if someone asks how the map's colors were made up.
"""
import numpy as np

EARTH_RADIUS_KM = 6371.0088


def idw_grid(
    lats: np.ndarray,
    lons: np.ndarray,
    values: np.ndarray,
    grid_size: int = 100,
    power: float = 2.0,
    padding_km: float = 1.5,
):
    """IDW-interpolate `values` at (lats, lons) onto a regular grid.

    Returns (grid_lats, grid_lons, grid_values): grid_lats/grid_lons are
    1-D arrays (south->north, west->east), grid_values is
    (grid_size, grid_size) with grid_values[i, j] at (grid_lats[i], grid_lons[j]).
    """
    lats = np.asarray(lats, dtype=float)
    lons = np.asarray(lons, dtype=float)
    values = np.asarray(values, dtype=float)

    pad_deg_lat = padding_km / 111.0
    pad_deg_lon = padding_km / (111.0 * np.cos(np.radians(lats.mean())))

    grid_lats = np.linspace(lats.min() - pad_deg_lat, lats.max() + pad_deg_lat, grid_size)
    grid_lons = np.linspace(lons.min() - pad_deg_lon, lons.max() + pad_deg_lon, grid_size)
    glon, glat = np.meshgrid(grid_lons, grid_lats)  # both (grid_size, grid_size)

    # haversine distance from every grid cell to every station, vectorized
    # -> shape (grid_size, grid_size, n_stations)
    phi1 = np.radians(glat)[..., None]
    phi2 = np.radians(lats)[None, None, :]
    dphi = phi2 - phi1
    dlambda = np.radians(lons)[None, None, :] - np.radians(glon)[..., None]
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    dist_km = 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))

    # avoid divide-by-zero when a grid cell lands exactly on a station
    dist_km = np.maximum(dist_km, 1e-4)
    weights = 1.0 / dist_km**power
    grid_values = (weights * values[None, None, :]).sum(axis=2) / weights.sum(axis=2)

    return grid_lats, grid_lons, grid_values
