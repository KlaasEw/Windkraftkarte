"""Einwohnerdaten laden und Verwaltungsgrenzen anreichern."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def normalize_ags(ags: str) -> str:
    ags = str(ags)
    return ags[:5] if len(ags) == 8 else ags


def _format_ags5(value: str | int | float) -> str:
    return str(int(float(value))).zfill(5)


def load_population_tables(csv_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = pd.read_csv(csv_path, dtype={"ags_5": str, "iso": str})
    kreise = data[data["region_type"] == "kreis"][["ags_5", "einwohner", "stichtag"]].copy()
    kreise["ags_5"] = kreise["ags_5"].map(_format_ags5)
    bundeslaender = data[data["region_type"] == "bundesland"][
        ["iso", "einwohner", "stichtag"]
    ].copy()
    return kreise, bundeslaender
