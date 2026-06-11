"""Layout-Hilfen für die Folium-Karte (Legenden, Zoom, CSS/JS)."""

from __future__ import annotations

import folium
from branca.element import MacroElement
from jinja2 import Template

from src.fetch_population import STICHTAG

LAYER_LEGENDS = {
    "Bundesländer (Anzahl)": "legend-bl-anzahl",
    "Bundesländer (Dichte je km²)": "legend-bl-dichte",
    "Bundesländer (je 1.000 EW)": "legend-bl-ew",
    "Kreise (Anzahl)": "legend-kreis-anzahl",
    "Kreise (Dichte je km²)": "legend-kreis-dichte",
    "Kreise (je 1.000 EW)": "legend-kreis-ew",
}


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
                    var layerName = label.textContent.trim();
                    if (Object.prototype.hasOwnProperty.call(layerLegendMap, layerName)) {
                        setLegendVisible(layerName, input.checked);
                    }
                });
            }

            map.on("overlayadd", function(event) {
                setLegendVisible(event.name, true);
            });

            map.on("overlayremove", function(event) {
                setLegendVisible(event.name, false);
            });

            map.whenReady(function() {
                arrangeBottomRightControls();
                syncLegendsFromLayerControl();
            });

            document.addEventListener("change", function(event) {
                if (event.target.closest(".leaflet-control-layers-overlays")) {
                    syncLegendsFromLayerControl();
                }
            });
        })();
        {% endmacro %}
        """
    )

    def __init__(
        self,
        layer_legend_map: dict[str, str],
        export_file_name: str = "windkarte.png",
    ) -> None:
        super().__init__()
        self.layer_legend_map = layer_legend_map
        self.export_file_name = export_file_name


def add_map_layout(
    map_obj: folium.Map,
    title: str,
    legend_items_html: str,
) -> None:
    map_obj.get_root().header.add_child(
        folium.Element(
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>'
        )
    )
    map_obj.get_root().html.add_child(folium.Element(LAYOUT_CSS))

    year, month, day = STICHTAG.split("-")
    stichtag_de = f"{day}.{month}.{year}"
    title_html = f"""
    <div class="windkarte-title">
        <b>{title}</b><br>
        Datenquellen:<br>
        Windräder: OpenStreetMap via Overpass Turbo<br>
        Einwohner: Statistisches Bundesamt (Destatis), Stichtag {stichtag_de}
    </div>
    """
    map_obj.get_root().html.add_child(folium.Element(title_html))

    legend_bar_html = f"""
    <div id="windkarte-legend-bar">
        {legend_items_html}
    </div>
    """
    map_obj.get_root().html.add_child(folium.Element(legend_bar_html))

    map_obj.add_child(MapLayoutScript(LAYER_LEGENDS.copy()))
