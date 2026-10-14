#!/usr/bin/env python3
"""
EinfachmitTimo – Essensplaner FINAL DESIGN
Warmes professionelles Theme, Banner, größere Kacheln, Wochenplan mit Auswahl.

Lokal starten:
    pip install streamlit requests pillow
    streamlit run app_final.py
"""

import json
import math
import requests
import streamlit as st
from pathlib import Path
from PIL import Image
from datetime import datetime, timedelta

# ---- Konfiguration ----
RECIPES_FILE = Path(__file__).parent / "recipes.json"
PORTRAIT_FILE = Path(__file__).parent / "timo_portrait.png"
API_URL = "https://api.marktguru.de/api/v1/offers/search"


def hole_marktguru_keys():
    try:
        return {
            "x-clientkey": st.secrets["marktguru"]["clientkey"],
            "x-apikey": st.secrets["marktguru"]["apikey"],
        }
    except Exception:
        return {
            "x-clientkey": "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90=",
            "x-apikey": "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE=",
        }


HEADERS = hole_marktguru_keys()

STUECK_EINHEITEN = {
    "Stück", "Bund", "Dose", "Dosen", "Kopf", "Laib", "Packung", "Gläser",
    "Glas", "Würfel", "TL", "EL", "Scheiben", "Stangen", "Filet", "Filets",
}
DIET_OPTIONEN = {
    "Alles": {"vegan", "vegetarisch", "fisch", "fleisch"},
    "Vegetarisch": {"vegan", "vegetarisch"},
    "Vegan": {"vegan"},
    "Pescetarisch": {"vegan", "vegetarisch", "fisch"},
}
KATEGORIEN = ["Frühstück", "Mittagessen", "Abendessen", "Soßen"]

# ============================================================
#  STYLING – Professionelles warmes Design
# ============================================================
st.set_page_config(page_title="EinfachmitTimo", page_icon="🍽️", layout="wide")

st.markdown("""
<style>
    * { font-family: 'Segoe UI', Tahoma, sans-serif; }
    
    .stApp { 
        background: linear-gradient(to bottom, #faf8f5, #f5f1ed);
        color: #2c2417;
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #4a3f34 0%, #3d332a 100%);
        border-right: 3px solid #d4a574;
    }
    
    section[data-testid="stSidebar"] * { color: #f5f1ed !important; }
    
    /* Header Banner */
    .banner {
        background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%);
        padding: 20px; border-radius: 12px; margin-bottom: 24px;
        text-align: center; color: #2c2417; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .banner-title { font-size: 32px; font-weight: 800; margin: 0; }
    .banner-sub { font-size: 13px; letter-spacing: 1.5px; opacity: 0.9; margin: 4px 0 0 0; }
    
    /* Sidebar */
    .brand { text-align: center; padding: 16px 0; border-bottom: 1px solid #5a4d42; }
    .brand-title { font-size: 20px; font-weight: 800; color: #d4a574; margin: 0; }
    .brand-sub { font-size: 10px; letter-spacing: 1px; color: #a89080; margin: 4px 0 0 0; }
    
    .portrait-container { text-align: center; padding: 16px 0; }
    .portrait-img { width: 100px; height: 100px; border-radius: 50%; border: 3px solid #d4a574; object-fit: cover; }
    
    div[role="radiogroup"] > label {
        display: block; padding: 10px 14px; margin-bottom: 5px;
        border-radius: 8px; cursor: pointer; background-color: #5a4d42;
        color: #f5f1ed; font-size: 14px;
    }
    div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%);
        color: #2c2417 !important; font-weight: 600;
    }
    
    /* Rezept-Karten */
    .recipe-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 18px; }
    
    .recipe-card {
        background: white; border-radius: 14px; overflow: hidden;
        border: 1px solid #e0d5ca; box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        transition: all 0.3s ease; cursor: pointer;
    }
    
    .recipe-card:hover {
        transform: translateY(-4px); box-shadow: 0 6px 20px rgba(212, 165, 116, 0.25);
    }
    
    .recipe-card-img {
        font-size: 70px; text-align: center; padding: 40px 0;
        background: linear-gradient(135deg, #f5e6d3 0%, #ede3d6 100%);
        min-height: 180px; display: flex; align-items: center; justify-content: center;
    }
    
    .recipe-card-body { padding: 16px; }
    .recipe-card-title { font-size: 16px; font-weight: 700; margin-bottom: 10px; color: #2c2417; }
    
    .badge {
        display: inline-block; font-size: 11px; padding: 4px 10px;
        border-radius: 18px; margin-right: 6px; margin-bottom: 6px;
        font-weight: 600; white-space: nowrap;
    }
    
    .badge-time { background-color: #f5e6d3; color: #7a5f35; }
    .badge-Frühstück { background-color: #fef3e0; color: #c98f4c; }
    .badge-Mittagessen { background-color: #e8f5e9; color: #558b2f; }
    .badge-Abendessen { background-color: #e3f2fd; color: #1565c0; }
    .badge-Soßen { background-color: #fff3e0; color: #e65100; }
    .badge-diet { background-color: #f0e6d2; color: #6d5c47; font-size: 10px; }
    .badge-deal { background-color: #d4a574; color: #2c2417; font-weight: 700; }
    
    /* Detail-Seite */
    .detail-container { background: white; border-radius: 14px; padding: 24px; border: 1px solid #e0d5ca; }
    .detail-header { display: flex; gap: 24px; margin-bottom: 24px; }
    .detail-icon { font-size: 100px; min-width: 120px; text-align: center; }
    .detail-info h2 { margin: 0 0 12px 0; font-size: 28px; }
    
    /* Buttons */
    .stButton > button {
        border-radius: 10px; border: none;
        background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%);
        color: #2c2417; font-weight: 600; padding: 10px 20px;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #c98f4c 0%, #b87a2f 100%);
        transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    hr { border-color: #e0d5ca; margin: 24px 0; }
    h1, h2, h3 { color: #2c2417; }
</style>
""", unsafe_allow_html=True)


