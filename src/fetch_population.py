"""Lädt Einwohnerzahlen von Destatis (GENESIS INSPIRE, Stichtag 31.12.2024)."""

from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

DESTATIS_POPULATION_URL = (
    "https://genesis.destatis.de/genesisWS/inspire/pd/00/features/12411-0015.xml"
)
STICHTAG = "2024-12-31"
BL_TO_ISO = {
    "01": "DE-SH",
    "02": "DE-HH",
    "03": "DE-NI",
    "04": "DE-HB",
    "05": "DE-NW",
    "06": "DE-HE",
    "07": "DE-RP",
    "08": "DE-BW",
    "09": "DE-BY",
    "10": "DE-SL",
    "11": "DE-BE",
    "12": "DE-BB",
    "13": "DE-MV",
    "14": "DE-SN",
    "15": "DE-ST",
    "16": "DE-TH",
}


def _download_population_xml() -> ET.Element:
    response = requests.get(
        DESTATIS_POPULATION_URL,
        headers={"User-Agent": "Windkraftkarte/1.0 (local dev)"},
        timeout=180,
    )
    response.raise_for_status()
    return ET.fromstring(response.content)


def _parse_kreis_population(root: ET.Element) -> dict[str, int]:
    population_by_ags5: dict[str, int] = {}
    for member in root.iter():
        if not member.tag.endswith("StatisticalDataDistribution"):
            continue

        local_id = None
        value = None
        for child in member.iter():
            if child.tag.endswith("localId") and child.text:
                local_id = child.text
            if child.tag.endswith("value") and child.text:
                try:
                    value = int(float(child.text))
                except ValueError:
                    value = None

        if not local_id or value is None:
            continue

        parts = local_id.split("/")
        if len(parts) < 3 or parts[2] != STICHTAG:
            continue

        population_by_ags5[parts[1]] = value

    return population_by_ags5


def _bundesland_population(kreis_population: dict[str, int]) -> dict[str, int]:
    bl_totals: dict[str, int] = {}
    for ags5, count in kreis_population.items():
        bl_code = ags5[:2]
        iso = BL_TO_ISO.get(bl_code)
        if iso:
            bl_totals[iso] = bl_totals.get(iso, 0) + count
    return bl_totals


def fetch_population_csv(output_path: Path) -> None:
    root = _download_population_xml()
    kreis_population = _parse_kreis_population(root)
    bl_population = _bundesland_population(kreis_population)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["region_type", "ags_5", "iso", "einwohner", "stichtag"],
        )
        writer.writeheader()
        for ags5, count in sorted(kreis_population.items()):
            writer.writerow(
                {
                    "region_type": "kreis",
                    "ags_5": ags5,
                    "iso": "",
                    "einwohner": count,
                    "stichtag": STICHTAG,
                }
            )
        for iso, count in sorted(bl_population.items()):
            writer.writerow(
                {
                    "region_type": "bundesland",
                    "ags_5": "",
                    "iso": iso,
                    "einwohner": count,
                    "stichtag": STICHTAG,
                }
            )

    print(
        f"{len(kreis_population)} Kreise und {len(bl_population)} Bundesländer "
        f"(Stichtag {STICHTAG}) nach {output_path} geschrieben."
    )
