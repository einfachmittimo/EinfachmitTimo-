#!/usr/bin/env python3
"""
Essensplaner (Terminal-Version): Gleicht deine Rezepte mit aktuellen
Aldi/Lidl-Angeboten (über die inoffizielle Marktguru-API) ab und
erstellt Wochenplan + Einkaufsliste.

Tipp: Es gibt inzwischen auch eine Web-Oberfläche in app.py
("streamlit run app.py") – inklusive Hosting-Option, siehe README.md.
"""

import json
import requests
from pathlib import Path

ZIP_CODE = "89584"
RETAILERS = ["lidl", "aldi-sued"]
RECIPES_FILE = Path(__file__).parent / "recipes.json"

API_URL = "https://api.marktguru.de/api/v1/offers/search"
HEADERS = {
    "x-clientkey": "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90=",
    "x-apikey": "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE=",
}


def lade_rezepte():
    with open(RECIPES_FILE, encoding="utf-8") as f:
        return json.load(f)


def zutat_name(zutat):
    return zutat["name"] if isinstance(zutat, dict) else zutat


def suche_angebot(zutat: str):
    params = {"as": "web", "limit": 10, "offset": 0, "q": zutat, "zipCode": ZIP_CODE}
    try:
        r = requests.get(API_URL, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [Warnung] Abfrage für '{zutat}' fehlgeschlagen: {e}")
        return None

    treffer = []
    for result in data.get("results", []):
        preis = result.get("price")
        if preis is None:
            continue
        for adv in result.get("advertisers", []):
            if adv.get("uniqueName", "") in RETAILERS:
                treffer.append({"zutat": zutat, "beschreibung": result.get("description", ""),
                                 "preis": preis, "haendler": adv.get("name", "")})
    if not treffer:
        return None
    return min(treffer, key=lambda t: t["preis"])


def erstelle_plan():
    rezepte = lade_rezepte()
    alle_zutaten = sorted({zutat_name(z) for r in rezepte for z in r["ingredients"]})

    print(f"Prüfe {len(alle_zutaten)} Zutaten aus {len(rezepte)} Rezepten "
          f"auf Angebote bei {', '.join(RETAILERS)} (PLZ {ZIP_CODE})...\n")

    angebot_je_zutat = {}
    for zutat in alle_zutaten:
        treffer = suche_angebot(zutat)
        if treffer:
            angebot_je_zutat[zutat] = treffer

    bewertung = []
    for rezept in rezepte:
        namen = [zutat_name(z) for z in rezept["ingredients"]]
        treffer_namen = [n for n in namen if n in angebot_je_zutat]
        bewertung.append((rezept, treffer_namen))
    bewertung.sort(key=lambda x: len(x[1]), reverse=True)

    print("=" * 50)
    print("WOCHENPLAN-VORSCHLAG (sortiert nach Angebots-Treffern)")
    print("=" * 50)
    for rezept, treffer_namen in bewertung:
        print(f"\n🍽  {rezept['name']}  ({len(treffer_namen)}/{len(rezept['ingredients'])} Zutaten im Angebot)")
        for name in treffer_namen:
            angebot = angebot_je_zutat[name]
            print(f"    ✓ {angebot['zutat']}: {angebot['beschreibung']} "
                  f"– {angebot['preis']}€ bei {angebot['haendler']}")

    print("\n" + "=" * 50)
    print("EINKAUFSLISTE")
    print("=" * 50)
    for zutat in alle_zutaten:
        markierung = " (IM ANGEBOT)" if zutat in angebot_je_zutat else ""
        print(f"  [ ] {zutat}{markierung}")


if __name__ == "__main__":
    erstelle_plan()