# ============================================================
#  Daten laden
# ============================================================
def lade_rezepte():
    with open(RECIPES_FILE, encoding="utf-8") as f:
        rezepte = json.load(f)
    for r in rezepte:
        r.setdefault("favorite", False)
        r.setdefault("category", "Mittagessen")
        r.setdefault("icon", "🍽️")
        r.setdefault("time_min", 20)
        r.setdefault("difficulty", "Einfach")
        r.setdefault("diet", "vegetarisch")
        r.setdefault("steps", [])
    return rezepte


def speichere_rezepte(rezepte):
    with open(RECIPES_FILE, "w", encoding="utf-8") as f:
        json.dump(rezepte, f, ensure_ascii=False, indent=2)


def zutat_name(z):
    return z["name"] if isinstance(z, dict) else z


def skaliere_menge(amount, unit, faktor):
    skaliert = amount * faktor
    if unit in STUECK_EINHEITEN:
        return max(1, math.ceil(skaliert))
    if skaliert < 10:
        return round(skaliert, 1)
    return round(skaliert / 10) * 10


def formatiere_menge(amount, unit):
    if isinstance(amount, float) and amount.is_integer():
        amount = int(amount)
    return f"{amount} {unit}"


@st.cache_data(ttl=3600, show_spinner=False)
def suche_angebot(zutat: str, zip_code: str, retailers: tuple):
    params = {"as": "web", "limit": 10, "offset": 0, "q": zutat, "zipCode": zip_code}
    try:
        r = requests.get(API_URL, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None
    treffer = []
    for result in data.get("results", []):
        preis = result.get("price")
        if preis is None:
            continue
        for adv in result.get("advertisers", []):
            if adv.get("uniqueName", "") in retailers:
                treffer.append({"beschreibung": result.get("description", ""),
                                 "preis": preis, "haendler": adv.get("name", "")})
    if not treffer:
        return None
    return min(treffer, key=lambda t: t["preis"])


# ============================================================
#  Session State
# ============================================================
ss = st.session_state
ss.setdefault("nav", "Startseite")
ss.setdefault("selected_recipe", None)
ss.setdefault("zip_code", "89584")
ss.setdefault("retailer_auswahl", ["lidl", "aldi-sued"])
ss.setdefault("portionen", 4)
ss.setdefault("ernaehrungsweise", "Alles")
ss.setdefault("wochenplan_choice", "diese_woche")

rezepte = lade_rezepte()


# ============================================================
#  SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-title">🍽️ EinfachmitTimo</div>'
        '<div class="brand-sub">EINFACH GUTES ESSEN</div></div>',
        unsafe_allow_html=True,
    )
    
    if PORTRAIT_FILE.exists():
        try:
            img = Image.open(PORTRAIT_FILE)
            st.markdown('<div class="portrait-container">', unsafe_allow_html=True)
            st.image(img, use_container_width=False, width=100)
            st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            pass
    
    nav_optionen = ["Startseite", "Rezepte", "Wochenplan", "Favoriten", "Kategorien", "Suche", "Über"]
    ss["nav"] = st.radio("Navigation", nav_optionen, index=nav_optionen.index(ss["nav"]), label_visibility="collapsed")

    st.divider()
    with st.expander("⚙️ Einstellungen"):
        ss["zip_code"] = st.text_input("PLZ", value=ss["zip_code"])
        ss["retailer_auswahl"] = st.multiselect(
            "Märkte", options=["lidl", "aldi-sued", "aldi-nord"], default=ss["retailer_auswahl"]
        )
        ss["portionen"] = st.number_input("Portionen", min_value=1, max_value=12, value=ss["portionen"])
        ss["ernaehrungsweise"] = st.selectbox(
            "Ernährungsweise", options=list(DIET_OPTIONEN.keys()), index=list(DIET_OPTIONEN.keys()).index(ss["ernaehrungsweise"]),
        )


