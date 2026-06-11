"""Layout-Hilfen für die Folium-Karte (Legenden, Zoom, CSS/JS)."""

from __future__ import annotations

import folium
from branca.element import MacroElement
from jinja2 import Template

from src.fetch_population import STICHTAG
from src.fetch_mastr import format_stichtag_de

LAYER_LEGENDS = {
    "Bundesländer (Anzahl)": "legend-bl-anzahl",
    "Bundesländer (Dichte je km²)": "legend-bl-dichte",
    "Bundesländer (je 1.000 EW)": "legend-bl-ew",
    "Bundesländer (MW)": "legend-bl-mw",
    "Bundesländer (MW/km²)": "legend-bl-mw-dichte",
    "Bundesländer (MW je 1.000 EW)": "legend-bl-mw-ew",
    "Kreise (Anzahl)": "legend-kreis-anzahl",
    "Kreise (Dichte je km²)": "legend-kreis-dichte",
    "Kreise (je 1.000 EW)": "legend-kreis-ew",
    "Kreise (MW)": "legend-kreis-mw",
    "Kreise (MW/km²)": "legend-kreis-mw-dichte",
    "Kreise (MW je 1.000 EW)": "legend-kreis-mw-ew",
}


HEATMAP_LAYER_NAME = "Heatmap (Onshore + Offshore)"


def format_legend_value(value: float) -> str:
    if value >= 100:
        return f"{value:.0f}"
    if value >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def legend_item_html(
    legend_id: str,
    layer_name: str,
    caption: str,
    colors: list[str],
    vmin: float,
    vmax: float,
) -> str:
    gradient = ", ".join(colors)
    return f"""
    <div id="{legend_id}" class="windkarte-legend" data-layer="{layer_name}" style="display: none;">
        <div class="windkarte-legend-caption">{caption}</div>
        <div class="windkarte-legend-gradient" style="background: linear-gradient(to right, {gradient});"></div>
        <div class="windkarte-legend-ticks">
            <span>{format_legend_value(vmin)}</span>
            <span>{format_legend_value(vmax)}</span>
        </div>
    </div>
    """


LAYOUT_CSS = """
<style>
    .windkarte-title {
        position: fixed;
        top: 12px;
        left: 12px;
        z-index: 1000;
        background: white;
        padding: 10px 14px;
        border-radius: 6px;
        box-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);
        font-family: sans-serif;
        font-size: 14px;
        max-width: min(420px, calc(100vw - 24px));
    }

    #windkarte-legend-bar {
        position: fixed;
        bottom: 12px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 1000;
        display: flex;
        gap: 14px;
        flex-wrap: wrap;
        justify-content: center;
        max-width: calc(100vw - 180px);
        pointer-events: none;
    }

    .windkarte-legend {
        background: white;
        padding: 8px 12px;
        border-radius: 6px;
        box-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);
        flex-direction: column;
        gap: 4px;
        min-width: 220px;
        font-family: sans-serif;
        font-size: 12px;
    }

    .windkarte-legend-caption {
        font-weight: 600;
        color: #222;
    }

    .windkarte-legend-gradient {
        height: 14px;
        border-radius: 3px;
        border: 1px solid rgba(0, 0, 0, 0.15);
    }

    .windkarte-legend-ticks {
        display: flex;
        justify-content: space-between;
        color: #444;
    }

    .leaflet-bottom.leaflet-right {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 8px;
        margin-bottom: 10px;
        margin-right: 10px;
    }

    .leaflet-bottom.leaflet-right .windkarte-export-control {
        order: 0;
        margin: 0 !important;
        border: none;
        box-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);
    }

    .windkarte-export-control a {
        width: 34px;
        height: 34px;
        line-height: 34px;
        text-align: center;
        display: block;
        background: #fff;
        color: #333;
        text-decoration: none;
        font-size: 15px;
    }

    .windkarte-export-control a:hover,
    .windkarte-export-control a:focus {
        background: #f4f4f4;
        color: #111;
    }

    .windkarte-export-control a.windkarte-export-busy {
        opacity: 0.55;
        pointer-events: none;
    }

    body.windkarte-capturing .windkarte-export-control,
    body.windkarte-capturing .leaflet-control-zoom,
    body.windkarte-capturing .leaflet-control-layers {
        display: none !important;
    }

    .leaflet-bottom.leaflet-right .leaflet-control-zoom {
        order: 1;
        margin: 0 !important;
        border: none;
        box-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);
    }

    .leaflet-bottom.leaflet-right .leaflet-control-layers {
        order: 2;
        margin: 0 !important;
    }

    .leaflet-control-layers-expanded .leaflet-control-layers-overlays::before {
        content: "Datenlayer";
        display: block;
        font-weight: 700;
        margin-bottom: 6px;
        padding: 0 4px;
    }

    .leaflet-control-layers-base,
    .leaflet-control-layers-separator {
        display: none !important;
    }

    .leaflet-bottom.leaflet-right .leaflet-control-attribution {
        order: 3;
        margin: 0 !important;
        white-space: normal;
        text-align: right;
        max-width: 280px;
        line-height: 1.35;
        background: rgba(255, 255, 255, 0.9);
        box-shadow: 0 1px 6px rgba(0, 0, 0, 0.15);
    }

    .leaflet-bottom.leaflet-left .leaflet-control-scale {
        margin-bottom: 12px;
        margin-left: 12px;
    }
</style>
"""


