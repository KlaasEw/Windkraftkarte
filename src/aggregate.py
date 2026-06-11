"""Windanlagen Verwaltungsgebieten zuordnen und Kennzahlen berechnen."""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import pandas as pd

from src.load_population import normalize_ags


@dataclass(frozen=True)
class OffshoreSummary:
    anzahl: int
    leistung_mw: float


def _join_turbines_to_regions(
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

    return joined


def aggregate_turbines_by_region(
    turbines: gpd.GeoDataFrame,
    boundaries: gpd.GeoDataFrame,
    name_column: str,
    *,
    onshore_only: bool = False,
) -> gpd.GeoDataFrame:
    data = turbines
    if onshore_only and "typ" in turbines.columns:
        data = turbines[turbines["typ"] == "onshore"].copy()

    if data.empty:
        result = boundaries.copy()
        result["anzahl"] = 0
        result["leistung_mw"] = 0.0
        return add_area_metrics(result)

    joined = _join_turbines_to_regions(data, boundaries, name_column)
    if "leistung_mw" not in joined.columns:
        joined["leistung_mw"] = 0.0

    stats = (
        joined.groupby(name_column, dropna=False)
        .agg(anzahl=("leistung_mw", "size"), leistung_mw=("leistung_mw", "sum"))
        .reset_index()
    )
    stats = stats[stats[name_column].notna()]
    stats["leistung_mw"] = stats["leistung_mw"].round(1)

    result = boundaries.merge(stats, on=name_column, how="left")
    result["anzahl"] = result["anzahl"].fillna(0).astype(int)
    result["leistung_mw"] = result["leistung_mw"].fillna(0.0)
    return add_area_metrics(result)


def add_area_metrics(boundaries_with_counts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    result = boundaries_with_counts.copy()
    projected = result.to_crs("EPSG:25832")
    result["flaeche_km2"] = (projected.geometry.area / 1_000_000).round(1)
    result["dichte"] = (result["anzahl"] / result["flaeche_km2"]).round(2)
    result["leistung_dichte"] = (result["leistung_mw"] / result["flaeche_km2"]).round(2)
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
    result["mw_je_1000_ew"] = (
        (result["leistung_mw"] / result["einwohner"]) * 1000
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
    return aggregate_turbines_by_region(
        turbines, boundaries, "kreis_name", onshore_only=True
    )


def aggregate_turbines_by_bundesland(
    turbines: gpd.GeoDataFrame,
    boundaries: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    return aggregate_turbines_by_region(
        turbines, boundaries, "bundesland_name", onshore_only=True
    )


def compute_offshore_summary(turbines: gpd.GeoDataFrame) -> OffshoreSummary:
    if "typ" not in turbines.columns:
        return OffshoreSummary(anzahl=0, leistung_mw=0.0)
    offshore = turbines[turbines["typ"] == "offshore"]
    return OffshoreSummary(
        anzahl=int(len(offshore)),
        leistung_mw=round(float(offshore["leistung_mw"].sum()), 1),
    )


def print_summary(
    boundaries_with_counts: gpd.GeoDataFrame,
    total_turbines: int,
    name_column: str,
    label: str,
) -> None:
    assigned = int(boundaries_with_counts["anzahl"].sum())
    assigned_mw = float(boundaries_with_counts["leistung_mw"].sum())
    print(f"\n=== {label} ===")
    print(f"Windanlagen gesamt:   {total_turbines}")
    print(f"Zugeordnet (Anzahl):  {assigned}")
    print(f"Zugeordnet (MW):      {assigned_mw:.1f}")
    print(f"Differenz (Anzahl):   {total_turbines - assigned}")
    print()
    columns = [name_column, "anzahl", "leistung_mw", "flaeche_km2", "dichte", "leistung_dichte"]
    if "einwohner" in boundaries_with_counts.columns:
        columns.extend(["einwohner", "je_1000_ew", "mw_je_1000_ew"])
    summary = (
        boundaries_with_counts[columns]
        .sort_values("leistung_mw", ascending=False)
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
        boundaries_with_counts[
            [name_column, "anzahl", "leistung_mw", "flaeche_km2", "dichte", "leistung_dichte"]
        ]
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
    print(f"\n=== {label} (Top 10 nach MW je 1.000 EW) ===")
    summary = (
        boundaries_with_counts[
            [name_column, "anzahl", "leistung_mw", "einwohner", "je_1000_ew", "mw_je_1000_ew"]
        ]
        .dropna(subset=["mw_je_1000_ew"])
        .sort_values("mw_je_1000_ew", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    print(summary.to_string(index=False))


def print_offshore_summary(summary: OffshoreSummary) -> None:
    print("\n=== Offshore (Wind auf See, nicht Kreis-zugeordnet) ===")
    print(f"Anlagen:              {summary.anzahl}")
    print(f"Installierte Leistung: {summary.leistung_mw:.1f} MW")
