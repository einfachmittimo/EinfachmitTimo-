EinfachmitTimo – Design-Update

Dateien:
- app.py: aktualisierte Streamlit-App mit kompakter Startseite
- recipes.json: bestehende Rezeptdaten (unverändert)
- assets/recipes/*.jpg: 10 vorhandene Testbilder

Einspielen:
1. Die ZIP lokal entpacken.
2. app.py, recipes.json und den Ordner assets/recipes in denselben Projektordner deiner Streamlit-App übernehmen.
3. Vorhandene app.py ersetzen; recipes.json nur ersetzen, wenn du die mitgelieferte aktuelle Kopie nutzen möchtest.
4. Commit/Push in das Repository ausführen, aus dem Streamlit Cloud deployed wird.
5. App neu laden.

Hinweis: Das Update wurde mit py_compile auf Python-Syntax geprüft. Ein vollständiger Live-Test gegen Marktguru/Streamlit Cloud wurde nicht durchgeführt. Die Marktguru-Zugangsdaten müssen weiterhin als Streamlit Secrets konfiguriert sein.