class MapLayoutScript(MacroElement):
    """Zoom, Export und Legenden-Sichtbarkeit für die Karte."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        (function() {
            var map = {{ this._parent.get_name() }};
            var layerLegendMap = {{ this.layer_legend_map | tojson }};
            var exportFileName = {{ this.export_file_name | tojson }};
            var choroplethLayersByName = {
                {%- for name, var_name in this.choropleth_layer_refs.items() %}
                {{ name | tojson }}: {{ var_name }},
                {%- endfor %}
            };
            var heatmapLayer = {{ this.heatmap_layer_ref }};
            var heatmapLayerName = {{ this.heatmap_layer_name | tojson }};

            if (map.zoomControl) {
                map.zoomControl.remove();
            }
            L.control.zoom({position: "bottomright"}).addTo(map);

            var ExportControl = L.Control.extend({
                options: {position: "bottomright"},
                onAdd: function() {
                    var container = L.DomUtil.create(
                        "div",
                        "leaflet-bar leaflet-control windkarte-export-control"
                    );
                    var link = L.DomUtil.create("a", "windkarte-export-button", container);
                    link.href = "#";
                    link.title = "Karte als PNG exportieren";
                    link.setAttribute("aria-label", "Karte als PNG exportieren");
                    link.innerHTML = '<i class="fa fa-download" aria-hidden="true"></i>';

                    L.DomEvent.disableClickPropagation(container);
                    L.DomEvent.on(link, "click", function(event) {
                        L.DomEvent.preventDefault(event);
                        L.DomEvent.stopPropagation(event);
                        exportMapScreenshot(link);
                    });
                    return container;
                },
            });
            new ExportControl().addTo(map);

            function arrangeBottomRightControls() {
                var mapContainer = map.getContainer();
                var corner = mapContainer.querySelector(".leaflet-bottom.leaflet-right");
                if (!corner) {
                    return;
                }

                var exportControl = corner.querySelector(".windkarte-export-control");
                var zoom = corner.querySelector(".leaflet-control-zoom");
                var layers = corner.querySelector(".leaflet-control-layers");
                var attribution = mapContainer.querySelector(".leaflet-control-attribution");

                if (attribution && attribution.parentElement !== corner) {
                    corner.appendChild(attribution);
                }

                [exportControl, zoom, layers, attribution].filter(Boolean).forEach(function(control) {
                    corner.appendChild(control);
                });
            }

            function waitForNextPaint() {
                return new Promise(function(resolve) {
                    requestAnimationFrame(function() {
                        requestAnimationFrame(resolve);
                    });
                });
            }

            function fixLeafletSvgTransforms(clonedDoc) {
                clonedDoc.querySelectorAll("svg.leaflet-zoom-animated").forEach(function(svg) {
                    var transform = svg.style.transform;
                    if (!transform || transform === "none") {
                        return;
                    }

                    var match = transform.match(/matrix\\(([^)]+)\\)/);
                    if (!match) {
                        return;
                    }

                    var values = match[1].split(",").map(function(value) {
                        return parseFloat(value.trim());
                    });
                    if (values.length < 6) {
                        return;
                    }

                    svg.style.transform = "none";
                    svg.style.left = values[4] + "px";
                    svg.style.top = values[5] + "px";
                });
            }

            async function exportMapScreenshot(exportButton) {
                if (typeof html2canvas === "undefined") {
                    window.alert("Export nicht verfügbar: html2canvas konnte nicht geladen werden.");
                    return;
                }

                if (exportButton) {
                    exportButton.classList.add("windkarte-export-busy");
                }

                document.body.classList.add("windkarte-capturing");
                await waitForNextPaint();

                try {
                    var canvas = await html2canvas(document.body, {
                        useCORS: true,
                        allowTaint: false,
                        backgroundColor: "#ffffff",
                        scale: Math.min(window.devicePixelRatio || 1, 2),
                        logging: false,
                        onclone: function(clonedDoc) {
                            clonedDoc.body.classList.add("windkarte-capturing");
                            fixLeafletSvgTransforms(clonedDoc);
                        },
                    });

                    await new Promise(function(resolve, reject) {
                        canvas.toBlob(function(blob) {
                            if (!blob) {
                                reject(new Error("PNG konnte nicht erzeugt werden."));
                                return;
                            }
                            var url = URL.createObjectURL(blob);
                            var link = document.createElement("a");
                            link.href = url;
                            link.download = exportFileName;
                            link.click();
                            URL.revokeObjectURL(url);
                            resolve();
                        }, "image/png");
                    });
                } catch (error) {
                    console.error(error);
                    window.alert("Screenshot konnte nicht erstellt werden.");
                } finally {
                    document.body.classList.remove("windkarte-capturing");
                    if (exportButton) {
                        exportButton.classList.remove("windkarte-export-busy");
                    }
                }
            }

            function isChoroplethLayer(layerName) {
                return Object.prototype.hasOwnProperty.call(layerLegendMap, layerName);
            }

            function getOverlayLabelName(label) {
                var span = label.querySelector("span");
                if (span) {
                    return span.textContent.trim();
                }
                return label.textContent.trim();
            }

            function findInputForLayerName(layerName) {
                var container = document.querySelector(".leaflet-control-layers-overlays");
                if (!container) {
                    return null;
                }

                var matchedInput = null;
                container.querySelectorAll("label").forEach(function(label) {
                    if (getOverlayLabelName(label) === layerName) {
                        matchedInput = label.querySelector("input");
                    }
                });
                return matchedInput;
            }

            function disableHeatmapPointerEvents() {
                if (!heatmapLayer) {
                    return;
                }

                heatmapLayer.eachLayer(function(layer) {
                    if (layer._canvas) {
                        layer._canvas.style.pointerEvents = "none";
                    }
                });
            }

            function ensureChoroplethAboveHeatmap() {
                if (heatmapLayer && map.hasLayer(heatmapLayer)) {
                    heatmapLayer.bringToBack();
                    heatmapLayer.eachLayer(function(layer) {
                        if (typeof layer.bringToBack === "function") {
                            layer.bringToBack();
                        }
                    });
                    disableHeatmapPointerEvents();
                }

                Object.keys(choroplethLayersByName).forEach(function(name) {
                    var layer = choroplethLayersByName[name];
                    if (map.hasLayer(layer) && typeof layer.bringToFront === "function") {
                        layer.bringToFront();
                    }
                });
            }

            function activateChoroplethLayer(layerName) {
                Object.keys(choroplethLayersByName).forEach(function(name) {
                    if (name === layerName) {
                        return;
                    }
                    var layer = choroplethLayersByName[name];
                    if (map.hasLayer(layer)) {
                        map.removeLayer(layer);
                    }
                    var input = findInputForLayerName(name);
                    if (input) {
                        input.checked = false;
                    }
                    setLegendVisible(name, false);
                });

                var activeLayer = choroplethLayersByName[layerName];
                if (!map.hasLayer(activeLayer)) {
                    map.addLayer(activeLayer);
                }
                var activeInput = findInputForLayerName(layerName);
                if (activeInput) {
                    activeInput.checked = true;
                }
                setLegendVisible(layerName, true);
                ensureChoroplethAboveHeatmap();
            }

            function setupExclusiveChoroplethControl() {
                var container = document.querySelector(".leaflet-control-layers-overlays");
                if (!container) {
                    return;
                }

                container.addEventListener("click", function(event) {
                    var label = event.target.closest("label");
                    if (!label || !container.contains(label)) {
                        return;
                    }

                    var input = label.querySelector("input");
                    if (!input || input.type !== "checkbox") {
                        return;
                    }

                    var layerName = getOverlayLabelName(label);
                    if (!isChoroplethLayer(layerName)) {
                        return;
                    }

                    event.preventDefault();
                    event.stopPropagation();
                    event.stopImmediatePropagation();

                    var layer = choroplethLayersByName[layerName];
                    if (!layer) {
                        return;
                    }

                    if (map.hasLayer(layer)) {
                        map.removeLayer(layer);
                        input.checked = false;
                        setLegendVisible(layerName, false);
                        return;
                    }

                    activateChoroplethLayer(layerName);
                }, true);
            }

            function setLegendVisible(layerName, visible) {
                var legendId = layerLegendMap[layerName];
                if (!legendId) {
                    return;
                }
                var legend = document.getElementById(legendId);
                if (legend) {
                    legend.style.display = visible ? "flex" : "none";
                }
            }

            function syncLegendsFromLayerControl() {
                Object.keys(layerLegendMap).forEach(function(layerName) {
                    setLegendVisible(layerName, false);
                });

                var container = document.querySelector(".leaflet-control-layers-overlays");
                if (!container) {
                    return;
                }

                container.querySelectorAll("label").forEach(function(label) {
                    var input = label.querySelector("input");
                    if (!input) {
                        return;
                    }
                    var layerName = getOverlayLabelName(label);
                    if (Object.prototype.hasOwnProperty.call(layerLegendMap, layerName)) {
                        setLegendVisible(layerName, input.checked);
                    }
                });
            }

            map.on("overlayadd", function(event) {
                if (event.layer === heatmapLayer || event.name === heatmapLayerName) {
                    ensureChoroplethAboveHeatmap();
                }
            });

            map.whenReady(function() {
                arrangeBottomRightControls();
                setupExclusiveChoroplethControl();
                disableHeatmapPointerEvents();
                syncLegendsFromLayerControl();
            });
        })();
        {% endmacro %}
        """
    )

    def __init__(
        self,
        layer_legend_map: dict[str, str],
        choropleth_layer_refs: dict[str, str] | None = None,
        heatmap_layer_ref: str = "",
        heatmap_layer_name: str = HEATMAP_LAYER_NAME,
        export_file_name: str = "windkarte.png",
    ) -> None:
        super().__init__()
        self.layer_legend_map = layer_legend_map
        self.choropleth_layer_refs = choropleth_layer_refs or {}
        self.heatmap_layer_ref = heatmap_layer_ref
        self.heatmap_layer_name = heatmap_layer_name
        self.export_file_name = export_file_name


