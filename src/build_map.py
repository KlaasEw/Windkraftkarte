"""Interaktive Folium-Karte mit Heatmap und klickbaren Verwaltungsgrenzen."""

from __future__ import annotations

import json
from dataclasses import dataclass

import branca.colormap as cm
import folium
import geopandas as gpd
from folium.plugins import HeatMap

from src.aggregate import OffshoreSummary
from src.map_ui import (
    HEATMAP_LAYER_NAME,
    LAYER_LEGENDS,
    add_map_layout,
    legend_item_html,
)


@dataclass(frozen=True)
class MapConfig:
    title: str = "Windenergie in Deutschland"
    center: tuple[float, float] = (51.16, 10.45)
    zoom_start: int = 6
    heat_radius: int = 12
    heat_blur: int = 18


KREIS_COUNT_COLORS = ["#fff7bc", "#fec44f", "#fe9929", "#ec7014", "#cc4c02"]
BUNDESLAND_COUNT_COLORS = ["#edf8fb", "#b3cde3", "#8c96c6", "#8856a7", "#810f7c"]
KREIS_DENSITY_COLORS = ["#f7fcf5", "#c7e9c0", "#74c476", "#238b45", "#00441b"]
BUNDESLAND_DENSITY_COLORS = ["#f7fcfd", "#ccece6", "#66c2a4", "#238b8d", "#005824"]
KREIS_EW_COLORS = ["#f2f0f7", "#cbc9e2", "#9e9ac8", "#756bb1", "#54278f"]
BUNDESLAND_EW_COLORS = ["#fee5d9", "#fcae91", "#fb6a4a", "#de2d26", "#a50f15"]
KREIS_MW_COLORS = ["#fef0d9", "#fdcc8a", "#fc8d59", "#e34a33", "#b30000"]
BUNDESLAND_MW_COLORS = ["#f7fcf0", "#ccebc5", "#7bccc4", "#2b8cbe", "#084081"]
KREIS_MW_DENSITY_COLORS = ["#ffffcc", "#c2e699", "#78c679", "#31a354", "#006837"]
BUNDESLAND_MW_DENSITY_COLORS = ["#ffffd4", "#fed98e", "#fe9929", "#d95f0e", "#993404"]
KREIS_MW_EW_COLORS = ["#fde0dd", "#fa9fb5", "#f768a1", "#dd3497", "#7a0177"]
BUNDESLAND_MW_EW_COLORS = ["#edf8e9", "#bae4b3", "#74c476", "#238b45", "#005a32"]

FIELD_LABELS = {
    "anzahl": "Windanlagen",
    "leistung_mw": "Installierte Leistung (MW)",
    "flaeche_km2": "Fläche (km²)",
    "dichte": "Dichte (je km²)",
    "leistung_dichte": "Leistungsdichte (MW/km²)",
    "einwohner": "Einwohner",
    "je_1000_ew": "Windanlagen je 1.000 EW",
    "mw_je_1000_ew": "MW je 1.000 EW",
}

METRIC_TOOLTIP_FIELDS = {
    "anzahl": ["anzahl"],
    "dichte": ["anzahl", "flaeche_km2", "dichte"],
    "je_1000_ew": ["anzahl", "einwohner", "je_1000_ew"],
    "leistung_mw": ["leistung_mw"],
    "leistung_dichte": ["leistung_mw", "flaeche_km2", "leistung_dichte"],
    "mw_je_1000_ew": ["leistung_mw", "einwohner", "mw_je_1000_ew"],
}


def _tooltip_config(name_column: str, value_column: str) -> tuple[list[str], list[str]]:
    fields = [name_column, *METRIC_TOOLTIP_FIELDS[value_column]]
    aliases = ["Gebiet:", *[f"{FIELD_LABELS[field]}:" for field in METRIC_TOOLTIP_FIELDS[value_column]]]
    return fields, aliases