# ============================================================
#  HILFSFUNKTIONEN
# ============================================================
def angebot_fuer(name):
    return ss.get("angebot_je_zutat", {}).get(name)


def zeige_karte(rezept):
    """Karte für Grid-Anzeige"""
    st.markdown(f"""
    <div class="recipe-card">
        <div class="recipe-card-img">{rezept['icon']}</div>
        <div class="recipe-card-body">
            <div class="recipe-card-title">{rezept['name']}</div>
            <span class="badge badge-time">⏱ {rezept['time_min']} Min</span>
            <span class="badge badge-{rezept['category']}">{rezept['category']}</span>
            <span class="badge badge-diet">{rezept['diet']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([3, 1])
    with c1:
        if st.button("Ansehen", key=f"ansehen_{rezept['name']}", use_container_width=True):
            ss["selected_recipe"] = rezept["name"]
            st.rerun()
    with c2:
        herz = "❤️" if rezept.get("favorite") else "🤍"
        if st.button(herz, key=f"fav_{rezept['name']}", use_container_width=True):
            for r in rezepte:
                if r["name"] == rezept["name"]:
                    r["favorite"] = not r.get("favorite", False)
            speichere_rezepte(rezepte)
            st.rerun()


def zeige_grid(liste):
    """Grid-Layout für Rezepte"""
    if not liste:
        st.info("Keine Rezepte gefunden.")
        return
    
    cols = st.columns(3, gap="large")
    for idx, rezept in enumerate(liste):
        with cols[idx % 3]:
            zeige_karte(rezept)


def zeige_detail(rezept):
    """Detail-Ansicht mit großem Layout"""
    if st.button("← Zurück"):
        ss["selected_recipe"] = None
        st.rerun()
    
    st.markdown(f"""
    <div class="detail-container">
        <div class="detail-header">
            <div class="detail-icon">{rezept['icon']}</div>
            <div class="detail-info">
                <h2 style="margin-bottom: 12px;">{rezept['name']}</h2>
                <span class="badge badge-time">⏱ {rezept['time_min']} Min</span>
                <span class="badge badge-{rezept['category']}">{rezept['category']}</span>
                <span class="badge badge-diet">{rezept['difficulty']}</span>
                <span class="badge badge-diet">{rezept['diet']}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    portionen = ss["portionen"]
    basis = rezept.get("base_servings", 4)
    faktor = portionen / basis

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown(f"### Zutaten *(für {portionen} Portionen)*")
        for z in rezept["ingredients"]:
            name = zutat_name(z)
            if isinstance(z, dict):
                menge = skaliere_menge(z["amount"], z["unit"], faktor)
                mengen_text = formatiere_menge(menge, z["unit"])
            else:
                mengen_text = ""
            angebot = angebot_fuer(name)
            if angebot:
                st.markdown(
                    f"- **{mengen_text} {name}** 🏷️ *{angebot['preis']}€ {angebot['haendler']}*"
                )
            else:
                st.markdown(f"- {mengen_text} {name}")

    with col2:
        st.markdown("### Zubereitung")
        if rezept.get("steps"):
            for i, step in enumerate(rezept["steps"], start=1):
                st.markdown(f"**{i}.** {step}")
        else:
            st.caption("Keine Schritte hinterlegt.")

    st.divider()
    st.markdown("### Nährwerte pro Portion *(geschätzt)*")
    n1, n2, n3, n4, n5 = st.columns(5)
    n1.metric("🔥 Kalorien", f"{rezept.get('kcal', '–')} kcal")
    n2.metric("🥩 Eiweiß", f"{rezept.get('protein', '–')} g")
    n3.metric("🍞 Kohlenhydrate", f"{rezept.get('carbs', '–')} g")
    n4.metric("🥑 Fett", f"{rezept.get('fett', '–')} g")
    n5.metric("🌿 Ballaststoffe", f"{rezept.get('ballaststoffe', '–')} g")


def filter_und_suche(liste, kategorie, suchtext, diet_filter):
    erlaubte_diets = DIET_OPTIONEN[diet_filter]
    ergebnis = liste
    if kategorie != "Alle":
        ergebnis = [r for r in ergebnis if r["category"] == kategorie]
    if suchtext:
        s = suchtext.lower()
        ergebnis = [r for r in ergebnis if s in r["name"].lower()
                    or any(s in zutat_name(z).lower() for z in r["ingredients"])]
    ergebnis = [r for r in ergebnis if r.get("diet", "vegetarisch") in erlaubte_diets]
    return ergebnis


# ============================================================
#  SEITEN
# ============================================================

# Detail-Ansicht priorisiert
if ss["selected_recipe"] is not None:
    aktuelles = next((r for r in rezepte if r["name"] == ss["selected_recipe"]), None)
    if aktuelles:
        zeige_detail(aktuelles)
    else:
        ss["selected_recipe"] = None

elif ss["nav"] == "Startseite":
    st.markdown('<div class="banner"><div class="banner-title">🍽️ EinfachmitTimo</div><div class="banner-sub">EINFACH GUTES ESSEN</div></div>', unsafe_allow_html=True)
    st.markdown("### Willkommen!")
    st.write("Dein Essensplaner mit aktuellen Aldi- & Lidl-Angeboten. Wähle eine Option:")
    
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        st.markdown("**📖 Rezepte**")
        if st.button("Durchstöbern", key="btn_rezepte", use_container_width=True):
            ss["nav"] = "Rezepte"; st.rerun()
    with c2:
        st.markdown("**📋 Wochenplan**")
        if st.button("Erstellen", key="btn_plan", use_container_width=True):
            ss["nav"] = "Wochenplan"; st.rerun()
    with c3:
        st.markdown("**❤️ Favoriten**")
        if st.button("Ansehen", key="btn_fav", use_container_width=True):
            ss["nav"] = "Favoriten"; st.rerun()

elif ss["nav"] == "Rezepte":
    st.markdown('<div class="banner"><div class="banner-title">Alle Rezepte</div></div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns([3, 1])
    with c1:
        suchtext = st.text_input("🔍 Suchen...", label_visibility="collapsed", placeholder="🔍 Nach Rezepten suchen...")
    with c2:
        sort = st.selectbox("Sortierung", ["Name", "Zeit", "Kalorien"], label_visibility="collapsed")
    
    tabs = st.tabs(["Alle"] + KATEGORIEN)
    for tab, kat in zip(tabs, ["Alle"] + KATEGORIEN):
        with tab:
            gefiltert = filter_und_suche(rezepte, kat, suchtext, ss["ernaehrungsweise"])
            if sort == "Name":
                gefiltert = sorted(gefiltert, key=lambda r: r["name"])
            elif sort == "Zeit":
                gefiltert = sorted(gefiltert, key=lambda r: r["time_min"])
            else:
                gefiltert = sorted(gefiltert, key=lambda r: r.get("kcal", 0))
            zeige_grid(gefiltert)

elif ss["nav"] == "Favoriten":
    st.markdown('<div class="banner"><div class="banner-title">❤️ Deine Favoriten</div></div>', unsafe_allow_html=True)
    favoriten = [r for r in rezepte if r.get("favorite")]
    zeige_grid(favoriten)

elif ss["nav"] == "Kategorien":
    st.markdown('<div class="banner"><div class="banner-title">Kategorien</div></div>', unsafe_allow_html=True)
    cols = st.columns(4, gap="large")
    for col, kat in zip(cols, KATEGORIEN):
        with col:
            anzahl = len([r for r in rezepte if r["category"] == kat])
            st.metric(kat, anzahl)
            if st.button(f"Anschauen", key=f"kat_{kat}", use_container_width=True):
                ss["nav"] = "Rezepte"
                st.rerun()

elif ss["nav"] == "Suche":
    st.markdown('<div class="banner"><div class="banner-title">🔍 Suche</div></div>', unsafe_allow_html=True)
    suchtext = st.text_input("Rezept oder Zutat suchen")
    if suchtext:
        ergebnisse = filter_und_suche(rezepte, "Alle", suchtext, ss["ernaehrungsweise"])
        st.write(f"**{len(ergebnisse)} Treffer**")
        zeige_grid(ergebnisse)

elif ss["nav"] == "Wochenplan":
    st.markdown('<div class="banner"><div class="banner-title">📋 Wochenplan</div></div>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        anzahl = st.slider("Rezepte", 3, 15, 7)
    with c2:
        ss["wochenplan_choice"] = st.radio(
            "Angebote für:",
            ["diese_woche", "naechste_woche"],
            format_func=lambda x: "Diese Woche" if x == "diese_woche" else "Nächste Woche",
            label_visibility="collapsed"
        )
    with c3:
        starten = st.button("🔍 Plan erstellen", type="primary", use_container_width=True)
    
    if starten:
        if not ss["retailer_auswahl"]:
            st.error("Märkte in Einstellungen auswählen!")
        else:
            alle_namen = sorted({zutat_name(z) for r in rezepte for z in r["ingredients"]})
            fortschritt = st.progress(0, text="Angebote suchen...")
            angebot_je_zutat = {}
            for idx, name in enumerate(alle_namen):
                treffer = suche_angebot(name, ss["zip_code"], tuple(ss["retailer_auswahl"]))
                if treffer:
                    angebot_je_zutat[name] = treffer
                fortschritt.progress((idx + 1) / len(alle_namen), text=f"Suche...")
            fortschritt.empty()
            
            bewertung = []
            for rezept in rezepte:
                namen = [zutat_name(z) for z in rezept["ingredients"]]
                treffer_namen = [n for n in namen if n in angebot_je_zutat]
                bewertung.append((rezept, treffer_namen))
            bewertung.sort(key=lambda x: len(x[1]), reverse=True)
            
            ss["bewertung"] = bewertung
            ss["angebot_je_zutat"] = angebot_je_zutat
            ss["offset"] = 0

    if "bewertung" in ss:
        erlaubte_diets = DIET_OPTIONEN[ss["ernaehrungsweise"]]
        gefiltert = [(r, t) for r, t in ss["bewertung"] if r.get("diet", "vegetarisch") in erlaubte_diets]
        
        if not gefiltert:
            st.warning("Keine Rezepte für diese Ernährungsweise!")
        else:
            offset = ss.get("offset", 0) % len(gefiltert)
            n = min(anzahl, len(gefiltert))
            auswahl = [gefiltert[(offset + i) % len(gefiltert)] for i in range(n)]
            
            wochen_text = "Diese Woche" if ss["wochenplan_choice"] == "diese_woche" else "Nächste Woche"
            st.subheader(f"Top {n} Rezepte · {wochen_text} · {ss['portionen']} Portionen")
            
            if len(gefiltert) > n and st.button("🔀 Andere vorschlagen", use_container_width=True):
                ss["offset"] = offset + n
                st.rerun()
            
            zeige_grid([r for r, _ in auswahl])
            
            st.divider()
            st.markdown("### 🛒 Einkaufsliste")
            summe = {}
            for rezept, _ in auswahl:
                basis = rezept.get("base_servings", 4)
                faktor = ss["portionen"] / basis
                for z in rezept["ingredients"]:
                    name = zutat_name(z)
                    if isinstance(z, dict):
                        menge = z["amount"] * faktor
                        unit = z["unit"]
                        if name in summe and summe[name]["unit"] == unit:
                            summe[name]["amount"] += menge
                        else:
                            summe[name] = {"amount": menge, "unit": unit}
            
            cols = st.columns(3)
            for idx, name in enumerate(sorted(summe.keys())):
                info = summe[name]
                gerundet = skaliere_menge(info["amount"], info["unit"], 1)
                mengen_text = formatiere_menge(gerundet, info["unit"])
                im_angebot = "🏷️" if name in ss["angebot_je_zutat"] else ""
                cols[idx % 3].checkbox(f"{mengen_text} {name} {im_angebot}", key=f"item_{name}")
    else:
        st.info("Klick oben auf 'Plan erstellen'")

elif ss["nav"] == "Über":
    st.markdown('<div class="banner"><div class="banner-title">Über EinfachmitTimo</div></div>', unsafe_allow_html=True)
    st.write(
        "Dieser Essensplaner gleicht deine Rezeptsammlung mit aktuellen "
        "Aldi- & Lidl-Angeboten ab und schlägt passende Gerichte vor."
    )
    st.caption("Angebote via inoffizielle Marktguru-API (privat nur)")
