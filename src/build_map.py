"""Interaktive Folium-Karte mit Heatmap und klickbaren Verwaltungsgrenzen."""

from __future__ import annotations

import json
from dataclasses import dataclass

import branca.colormap as cm
import folium
import geopandas as gpd
from folium.plugins import HeatMap

from src.map_ui import (
    LAYER_LEGENDS,
    add_map_layout,
    legend_item_html,
)


@dataclass(frozen=True)
class MapConfig:
    title: str = "Windräder in Deutschland"
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

POPUP_FIELDS = [
    "anzahl",
    "flaeche_km2",
    "dichte",
    "einwohner",
    "je_1000_ew",
]
POPUP_ALIASES = [
    "Windräder",
    "Fläche (km²)",
    "Dichte (je km²)",
    "Einwohner",
    "Windräder je 1.000 EW",
]

LAYER_CONFIG = [
    {
        "layer_name": "Bundesländer (Anzahl)",
        "legend_id": LAYER_LEGENDS["Bundesländer (Anzahl)"],
        "name_column": "bundesland_name",
        "value_column": "anzahl",
        "colors": BUNDESLAND_COUNT_COLORS,
        "caption": "Windräder pro Bundesland (Anzahl)",
        "fill_opacity": 0.45,
        "weight": 2.0,
        "show": True,
    },
    {
        "layer_name": "Bundesländer (Dichte je km²)",
        "legend_id": LAYER_LEGENDS["Bundesländer (Dichte je km²)"],
        "name_column": "bundesland_name",
        "value_column": "dichte",
        "colors": BUNDESLAND_DENSITY_COLORS,
        "caption": "Windräder pro Bundesland (je km²)",
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
        "caption": "Windräder pro Kreis (Anzahl)",
        "fill_opacity": 0.55,
        "weight": 1.0,
        "show": True,
    },
    {
        "layer_name": "Kreise (Dichte je km²)",
        "legend_id": LAYER_LEGENDS["Kreise (Dichte je km²)"],
        "name_column": "kreis_name",
        "value_column": "dichte",
        "colors": KREIS_DENSITY_COLORS,
        "caption": "Windräder pro Kreis (je km²)",
        "fill_opacity": 0.55,
        "weight": 1.0,
        "show": False,
    },
    {
        "layer_name": "Bundesländer (je 1.000 EW)",
        "legend_id": LAYER_LEGENDS["Bundesländer (je 1.000 EW)"],
        "name_column": "bundesland_name",
        "value_column": "je_1000_ew",
        "colors": BUNDESLAND_EW_COLORS,
        "caption": "Windräder pro Bundesland (je 1.000 EW)",
        "fill_opacity": 0.45,
        "weight": 2.0,
        "show": False,
    },
    {
        "layer_name": "Kreise (je 1.000 EW)",
        "legend_id": LAYER_LEGENDS["Kreise (je 1.000 EW)"],
        "name_column": "kreis_name",
        "value_column": "je_1000_ew",
        "colors": KREIS_EW_COLORS,
        "caption": "Windräder pro Kreis (je 1.000 EW)",
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
) -> None:
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

    folium.GeoJson(
        geojson_data,
        name=layer_name,
        style_function=style_function,
        highlight_function=highlight_function,
        show=show,
        tooltip=folium.GeoJsonTooltip(
            fields=[name_column, *POPUP_FIELDS],
            aliases=["Gebiet:", *[f"{alias}:" for alias in POPUP_ALIASES]],
            localize=True,
        ),
        popup=folium.GeoJsonPopup(
            fields=[name_column, *POPUP_FIELDS],
            aliases=["Gebiet", *POPUP_ALIASES],
            localize=True,
            labels=True,
        ),
    ).add_to(map_obj)


def build_map(
    turbines: gpd.GeoDataFrame,
    kreise_with_counts: gpd.GeoDataFrame,
    bundeslaender_with_counts: gpd.GeoDataFrame,
    output_path: str,
    config: MapConfig | None = None,
) -> folium.Map:
    config = config or MapConfig()
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
    heat_layer = folium.FeatureGroup(name="Heatmap", show=True)
    HeatMap(
        heat_coords,
        radius=config.heat_radius,
        blur=config.heat_blur,
        max_zoom=12,
        min_opacity=0.35,
    ).add_to(heat_layer)
    heat_layer.add_to(m)

    legend_items: list[str] = []

    for layer_cfg in LAYER_CONFIG:
        boundaries = data_by_column[layer_cfg["name_column"]]
        value_column = layer_cfg["value_column"]
        colormap = _color_scale(boundaries, value_column, layer_cfg["colors"])

        _add_region_layer(
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
    )

    m.save(output_path)
    return m
