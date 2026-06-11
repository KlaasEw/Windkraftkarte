# Windkraftkarte

Interaktive Karte der Windenergieanlagen in Deutschland. Die Anwendung zählt Windanlagen pro Kreis und Bundesland, berechnet installierte Leistung (MW), Flächen- und Leistungsdichte sowie Kennzahlen je 1.000 Einwohner und stellt alles in einer übersichtlichen Webkarte dar.

![Bild der generrierten Karte](/assets/windkarte.png)

---

## Nutzung

### Karte ansehen (ohne Installation)

Die fertige Karte liegt unter `output/windkarte.html`. Öffne die Datei einfach im Browser (Doppelklick oder „Öffnen mit …"). Es ist keine Internetverbindung zwingend nötig, sobald die Datei einmal erzeugt wurde — für die Hintergrundkarte und den PNG-Export werden jedoch externe Dienste geladen.

Die Karte ist außerdem online unter [https://klaasew.github.io/Windkraftkarte/](https://klaasew.github.io/Windkraftkarte/) erreichbar. Dort wird die zuletzt veröffentlichte Version angezeigt; Rohdaten können auf der Website nicht neu geladen oder aktualisiert werden. Für einen aktuellen Datenstand muss die Karte lokal neu erzeugt und das Repository aktualisiert werden (siehe „Karte neu erzeugen").

### Karte neu erzeugen

1. Python 3 installieren (empfohlen: Version 3.10 oder neuer).
2. Abhängigkeiten installieren:

   ```bash
   pip install -r requirements.txt
   ```

3. Pipeline starten:

   ```bash
   python main.py
   ```

   Beim ersten Lauf werden alle fehlenden Rohdaten automatisch bezogen. Windanlagen stammen aus dem Marktstammdatenregister (MaStR); der Bulk-Download ist groß (~3 GB) und wird lokal unter `data/mastr/` gespeichert (nicht im Git-Repository). Anschließend erscheint eine Zusammenfassung in der Konsole und die aktualisierte Karte unter `output/windkarte.html`.

   **Hinweis:** Beim ersten MaStR-Download kann der Vorgang je nach Internetverbindung deutlich länger dauern als die bisherige Overpass-Abfrage.

   **Aktualisierung:** Datei `data/wind_mastr_de.geojson` löschen (optional auch `data/mastr/`) und `python main.py` erneut ausführen.

### Bedienung der Karte

| Element | Funktion |
|---|---|
| **Mausrad / Zoomen** | Karte vergrößern und verkleinern |
| **Verschieben** | Mit gedrückter linker Maustaste die Karte bewegen |
| **Layer-Steuerung** (unten rechts) | Einzelne Darstellungsebenen ein- und ausschalten |
| **Heatmap** | Räumliche Verteilung aller Windanlagen (Onshore + Offshore) |
| **Farbige Flächen** | Kreise oder Bundesländer, eingefärbt nach gewählter Kennzahl |
| **Legende** (unten mittig) | Farbskala der aktuell sichtbaren Ebenen |
| **Tooltip** | Beim Überfahren einer Fläche Kurzinfo anzeigen |
| **Klick auf Fläche** | Popup mit allen Kennzahlen für das Gebiet |
| **Download-Symbol** (unten rechts) | Aktuelle Kartenansicht als PNG-Datei speichern |
| **Maßstab** (unten links) | Entfernungen auf der Karte ablesen |

#### Verfügbare Darstellungsebenen

Standardmäßig ist nur die **Heatmap** aktiv. Choropleth-Ebenen (Kreise/Bundesländer) schließen sich gegenseitig aus — beim Aktivieren einer Ebene wird die zuvor gewählte automatisch deaktiviert. Weitere Ebenen können über die Layer-Steuerung hinzugefügt werden:

**Anzahl & Dichte (Onshore, Kreis-/Bundesland-Choropleth):**
- **Anzahl** — Windanlagen im Gebiet
- **Dichte (je km²)** — Anlagen geteilt durch Fläche
- **je 1.000 EW** — Anlagen pro 1.000 Einwohner

**Installierte Leistung (Onshore, Kreis-/Bundesland-Choropleth):**
- **MW** — Summe der Bruttoleistung im Gebiet
- **MW/km²** — Leistungsdichte
- **MW je 1.000 EW** — installierte Leistung pro 1.000 Einwohner

Mehrere Ebenen können gleichzeitig eingeblendet sein; die Legende passt sich der Auswahl an.

**Offshore:** Windenergieanlagen auf See erscheinen in der Heatmap und als gesonderte Gesamtzahl in der Kartenüberschrift. Sie fließen nicht in Kreis-Choropleths ein, da sie außerhalb der Landkreisgrenzen liegen.

---

## Datenquellen

Die Karte kombiniert vier Datenbestände. Grenzen und Einwohner werden bei Bedarf automatisch bezogen; MaStR-Rohdaten liegen unter `data/mastr/` (gitignored).

### Windanlagen — Marktstammdatenregister (MaStR)

| | |
|---|---|
| **Datei** | `data/wind_mastr_de.geojson` (aus Pipeline erzeugt) |
| **Herkunft** | [Marktstammdatenregister](https://www.marktstammdatenregister.de/) der Bundesnetzagentur |
| **Bezug** | Bulk-Download via [`open-mastr`](https://open-mastr.readthedocs.io/), gefiltert auf Wind (Onshore + Offshore), Status „In Betrieb" |
| **Lizenz** | [Datenlizenz Deutschland – Namensnennung – Version 2.0](https://www.govdata.de/dl-de/by-2-0) |
| **Rohdownload** | `data/mastr/` (~3 GB, **nicht** im Git-Repository) |

**Fallback:** Ist noch kein lokaler Bulk-Download unter `data/mastr/` vorhanden, lädt die Pipeline automatisch die aufbereitete Wind-CSV von [Zenodo (open-MaStR)](https://zenodo.org/records/14843222) (~6 MB). Sobald ein Bulk-Download abgeschlossen ist, werden die lokalen SQLite-Daten bevorzugt.

Das MaStR ist das amtliche Register für Stromerzeugungsanlagen in Deutschland. Enthalten sind Bruttoleistung, Betriebsstatus, Koordinaten und die Unterscheidung Wind an Land / Wind auf See.

### Verwaltungsgrenzen — OpenStreetMap / Overpass API

| | |
|---|---|
| **Dateien** | `data/grenzen_de_kreise.geojson`, `data/grenzen_de_bundeslaender.geojson` |
| **Herkunft** | OpenStreetMap, abgefragt über die [Overpass API](https://overpass-api.de/) |
| **Lizenz** | [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/) |

### Einwohnerzahlen — Statistisches Bundesamt (Destatis)

| | |
|---|---|
| **Datei** | `data/einwohner_destatis.csv` |
| **Datensatz** | Bevölkerung auf Kreisebene (12411-0015), Stichtag 31. Dezember 2024 |

### Hintergrundkarte — CARTO

Kartenkacheln von [CARTO](https://carto.com/) (Stil „Positron"). Internetverbindung beim Betrachten der HTML-Datei erforderlich.

---

## Berechnete Kennzahlen

Für jedes Kreis- und Bundeslandgebiet (Onshore, räumliche Zuordnung):

- **Windanlagen** — Anzahl der Anlagen im Gebiet
- **Installierte Leistung (MW)** — Summe der Bruttoleistung
- **Fläche (km²)** — Fläche des Verwaltungsgebiets
- **Dichte (je km²)** — Anlagen pro Quadratkilometer
- **Leistungsdichte (MW/km²)** — Megawatt pro Quadratkilometer
- **Einwohner** — Bevölkerungszahl laut Destatis
- **Windanlagen je 1.000 EW**
- **MW je 1.000 EW**

---

## Technik (Kurzüberblick)

```
data/                    Rohdaten (MaStR-Cache, Grenzen, Einwohner)
src/                     Verarbeitung und Kartenerstellung
output/windkarte.html    Ergebnis — interaktive Karte im Browser
main.py                  Einstiegspunkt der Pipeline
```

Kernabhängigkeiten: GeoPandas, Folium, Pandas, open-mastr (siehe `requirements.txt`).

---

## Hinweise und Einschränkungen

- Windanlagen spiegeln den **MaStR-Stand zum Zeitpunkt des Exports** wider (Meldefrist ~1 Monat nach Inbetriebnahme).
- Kreis- und Bundesland-Choropleths zeigen **Onshore**-Kennzahlen; Offshore wird separat ausgewiesen.
- Der MaStR-Bulk-Download wird nicht ins Git-Repository aufgenommen (`data/mastr/` in `.gitignore`).
- Beim erneuten Laden werden die jeweiligen Dateien in `data/` überschrieben.

---

## Lizenz und Attribution

- Windanlagen: © [Bundesnetzagentur](https://www.bundesnetzagentur.de/) — Marktstammdatenregister, [dl-de/by-2-0](https://www.govdata.de/dl-de/by-2-0)
- Grenzdaten: © [OpenStreetMap](https://www.openstreetmap.org/copyright)-Mitwirkende, ODbL
- Einwohnerzahlen: © [Statistisches Bundesamt](https://www.destatis.de/)
- Kartenhintergrund: © [CARTO](https://carto.com/attributions), © OpenStreetMap-Mitwirkende
