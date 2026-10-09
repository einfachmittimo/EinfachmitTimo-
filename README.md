# EinfachmitTimo

Rezept-App mit Streamlit – mit Rezeptsuche, Kategorien, Favoriten, Zutaten, Zubereitung und Nährwerten.

## Lokal starten

1. Python 3.10 oder neuer installieren.
2. Terminal im Projektordner öffnen.
3. Abhängigkeiten installieren:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. App starten:

   ```bash
   python -m streamlit run app.py
   ```

## Auf GitHub hochladen

1. ZIP entpacken.
2. Alle Dateien aus diesem Ordner in dein bereits angelegtes GitHub-Repository hochladen.
3. `app.py`, `recipes.json`, `requirements.txt`, `EinfachmitTimo_Logo.jpg`, `Timo_Portrait.jpg` und `.streamlit/config.toml` müssen im Repository-Root bzw. im genannten Unterordner liegen.
4. Für Streamlit Community Cloud: Repository verbinden und als Main file path `app.py` auswählen. Die Plattform installiert `requirements.txt` automatisch.

## Daten

- `recipes.json` enthält 242 Rezepte.
- Die Nährwerte werden angezeigt, wenn strukturierte Werte oder eine passende Nährwertquelle in den Rezeptdaten vorhanden ist.
- Nicht für jedes Rezept ist ein geprüftes, individuelles Food-Foto vorhanden. Daher ordnet diese Version absichtlich keine beliebigen/recycelten Bilder zu; sie verwendet gestylte Platzhalter, bis korrekte Fotos ergänzt sind.

## Dateien

- `app.py` – Streamlit-App
- `recipes.json` – Rezeptdatenbank
- `EinfachmitTimo_Logo.jpg` – Markenlogo
- `Timo_Portrait.jpg` – Portrait in der Seitenleiste
- `requirements.txt` – Python-Abhängigkeiten
- `.streamlit/config.toml` – Farben passend zum Design
- `.gitignore` – hält Cache-, virtuelle Umgebungs- und Geheimnisdateien aus Git heraus
