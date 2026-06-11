"""Windräder Verwaltungsgebieten zuordnen und zählen."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from src.load_population import normalize_ags


def aggregate_turbines_by_region(
    turbines: gpd.GeoDataFrame,
    boundaries: gpd.GeoDataFrame,
    name_column: str,
) -> gpd.GeoDataFrame:
    joined = gpd.sjoin(
        turbines,
        boundaries[[name_column, "geometry"]],
        how="left",
        predicate="within",
    )
    joined = joined[~joined.index.duplicated(keep="first")]

    unmatched_mask = joined[name_column].isna()
    if unmatched_mask.any():
        unmatched_idx = joined.index[unmatched_mask]
        projected = boundaries.to_crs("EPSG:25832")
        projected["geometry"] = projected.geometry.buffer(50)
        projected = projected.to_crs(boundaries.crs)
        retry = gpd.sjoin(
            turbines.loc[unmatched_idx],
            projected[[name_column, "geometry"]],
            how="left",
            predicate="intersects",
        )
        retry = retry[~retry.index.duplicated(keep="first")]
        joined.loc[retry.index, name_column] = retry[name_column]

    counts = (
        joined.groupby(name_column, dropna=False)
        .size()
        .reset_index(name="anzahl")
    )
    counts = counts[counts[name_column].notna()]

    result = boundaries.merge(counts, on=name_column, how="left")
    result["anzahl"] = result["anzahl"].fillna(0).astype(int)
    return add_density(result)


def add_density(boundaries_with_counts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    result = boundaries_with_counts.copy()
    projected = result.to_crs("EPSG:25832")
    result["flaeche_km2"] = (projected.geometry.area / 1_000_000).round(1)
    result["dichte"] = (result["anzahl"] / result["flaeche_km2"]).round(2)
    return result


def add_population_metrics(
    boundaries_with_counts: gpd.GeoDataFrame,
    population: pd.DataFrame,
    join_column: str,
    population_join_column: str,
) -> gpd.GeoDataFrame:
    result = boundaries_with_counts.copy()
    result = result.merge(
        population,
        left_on=join_column,
        right_on=population_join_column,
        how="left",
    )
    result["einwohner"] = pd.to_numeric(result["einwohner"], errors="coerce")
    result["je_1000_ew"] = (
        (result["anzahl"] / result["einwohner"]) * 1000
    ).where(result["einwohner"] > 0).round(2)
    return result


def enrich_kreise_with_population(
    kreise_with_counts: gpd.GeoDataFrame,
    population_kreise: pd.DataFrame,
) -> gpd.GeoDataFrame:
    data = kreise_with_counts.copy()
    data["ags_norm"] = data["ags"].astype(str).map(normalize_ags).str.zfill(5)
    return add_population_metrics(data, population_kreise, "ags_norm", "ags_5")


def enrich_bundeslaender_with_population(
    bundeslaender_with_counts: gpd.GeoDataFrame,
    population_bundeslaender: pd.DataFrame,
) -> gpd.GeoDataFrame:
    return add_population_metrics(
        bundeslaender_with_counts,
        population_bundeslaender,
        "iso",
        "iso",
    )


def aggregate_turbines_by_kreis(
    turbines: gpd.GeoDataFrame,
    boundaries: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    return aggregate_turbines_by_region(turbines, boundaries, "kreis_name")


def aggregate_turbines_by_bundesland(
    turbines: gpd.GeoDataFrame,
    boundaries: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    return aggregate_turbines_by_region(turbines, boundaries, "bundesland_name")


def print_summary(
    boundaries_with_counts: gpd.GeoDataFrame,
    total_turbines: int,
    name_column: str,
    label: str,
) -> None:
    assigned = int(boundaries_with_counts["anzahl"].sum())
    print(f"\n=== {label} ===")
    print(f"Windräder gesamt:     {total_turbines}")
    print(f"Zugeordnete Zählung:  {assigned}")
    print(f"Differenz:            {total_turbines - assigned}")
    print()
    columns = [name_column, "anzahl", "flaeche_km2", "dichte"]
    if "einwohner" in boundaries_with_counts.columns:
        columns.extend(["einwohner", "je_1000_ew"])
    summary = (
        boundaries_with_counts[columns]
        .sort_values("anzahl", ascending=False)
        .reset_index(drop=True)
    )
    print(summary.to_string(index=False))


def print_density_summary(
    boundaries_with_counts: gpd.GeoDataFrame,
    name_column: str,
    label: str,
) -> None:
    print(f"\n=== {label} (Top 10 nach Dichte) ===")
    summary = (
        boundaries_with_counts[[name_column, "anzahl", "flaeche_km2", "dichte"]]
        .sort_values("dichte", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    print(summary.to_string(index=False))


def print_population_summary(
    boundaries_with_counts: gpd.GeoDataFrame,
    name_column: str,
    label: str,
) -> None:
    print(f"\n=== {label} (Top 10 nach Windrädern je 1.000 EW) ===")
    summary = (
        boundaries_with_counts[[name_column, "anzahl", "einwohner", "je_1000_ew"]]
        .dropna(subset=["je_1000_ew"])
        .sort_values("je_1000_ew", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    print(summary.to_string(index=False))