LAYER_CONFIG = [
    {
        "layer_name": "Bundesländer (Anzahl)",
        "legend_id": LAYER_LEGENDS["Bundesländer (Anzahl)"],
        "name_column": "bundesland_name",
        "value_column": "anzahl",
        "colors": BUNDESLAND_COUNT_COLORS,
        "caption": "Windanlagen pro Bundesland (Anzahl, Onshore)",
        "fill_opacity": 0.45,
        "weight": 2.0,
        "show": False,
    },
    {
        "layer_name": "Bundesländer (MW)",
        "legend_id": LAYER_LEGENDS["Bundesländer (MW)"],
        "name_column": "bundesland_name",
        "value_column": "leistung_mw",
        "colors": BUNDESLAND_MW_COLORS,
        "caption": "Installierte Leistung pro Bundesland (MW, Onshore)",
        "fill_opacity": 0.45,
        "weight": 2.0,
        "show": False,
    },
    {
        "layer_name": "Bundesländer (Dichte je km²)",
        "legend_id": LAYER_LEGENDS["Bundesländer (Dichte je km²)"],
        "name_column": "bundesland_name",
        "value_column": "dichte",
        "colors": BUNDESLAND_DENSITY_COLORS,
        "caption": "Windanlagen pro Bundesland (je km², Onshore)",
        "fill_opacity": 0.45,
        "weight": 2.0,
        "show": False,
    },
    {
        "layer_name": "Bundesländer (MW/km²)",
        "legend_id": LAYER_LEGENDS["Bundesländer (MW/km²)"],
        "name_column": "bundesland_name",
        "value_column": "leistung_dichte",
        "colors": BUNDESLAND_MW_DENSITY_COLORS,
        "caption": "Leistungsdichte pro Bundesland (MW/km², Onshore)",
        "fill_opacity": 0.45,
        "weight": 2.0,
        "show": False,
    },
    {
        "layer_name": "Bundesländer (je 1.000 EW)",
        "legend_id": LAYER_LEGENDS["Bundesländer (je 1.000 EW)"],
        "name_column": "bundesland_name",
        "value_column": "je_1000_ew",
        "colors": BUNDESLAND_EW_COLORS,
        "caption": "Windanlagen pro Bundesland (je 1.000 EW, Onshore)",
        "fill_opacity": 0.45,
        "weight": 2.0,
        "show": False,
    },
    {
        "layer_name": "Bundesländer (MW je 1.000 EW)",
        "legend_id": LAYER_LEGENDS["Bundesländer (MW je 1.000 EW)"],
        "name_column": "bundesland_name",
        "value_column": "mw_je_1000_ew",
        "colors": BUNDESLAND_MW_EW_COLORS,
        "caption": "MW je 1.000 EW pro Bundesland (Onshore)",
        "fill_opacity": 0.45,
        "weight": 2.0,
        "show": False,
    },
    {
        "layer_name": "Kreise (Anzahl)",
        "legend_id": LAYER_LEGENDS["Kreise (Anzahl)"],
        "name_column": "kreis_name",
        "value_column": "anzahl",
        "colors": KREIS_COUNT_COLORS,
        "caption": "Windanlagen pro Kreis (Anzahl, Onshore)",
        "fill_opacity": 0.55,
        "weight": 1.0,
        "show": False,
    },
    {
        "layer_name": "Kreise (MW)",
        "legend_id": LAYER_LEGENDS["Kreise (MW)"],
        "name_column": "kreis_name",
        "value_column": "leistung_mw",
        "colors": KREIS_MW_COLORS,
        "caption": "Installierte Leistung pro Kreis (MW, Onshore)",
        "fill_opacity": 0.55,
        "weight": 1.0,
        "show": False,
    },
    {
        "layer_name": "Kreise (Dichte je km²)",
        "legend_id": LAYER_LEGENDS["Kreise (Dichte je km²)"],
        "name_column": "kreis_name",
        "value_column": "dichte",
        "colors": KREIS_DENSITY_COLORS,
        "caption": "Windanlagen pro Kreis (je km², Onshore)",
        "fill_opacity": 0.55,
        "weight": 1.0,
        "show": False,
    },
    {
        "layer_name": "Kreise (MW/km²)",
        "legend_id": LAYER_LEGENDS["Kreise (MW/km²)"],
        "name_column": "kreis_name",
        "value_column": "leistung_dichte",
        "colors": KREIS_MW_DENSITY_COLORS,
        "caption": "Leistungsdichte pro Kreis (MW/km², Onshore)",
        "fill_opacity": 0.55,
        "weight": 1.0,
        "show": False,
    },
    {
        "layer_name": "Kreise (je 1.000 EW)",
        "legend_id": LAYER_LEGENDS["Kreise (je 1.000 EW)"],
        "name_column": "kreis_name",
        "value_column": "je_1000_ew",
        "colors": KREIS_EW_COLORS,
        "caption": "Windanlagen pro Kreis (je 1.000 EW, Onshore)",
        "fill_opacity": 0.55,
        "weight": 1.0,
        "show": False,
    },
    {
        "layer_name": "Kreise (MW je 1.000 EW)",
        "legend_id": LAYER_LEGENDS["Kreise (MW je 1.000 EW)"],
        "name_column": "kreis_name",
        "value_column": "mw_je_1000_ew",
        "colors": KREIS_MW_EW_COLORS,
        "caption": "MW je 1.000 EW pro Kreis (Onshore)",
        "fill_opacity": 0.55,
        "weight": 1.0,
        "show": False,
    },
]


def _color_scale(
    values: gpd.GeoDataFrame,
    value_column: str,
    colors: list[str],
) -> cm.LinearColormap:
    series = values[value_column].dropna()
    vmin = float(series.min()) if not series.empty else 0.0
    vmax = float(series.max()) if not series.empty else 1.0
    if vmax <= vmin:
        vmax = vmin + 1

    return cm.LinearColormap(colors=colors, vmin=vmin, vmax=vmax)


