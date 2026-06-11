"""Lädt Windenergieanlagen von der Overpass API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import osm2geojson

from src.fetch_boundaries import _download_overpass

OVERPASS_QUERY_TURBINES = """
[out:json][timeout:180];
area["ISO3166-1"="DE"]["admin_level"="2"]->.searchArea;
nwr["generator:source"="wind"](area.searchArea);
out geom;
"""


def fetch_de_turbines(output_path: Path) -> None:
    osm_data = _download_overpass(OVERPASS_QUERY_TURBINES, timeout=180)
    geojson = osm2geojson.json2geojson(osm_data)
    geojson["generator"] = "Windkraftkarte (Overpass API)"
    geojson["copyright"] = (
        "The data included in this document is from www.openstreetmap.org. "
        "The data is made available under ODbL."
    )
    geojson["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)

    print(f"{len(geojson['features'])} Windräder nach {output_path} geschrieben.")
