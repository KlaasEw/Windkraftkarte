#!/usr/bin/env python3
"""Pipeline: Grenzen laden → aggregieren → Deutschland-Karte erzeugen."""

from pathlib import Path

from src.aggregate import (
    aggregate_turbines_by_bundesland,
    aggregate_turbines_by_kreis,
    enrich_bundeslaender_with_population,
    enrich_kreise_with_population,
    print_density_summary,
    print_population_summary,
    print_summary,
)
from src.build_map import build_map
from src.fetch_boundaries import fetch_de_bundeslaender, fetch_de_kreise
from src.fetch_population import fetch_population_csv
from src.load_data import load_boundaries, load_turbines
from src.load_population import load_population_tables

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

TURBINES_PATH = DATA_DIR / "Windraeder_DE.geojson"
KREISE_PATH = DATA_DIR / "grenzen_de_kreise.geojson"
BUNDESLAENDER_PATH = DATA_DIR / "grenzen_de_bundeslaender.geojson"
POPULATION_PATH = DATA_DIR / "einwohner_destatis.csv"
MAP_PATH = OUTPUT_DIR / "windkarte.html"


def main() -> None:
    if not TURBINES_PATH.exists():
        raise FileNotFoundError(f"Windrad-Datei nicht gefunden: {TURBINES_PATH}")

    if not KREISE_PATH.exists():
        print("Kreisgrenzen werden von Overpass geladen …")
        fetch_de_kreise(KREISE_PATH)

    if not BUNDESLAENDER_PATH.exists():
        print("Bundeslandgrenzen werden von Overpass geladen …")
        fetch_de_bundeslaender(BUNDESLAENDER_PATH)

    if not POPULATION_PATH.exists():
        print("Einwohnerzahlen werden von Destatis geladen …")
        fetch_population_csv(POPULATION_PATH)

    turbines = load_turbines(TURBINES_PATH)
    kreise = load_boundaries(KREISE_PATH)
    bundeslaender = load_boundaries(BUNDESLAENDER_PATH)
    population_kreise, population_bundeslaender = load_population_tables(POPULATION_PATH)

    kreise_with_counts = enrich_kreise_with_population(
        aggregate_turbines_by_kreis(turbines, kreise),
        population_kreise,
    )
    bundeslaender_with_counts = enrich_bundeslaender_with_population(
        aggregate_turbines_by_bundesland(turbines, bundeslaender),
        population_bundeslaender,
    )

    print_summary(kreise_with_counts, len(turbines), "kreis_name", "Kreise")
    print_summary(
        bundeslaender_with_counts,
        len(turbines),
        "bundesland_name",
        "Bundesländer",
    )
    print_density_summary(kreise_with_counts, "kreis_name", "Kreise")
    print_density_summary(
        bundeslaender_with_counts,
        "bundesland_name",
        "Bundesländer",
    )
    print_population_summary(kreise_with_counts, "kreis_name", "Kreise")
    print_population_summary(
        bundeslaender_with_counts,
        "bundesland_name",
        "Bundesländer",
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    build_map(turbines, kreise_with_counts, bundeslaender_with_counts, str(MAP_PATH))
    print(f"\nKarte gespeichert: {MAP_PATH}")


if __name__ == "__main__":
    main()
