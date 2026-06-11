"""Lädt Verwaltungsgrenzen von der Overpass API."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import osm2geojson
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BUNDESLAND_CODES = {f"{code:02d}" for code in range(1, 17)}

OVERPASS_QUERY_KREISE = """
[out:json][timeout:180];
area["ISO3166-1"="DE"]["admin_level"="2"]->.region;
(
  relation["admin_level"="6"]["boundary"="administrative"](area.region);
);
out geom;
"""

OVERPASS_QUERY_BUNDESLAENDER = """
[out:json][timeout:90];
area["ISO3166-1"="DE"]["admin_level"="2"]->.region;
(
  relation["admin_level"="4"]["boundary"="administrative"](area.region);
);
out geom;
"""


def _download_overpass(query: str, timeout: int = 120) -> dict:
    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": "Windkraftkarte/1.0 (local dev)"},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "--max-time",
                str(timeout),
                "-X",
                "POST",
                OVERPASS_URL,
                "--data-urlencode",
                f"data={query.strip()}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)


def _is_german_kreis(tags: dict) -> bool:
    if tags.get("boundary") != "administrative":
        return False
    regional_key = str(
        tags.get("de:regionalschluessel")
        or tags.get("de:amtlicher_gemeindeschluessel")
        or ""
    )
    return regional_key.isdigit() and regional_key[:2] in BUNDESLAND_CODES


def _is_german_bundesland(tags: dict) -> bool:
    iso = str(tags.get("ISO3166-2", ""))
    return tags.get("boundary") == "administrative" and iso.startswith("DE-")


def _write_geojson(output_path: Path, geojson: dict, label: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"{len(geojson['features'])} {label} nach {output_path} geschrieben.")


def fetch_de_kreise(output_path: Path) -> None:
    osm_data = _download_overpass(OVERPASS_QUERY_KREISE, timeout=180)
    geojson = osm2geojson.json2geojson(osm_data)
    features = []
    for feature in geojson["features"]:
        props = feature.get("properties", {})
        tags = props.get("tags", props)
        if not _is_german_kreis(tags):
            continue
        regional_key = str(
            tags.get("de:regionalschluessel")
            or tags.get("de:amtlicher_gemeindeschluessel")
        )
        feature["properties"] = {
            "kreis_name": tags.get("name", "Unbekannt"),
            "ags": tags.get("de:amtlicher_gemeindeschluessel", regional_key),
        }
        features.append(feature)
    _write_geojson(output_path, {"type": "FeatureCollection", "features": features}, "Kreise")


def fetch_de_bundeslaender(output_path: Path) -> None:
    osm_data = _download_overpass(OVERPASS_QUERY_BUNDESLAENDER, timeout=120)
    geojson = osm2geojson.json2geojson(osm_data)
    features = []
    for feature in geojson["features"]:
        props = feature.get("properties", {})
        tags = props.get("tags", props)
        if not _is_german_bundesland(tags):
            continue
        feature["properties"] = {
            "bundesland_name": tags.get("name", "Unbekannt"),
            "iso": tags.get("ISO3166-2", ""),
        }
        features.append(feature)
    _write_geojson(
        output_path,
        {"type": "FeatureCollection", "features": features},
        "Bundesländer",
    )