def add_map_layout(
    map_obj: folium.Map,
    title: str,
    legend_items_html: str,
    mastr_stichtag: str,
    offshore_anzahl: int = 0,
    offshore_leistung_mw: float = 0.0,
    choropleth_layer_refs: dict[str, str] | None = None,
    heatmap_layer_ref: str = "",
) -> None:
    map_obj.get_root().header.add_child(
        folium.Element(
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>'
        )
    )
    map_obj.get_root().html.add_child(folium.Element(LAYOUT_CSS))

    year, month, day = STICHTAG.split("-")
    stichtag_de = f"{day}.{month}.{year}"
    mastr_stichtag_de = format_stichtag_de(mastr_stichtag)
    offshore_line = ""
    if offshore_anzahl > 0:
        offshore_line = (
            f"<br>Offshore gesamt: {offshore_anzahl} Anlagen, "
            f"{offshore_leistung_mw:.1f} MW (nicht Kreis-zugeordnet)"
        )

    title_html = f"""
    <div class="windkarte-title">
        <b>{title}</b><br>
        Datenquellen:<br>
        Windanlagen: Marktstammdatenregister (MaStR), Bundesnetzagentur,
        Stichtag {mastr_stichtag_de}<br>
        Grenzen: OpenStreetMap via Overpass Turbo<br>
        Einwohner: Statistisches Bundesamt (Destatis), Stichtag {stichtag_de}
        {offshore_line}
    </div>
    """
    map_obj.get_root().html.add_child(folium.Element(title_html))

    legend_bar_html = f"""
    <div id="windkarte-legend-bar">
        {legend_items_html}
    </div>
    """
    map_obj.get_root().html.add_child(folium.Element(legend_bar_html))

    map_obj.add_child(
        MapLayoutScript(
            LAYER_LEGENDS.copy(),
            choropleth_layer_refs=choropleth_layer_refs,
            heatmap_layer_ref=heatmap_layer_ref,
        )
    )
