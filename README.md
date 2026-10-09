# Essensplaner – Aldi/Lidl Angebote ("EinfachmitTimo")

Enthaltene Dateien:
- `app.py` – Web-Oberfläche (Streamlit), im EinfachmitTimo-Design
- `essensplaner.py` – ursprüngliche Terminal-Version
- `recipes.json` – deine Rezeptdatenbank
- `requirements.txt` – Liste der benötigten Pakete (fürs Hosting nötig)
- `.gitignore` – verhindert, dass Geheimnisse aus Versehen hochgeladen werden
- `secrets.toml.beispiel` – Vorlage für deine API-Keys (siehe unten)

---

## 🌍 Online stellen (Hosting) – Schritt für Schritt

Wir nutzen **Streamlit Community Cloud** – kostenlos, vom Streamlit-Hersteller
selbst betrieben, und gut geeignet für genau diese Art App.

### Schritt 1: GitHub-Konto erstellen
1. Gehe auf **github.com** und erstelle ein kostenloses Konto (falls noch nicht vorhanden)
2. E-Mail bestätigen

### Schritt 2: Neues Repository (= Projektordner auf GitHub) anlegen
1. Oben rechts auf das **"+"** und dann **"New repository"**
2. Name z. B. `essensplaner`
3. Sichtbarkeit: **Public** (öffentlich) – das ist für Streamlit Cloud kostenlos nötig.
   Dein Marktguru-Key liegt dank der `secrets.toml`-Lösung trotzdem NICHT öffentlich sichtbar.
4. "Create repository" klicken

### Schritt 3: Deine Dateien hochladen
1. Im neuen Repository auf **"uploading an existing file"** klicken
2. Folgende Dateien hochladen: `app.py`, `essensplaner.py`, `recipes.json`,
   `requirements.txt`, `.gitignore`
   (die `secrets.toml.beispiel` und echte Keys **NICHT** hochladen!)
3. Unten "Commit changes" klicken

### Schritt 4: Bei Streamlit Community Cloud anmelden
1. Gehe auf **share.streamlit.io**
2. "Sign up" bzw. "Continue with GitHub" – mit deinem GitHub-Konto anmelden
3. Streamlit darf Zugriff auf deine Repositories bekommen (bestätigen)

### Schritt 5: App deployen
1. "New app" / "Create app" klicken
2. Dein Repository `essensplaner` auswählen
3. Als Hauptdatei `app.py` angeben
4. Auf **"Advanced settings"** klicken → dort unter **"Secrets"** folgendes einfügen:
```
[marktguru]
clientkey = "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90="
apikey = "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE="
```
5. "Deploy" klicken

Nach ein paar Minuten bekommst du eine echte Internetadresse
(z. B. `https://essensplaner-timo.streamlit.app`), die von überall erreichbar ist –
nicht mehr nur im eigenen WLAN.

### Updates später hochladen
Änderst du `app.py` oder `recipes.json` künftig (z. B. neue Rezepte), lädst du die
aktualisierte Datei einfach wieder bei GitHub hoch ("Add file" → "Upload files" →
überschreiben) – die Streamlit-App aktualisiert sich dann von selbst.

---

## 💻 Lokal starten (auf deinem PC, wie bisher)

```
pip install streamlit requests
streamlit run app.py
```

Für die lokale Nutzung brauchst du keine `secrets.toml` – der Code hat einen
eingebauten Fallback auf die Keys direkt im Code, falls keine `secrets.toml`
gefunden wird.

Falls du lokal trotzdem genauso wie online testen willst: Erstelle einen Ordner
`.streamlit` neben `app.py`, und darin eine Datei `secrets.toml` mit dem Inhalt
aus `secrets.toml.beispiel`.

---

## Funktionsübersicht

- **Sidebar-Navigation:** Startseite, Rezepte, Wochenplan, Favoriten, Kategorien, Suche, Über
- **Rezepte-Seite:** Kachel-Ansicht mit Suche, Sortierung, Kategorie-Tabs
- **Detailansicht:** Zutaten (skaliert nach Portionen), Zubereitungsschritte, geschätzte Nährwerte
- **Favoriten:** Herz-Symbol zum Merken
- **Wochenplan:** Angebote bei Aldi/Lidl prüfen, Top-Rezepte vorschlagen, Einkaufsliste erstellen,
  "Andere vorschlagen"-Button für neue Auswahl ohne erneute Angebotssuche
- **Ernährungsweise-Filter:** Alles / Vegetarisch / Vegan / Pescetarisch
- **Portionen-Umrechnung:** Mengen werden automatisch hoch-/runtergerechnet, Stückgut wird aufgerundet

## Wichtige Hinweise

- Die Angebotsdaten stammen von einer **inoffiziellen** Schnittstelle von marktguru.de.
  Sie kann sich jederzeit ändern. Falls keine Angebote mehr gefunden werden, müssen die
  Keys in den Secrets (bzw. im Code als Fallback) erneuert werden
  (Entwicklertools im Browser auf marktguru.de, Tab "Netzwerk").
- Nur für private, nicht-kommerzielle Nutzung gedacht.
- Die Nährwertangaben sind grobe Schätzungen, keine Laborwerte.

## Nächste Schritte

- KI-Agenten für neue Rezepte, Makroberechnung und Bildgenerierung (in Planung)
- Automatischer wöchentlicher Lauf