def _add_region_layer(
    map_obj: folium.Map,
    boundaries: gpd.GeoDataFrame,
    name_column: str,
    value_column: str,
    layer_name: str,
    colormap: cm.LinearColormap,
    fill_opacity: float,
    weight: float,
    show: bool,
) -> folium.GeoJson:
    geojson_data = json.loads(boundaries.to_json())

    def style_function(feature: dict) -> dict:
        value = feature["properties"].get(value_column) or 0
        return {
            "fillColor": colormap(value),
            "color": "#444444",
            "weight": weight,
            "fillOpacity": fill_opacity,
        }

    def highlight_function(_feature: dict) -> dict:
        return {"weight": weight + 1.5, "color": "#111111", "fillOpacity": min(fill_opacity + 0.2, 0.85)}

    tooltip_fields, tooltip_aliases = _tooltip_config(name_column, value_column)
    popup_fields = tooltip_fields
    popup_aliases = [alias.rstrip(":") for alias in tooltip_aliases]

    geojson = folium.GeoJson(
        geojson_data,
        name=layer_name,
        style_function=style_function,
        highlight_function=highlight_function,
        show=show,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=True,
        ),
        popup=folium.GeoJsonPopup(
            fields=popup_fields,
            aliases=popup_aliases,
            localize=True,
            labels=True,
        ),
    )
    geojson.add_to(map_obj)
    return geojson


def build_map(
    turbines: gpd.GeoDataFrame,
    kreise_with_counts: gpd.GeoDataFrame,
    bundeslaender_with_counts: gpd.GeoDataFrame,
    output_path: str,
    config: MapConfig | None = None,
    offshore_summary: OffshoreSummary | None = None,
    mastr_stichtag: str = "2025-02-09",
) -> folium.Map:
    config = config or MapConfig()
    offshore_summary = offshore_summary or OffshoreSummary(anzahl=0, leistung_mw=0.0)
    data_by_column = {
        "bundesland_name": bundeslaender_with_counts,
        "kreis_name": kreise_with_counts,
    }

    m = folium.Map(
        location=list(config.center),
        zoom_start=config.zoom_start,
        tiles=None,
        control_scale=True,
        zoom_control=False,
        prefer_canvas=True,
    )
    folium.TileLayer(
        tiles="CartoDB positron",
        control=False,
        crossOrigin="anonymous",
    ).add_to(m)

    heat_coords = [
        [point.y, point.x]
        for point in turbines.geometry
        if point is not None and not point.is_empty
    ]
    heat_layer = folium.FeatureGroup(name=HEATMAP_LAYER_NAME, show=True)
    HeatMap(
        heat_coords,
        radius=config.heat_radius,
        blur=config.heat_blur,
        max_zoom=12,
        min_opacity=0.35,
    ).add_to(heat_layer)
    heat_layer.add_to(m)

    legend_items: list[str] = []
    choropleth_layer_refs: dict[str, str] = {}

    for layer_cfg in LAYER_CONFIG:
        boundaries = data_by_column[layer_cfg["name_column"]]
        value_column = layer_cfg["value_column"]
        colormap = _color_scale(boundaries, value_column, layer_cfg["colors"])

        geojson = _add_region_layer(
            m,
            boundaries,
            name_column=layer_cfg["name_column"],
            value_column=value_column,
            layer_name=layer_cfg["layer_name"],
            colormap=colormap,
            fill_opacity=layer_cfg["fill_opacity"],
            weight=layer_cfg["weight"],
            show=layer_cfg["show"],
        )
        choropleth_layer_refs[layer_cfg["layer_name"]] = geojson.get_name()

        series = boundaries[value_column].dropna()
        vmin = float(series.min()) if not series.empty else 0.0
        vmax = float(series.max()) if not series.empty else 1.0
        if vmax <= vmin:
            vmax = vmin + 1

        legend_items.append(
            legend_item_html(
                legend_id=layer_cfg["legend_id"],
                layer_name=layer_cfg["layer_name"],
                caption=layer_cfg["caption"],
                colors=layer_cfg["colors"],
                vmin=vmin,
                vmax=vmax,
            )
        )

    folium.LayerControl(collapsed=False, position="bottomright").add_to(m)

    add_map_layout(
        m,
        title=config.title,
        legend_items_html="\n".join(legend_items),
        mastr_stichtag=mastr_stichtag,
        offshore_anzahl=offshore_summary.anzahl,
        offshore_leistung_mw=offshore_summary.leistung_mw,
        choropleth_layer_refs=choropleth_layer_refs,
        heatmap_layer_ref=heat_layer.get_name(),
    )

    m.save(output_path)
    return m
