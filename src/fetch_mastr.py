"""Lädt Windenergieanlagen aus dem Marktstammdatenregister (MaStR)."""

from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime, timezone
from io import TextIOWrapper
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point
from sqlalchemy import inspect

STATUS_IN_BETRIEB = "In Betrieb"
ZENODO_WIND_URL = (
    "https://zenodo.org/api/records/14843222/files/"
    "bnetza_mastr_wind_raw.csv.zip/content"
)
ZENODO_WIND_ZIP = "bnetza_mastr_wind_raw.csv.zip"
ZENODO_MASTR_STICHTAG = "2025-02-09"


def format_stichtag_de(iso_date: str) -> str:
    year, month, day = iso_date.split("-")
    return f"{day}.{month}.{year}"


def load_mastr_stichtag(geojson_path: Path) -> str:
    meta_path = geojson_path.with_suffix(".meta.json")
    if meta_path.exists():
        with meta_path.open(encoding="utf-8") as f:
            meta = json.load(f)
        stichtag = meta.get("mastr_stichtag")
        if stichtag:
            return stichtag
    return ZENODO_MASTR_STICHTAG


def _extract_mastr_stichtag(df: pd.DataFrame, fallback: str) -> str:
    for column in ("DatumDownload", "DatumDownload_1", "DatumDownload_2"):
        if column not in df.columns:
            continue
        dates = pd.to_datetime(df[column], errors="coerce").dropna()
        if not dates.empty:
            return dates.max().strftime("%Y-%m-%d")
    return fallback


def _configure_mastr_home(mastr_dir: Path) -> None:
    mastr_dir.mkdir(parents=True, exist_ok=True)
    os.environ["OUTPUT_PATH"] = str(mastr_dir.resolve())


def _wind_table_has_data(engine) -> bool:
    if "wind_extended" not in inspect(engine).get_table_names():
        return False
    count = pd.read_sql("SELECT COUNT(*) AS n FROM wind_extended", con=engine).iloc[0]["n"]
    return int(count) > 0


def _classify_typ(row: pd.Series) -> str:
    location_type = str(row.get("WindAnLandOderAufSee") or row.get("Lage") or "").strip()
    seelage_raw = row.get("Seelage")
    seelage = "" if pd.isna(seelage_raw) else str(seelage_raw).strip()
    bundesland = str(row.get("Bundesland") or "").strip()
    if seelage or "auf See" in location_type:
        return "offshore"
    if "an Land" in location_type:
        return "onshore"
    if "Wirtschaftszone" in bundesland:
        return "offshore"
    return "onshore"


def _prepare_wind_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["EinheitBetriebsstatus"] = data["EinheitBetriebsstatus"].astype(str).str.strip()
    data = data[data["EinheitBetriebsstatus"] == STATUS_IN_BETRIEB]

    data["Land"] = data["Land"].astype(str).str.strip()
    data = data[data["Land"].str.fullmatch("Deutschland", na=False)]

    data["typ"] = data.apply(_classify_typ, axis=1)

    if "Bruttoleistung_extended" in data.columns:
        data["leistung_kw"] = pd.to_numeric(
            data["Bruttoleistung"].fillna(data["Bruttoleistung_extended"]),
            errors="coerce",
        )
    else:
        data["leistung_kw"] = pd.to_numeric(data["Bruttoleistung"], errors="coerce")

    data["leistung_mw"] = (data["leistung_kw"] / 1000).round(3)
    data["Laengengrad"] = pd.to_numeric(data["Laengengrad"], errors="coerce")
    data["Breitengrad"] = pd.to_numeric(data["Breitengrad"], errors="coerce")

    data = data.dropna(subset=["Laengengrad", "Breitengrad", "leistung_mw"])
    return data[data["leistung_mw"] > 0]


def _download_zenodo_wind_csv(mastr_dir: Path) -> Path:
    zip_path = mastr_dir / ZENODO_WIND_ZIP
    if zip_path.exists():
        print(f"Zenodo-Winddaten vorhanden: {zip_path}")
        return zip_path

    print("Fallback: Wind-CSV von Zenodo (open-MaStR) wird geladen …")
    response = requests.get(ZENODO_WIND_URL, timeout=120)
    response.raise_for_status()
    zip_path.write_bytes(response.content)
    return zip_path


