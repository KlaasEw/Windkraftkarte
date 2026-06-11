# Windkraftkarte

Interaktive Karte der Windenergieanlagen in Deutschland. Die Anwendung zählt Windräder pro Kreis und Bundesland, berechnet Kennzahlen wie Flächendichte und Anteil je 1.000 Einwohner und stellt alles in einer übersichtlichen Webkarte dar.

![Bild der generrierten Karte](/assets/windkarte.png)

---

## Nutzung

### Karte ansehen (ohne Installation)

Die fertige Karte liegt unter `output/windkarte.html`. Öffne die Datei einfach im Browser (Doppelklick oder „Öffnen mit …“). Es ist keine Internetverbindung zwingend nötig, sobald die Datei einmal erzeugt wurde — für die Hintergrundkarte und den PNG-Export werden jedoch externe Dienste geladen.

Die Karte ist außerdem online unter [https://klaasew.github.io/Windkraftkarte/](https://klaasew.github.io/Windkraftkarte/) erreichbar. Dort wird die zuletzt veröffentlichte Version angezeigt; Rohdaten können auf der Website nicht neu geladen oder aktualisiert werden. Für einen aktuellen Datenstand muss die Karte lokal neu erzeugt und das Repository aktualisiert werden (siehe „Karte neu erzeugen“).

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

   Beim ersten Lauf werden alle fehlenden Rohdaten (Windräder, Verwaltungsgrenzen, Einwohnerzahlen) automatisch aus dem Netz geladen und unter `data/` gespeichert. Anschließend erscheint eine Zusammenfassung in der Konsole und die aktualisierte Karte unter `output/windkarte.html`.

   **Hinweis:** Das Laden der Windräder kann einige Minuten dauern, da alle Windenergieanlagen in Deutschland von der Overpass API abgefragt werden.

### Bedienung der Karte

| Element | Funktion |
|---|---|
| **Mausrad / Zoomen** | Karte vergrößern und verkleinern |
| **Verschieben** | Mit gedrückter linker Maustaste die Karte bewegen |
| **Layer-Steuerung** (unten rechts) | Einzelne Darstellungsebenen ein- und ausschalten |
| **Heatmap** | Zeigt die räumliche Verteilung aller Windrad-Standorte als Dichtekarte |
| **Farbige Flächen** | Kreise oder Bundesländer, eingefärbt nach gewählter Kennzahl |
| **Legende** (unten mittig) | Farbskala der aktuell sichtbaren Ebenen |
| **Tooltip** | Beim Überfahren einer Fläche Kurzinfo anzeigen |
| **Klick auf Fläche** | Popup mit allen Kennzahlen für das Gebiet |
| **Download-Symbol** (unten rechts) | Aktuelle Kartenansicht als PNG-Datei speichern |
| **Maßstab** (unten links) | Entfernungen auf der Karte ablesen |

#### Verfügbare Darstellungsebenen

Standardmäßig sind die Heatmap sowie die Ebenen **Bundesländer (Anzahl)** und **Kreise (Anzahl)** aktiv. Weitere Ebenen können über die Layer-Steuerung hinzugefügt werden:

- **Anzahl** — absolute Zahl der Windräder im Gebiet
- **Dichte (je km²)** — Windräder geteilt durch die Fläche des Gebiets
- **je 1.000 EW** — Windräder pro 1.000 Einwohner (bezogen auf den Destatis-Stichtag)

Mehrere Ebenen können gleichzeitig eingeblendet sein; die Legende passt sich der Auswahl an.

---

## Datenquellen

Die Karte kombiniert vier Datenbestände. Alle werden beim Ausführen von `main.py` bei Bedarf automatisch bezogen und unter `data/` gespeichert.

### Windräder — OpenStreetMap / Overpass API

| | |
|---|---|
| **Datei** | `data/Windraeder_DE.geojson` |
| **Herkunft** | [OpenStreetMap](https://www.openstreetmap.org/) (Community-Kartierung) |
| **Bezug** | [Overpass API](https://overpass-api.de/) — alle Objekte in Deutschland mit `generator:source=wind` |
| **Lizenz** | [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/) |
| **Automatischer Download** | Ja, falls die Datei noch nicht existiert |

Die Abfrage entspricht der folgenden Overpass-Query (in Overpass Turbo mit `{{geocodeArea:Deutschland}}` für den Suchbereich):

```
[out:json][timeout:180];
area["ISO3166-1"="DE"]["admin_level"="2"]->.searchArea;
nwr["generator:source"="wind"](area.searchArea);
out geom;
```

OpenStreetMap enthält für viele Windenergieanlagen Standort und teils Zusatzinformationen (z. B. Hersteller, Modell, Nennleistung, Betreiber). Die Daten stammen von Freiwilligen und sind **nicht amtlich vollständig oder geprüft**. Fehlende Anlagen, veraltete Einträge oder leicht versetzte Positionen sind möglich.

**Aktualisierung:** Datei `data/Windraeder_DE.geojson` löschen und `python main.py` erneut ausführen, um einen frischen Stand von OpenStreetMap zu laden.

### Verwaltungsgrenzen — OpenStreetMap / Overpass API

| | |
|---|---|
| **Dateien** | `data/grenzen_de_kreise.geojson`, `data/grenzen_de_bundeslaender.geojson` |
| **Herkunft** | OpenStreetMap, abgefragt über die [Overpass API](https://overpass-api.de/) |
| **Inhalt** | Kreisgrenzen (Verwaltungsebene 6) und Bundeslandgrenzen (Ebene 4) für Deutschland |
| **Automatischer Download** | Ja, falls die Dateien noch nicht existieren |

Die Grenzen dienen dazu, jedes Windrad einem Kreis und Bundesland zuzuordnen. Sie basieren auf den in OSM hinterlegten Amtlichen Gemeindeschlüsseln (AGS) bzw. ISO-Codes der Bundesländer.

### Einwohnerzahlen — Statistisches Bundesamt (Destatis)

| | |
|---|---|
| **Datei** | `data/einwohner_destatis.csv` |
| **Herkunft** | [Statistisches Bundesamt](https://www.destatis.de/) — GENESIS INSPIRE-Dienst |
| **Datensatz** | Bevölkerung auf Kreisebene (12411-0015) |
| **Stichtag** | 31. Dezember 2024 |
| **Automatischer Download** | Ja, falls die Datei noch nicht existiert |

Die Einwohnerzahlen werden für die Kennzahl „Windräder je 1.000 Einwohner“ verwendet. Auf Kreisebene stammen sie direkt von Destatis; die Bundeslandwerte werden daraus summiert.

### Hintergrundkarte — CARTO

Die sichtbare Basiskarte (heller Hintergrund) nutzt Kartenkacheln von [CARTO](https://carto.com/) (Stil „Positron“). Dafür ist beim Betrachten der HTML-Datei eine Internetverbindung erforderlich.

---

## Berechnete Kennzahlen

Für jedes Kreis- und Bundeslandgebiet werden folgende Werte ermittelt:

- **Windräder** — Anzahl der Windenergieanlagen, deren Standort im Gebiet liegt
- **Fläche (km²)** — Fläche des Verwaltungsgebiets
- **Dichte (je km²)** — Windräder pro Quadratkilometer
- **Einwohner** — Bevölkerungszahl laut Destatis (Stichtag 31.12.2024)
- **Windräder je 1.000 EW** — Windräder pro 1.000 Einwohner

Windräder, die keinem Kreis eindeutig zugeordnet werden können, fließen nicht in die Gebietszählung ein.

---

## Technik (Kurzüberblick)

Das Projekt ist eine Python-Pipeline: Rohdaten laden, Windräder den Verwaltungsgebieten zuordnen, Kennzahlen berechnen und daraus eine interaktive HTML-Karte erzeugen. Kernabhängigkeiten sind unter anderem GeoPandas, Folium und Pandas (siehe `requirements.txt`).

```
data/                    Rohdaten (Windräder, Grenzen, Einwohner)
src/                     Verarbeitung und Kartenerstellung
output/windkarte.html    Ergebnis — interaktive Karte im Browser
main.py                  Einstiegspunkt der Pipeline
```

---

## Hinweise und Einschränkungen

- Die Windrad-Standorte spiegeln den **OpenStreetMap-Stand zum Zeitpunkt des Exports** wider, nicht einen amtlichen Anlagenregister.
- Grenzen und Einwohnerzahlen können von anderen Stichtagen oder Quellen abweichen; die Karte mischt daher Daten mit unterschiedlichen Aktualitätsständen.
- Der PNG-Export erfasst die gesamte Browseransicht; bei sehr großen Bildschirmen kann die Auflösung variieren.
- Beim erneuten Laden werden die jeweiligen Dateien in `data/` überschrieben. Dazu die gewünschte Datei löschen und `python main.py` erneut starten.

---

## Lizenz und Attribution

- Windrad- und Grenzdaten: © [OpenStreetMap](https://www.openstreetmap.org/copyright)-Mitwirkende, ODbL
- Einwohnerzahlen: © [Statistisches Bundesamt](https://www.destatis.de/)
- Kartenhintergrund: © [CARTO](https://carto.com/attributions), © OpenStreetMap-Mitwirkende

Bei Weitergabe oder Veröffentlichung der Karte sind die jeweiligen Quellenangaben zu beachten.
