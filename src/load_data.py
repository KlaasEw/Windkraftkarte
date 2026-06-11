"""Daten laden und auf einheitliches CRS bringen."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

CRS_WGS84 = "EPSG:4326"


def _to_points(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    points = gdf[gdf.geometry.geom_type == "Point"].copy()
    non_points = gdf[gdf.geometry.geom_type != "Point"].copy()
    if not non_points.empty:
        projected = non_points.to_crs("EPSG:25832")
        projected["geometry"] = projected.geometry.centroid
        non_points["geometry"] = projected.to_crs(gdf.crs).geometry
        points = gpd.GeoDataFrame(
            pd.concat([points, non_points], ignore_index=True),
            crs=gdf.crs,
        )
    return points


def load_turbines(path: Path) -> gpd.GeoDataFrame:
    turbines = gpd.read_file(path)
    if turbines.crs is None:
        turbines = turbines.set_crs(CRS_WGS84)
    else:
        turbines = turbines.to_crs(CRS_WGS84)
    return _to_points(turbines)


def load_boundaries(path: Path) -> gpd.GeoDataFrame:
    boundaries = gpd.read_file(path)
    if boundaries.crs is None:
        boundaries = boundaries.set_crs(CRS_WGS84)
    else:
        boundaries = boundaries.to_crs(CRS_WGS84)
    boundaries["geometry"] = boundaries.geometry.simplify(
        tolerance=0.001, preserve_topology=True
    )
    return boundaries