def _load_wind_from_zenodo(mastr_dir: Path) -> tuple[pd.DataFrame, str]:
    zip_path = _download_zenodo_wind_csv(mastr_dir)
    with zipfile.ZipFile(zip_path) as archive:
        csv_name = next(name for name in archive.namelist() if name.endswith(".csv"))
        with archive.open(csv_name) as raw_file:
            df = pd.read_csv(TextIOWrapper(raw_file, encoding="utf-8"), low_memory=False)

    if df.empty:
        raise RuntimeError("Keine Winddaten in der Zenodo-CSV gefunden.")
    prepared = _prepare_wind_dataframe(df)
    stichtag = _extract_mastr_stichtag(df, ZENODO_MASTR_STICHTAG)
    return prepared, stichtag


def _load_wind_from_bulk(mastr_dir: Path) -> tuple[pd.DataFrame, str]:
    _configure_mastr_home(mastr_dir)
    from open_mastr import Mastr

    db = Mastr()
    if not _wind_table_has_data(db.engine):
        print("MaStR-Winddaten werden heruntergeladen (Bulk, nur Wind) …")
        print("Hinweis: Der Gesamtdatenauszug ist groß (~3 GB) und liegt unter data/mastr/.")
        db.download(method="bulk", data=["wind"], bulk_cleansing=True)
    else:
        print("MaStR SQLite vorhanden — überspringe Bulk-Download.")

    df = pd.read_sql("SELECT * FROM wind_extended", con=db.engine)
    if df.empty:
        raise RuntimeError("Keine Winddaten in der MaStR-Datenbank gefunden.")
    stichtag = _extract_mastr_stichtag(
        df, datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    return _prepare_wind_dataframe(df), stichtag


def _mastr_wind_dataframe(mastr_dir: Path) -> tuple[pd.DataFrame, str]:
    mastr_dir.mkdir(parents=True, exist_ok=True)
    _configure_mastr_home(mastr_dir)

    from open_mastr import Mastr

    db = Mastr()
    if _wind_table_has_data(db.engine):
        df = pd.read_sql("SELECT * FROM wind_extended", con=db.engine)
        stichtag = _extract_mastr_stichtag(
            df, datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        return _prepare_wind_dataframe(df), stichtag

    zenodo_zip = mastr_dir / ZENODO_WIND_ZIP
    if zenodo_zip.exists():
        print("Keine lokale MaStR-SQLite mit Winddaten — nutze Zenodo-Wind-CSV.")
        return _load_wind_from_zenodo(mastr_dir)

    try:
        return _load_wind_from_bulk(mastr_dir)
    except Exception as exc:
        print(f"Bulk-Download fehlgeschlagen ({exc}).")
        return _load_wind_from_zenodo(mastr_dir)


def fetch_mastr_wind(output_path: Path, mastr_dir: Path) -> None:
    df, mastr_stichtag = _mastr_wind_dataframe(mastr_dir)

    name_col = "NameStromerzeugungseinheit"
    if name_col not in df.columns:
        name_col = "Name"

    geometry = [Point(lon, lat) for lon, lat in zip(df["Laengengrad"], df["Breitengrad"])]
    properties = pd.DataFrame(
        {
            "einheit_mastr_nr": df["EinheitMastrNummer"],
            "name": df[name_col] if name_col in df.columns else None,
            "leistung_kw": df["leistung_kw"],
            "leistung_mw": df["leistung_mw"],
            "typ": df["typ"],
            "betriebsstatus": df["EinheitBetriebsstatus"],
            "bundesland": df.get("Bundesland"),
            "landkreis": df.get("Landkreis"),
            "lage": df.get("Lage"),
            "seelage": df.get("Seelage"),
        }
    )

    gdf = gpd.GeoDataFrame(properties, geometry=geometry, crs="EPSG:4326")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver="GeoJSON")

    onshore = int((gdf["typ"] == "onshore").sum())
    offshore = int((gdf["typ"] == "offshore").sum())
    print(
        f"{len(gdf)} Windanlagen nach {output_path} geschrieben "
        f"(Onshore: {onshore}, Offshore: {offshore})."
    )

    meta_path = output_path.with_suffix(".meta.json")
    meta = {
        "source": "Marktstammdatenregister (MaStR)",
        "publisher": "Bundesnetzagentur",
        "license": "Datenlizenz Deutschland – Namensnennung – Version 2.0",
        "filter_status": STATUS_IN_BETRIEB,
        "mastr_stichtag": mastr_stichtag,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count_total": len(gdf),
        "count_onshore": onshore,
        "count_offshore": offshore,
        "leistung_mw_total": round(float(gdf["leistung_mw"].sum()), 1),
    }
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
