#!/usr/bin/env python3
"""
EinfachmitTimo – FINALES DESIGN
Großer Banner, kompakte Cards, modernes Layout
"""

import json
import math
import requests
import streamlit as st
from pathlib import Path
from PIL import Image

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
KATEGORIEN = ["Frühstück", "Mittagessen", "Abendessen", "Soßen", "Dessert"]

# ============================================================
#  STYLING – Kompakt, Modern, Sauber
# ============================================================
st.set_page_config(page_title="EinfachmitTimo", page_icon="🍽️", layout="wide")

st.markdown("""
<style>
    * { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    
    .stApp { 
        background: #faf8f5;
        color: #2c2417;
        padding: 0 !important;
    }
    
    .main { padding: 0 !important; }
    [data-testid="stAppViewContainer"] { padding: 0 !important; }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #4a3f34 0%, #3d332a 100%);
        border-right: 2px solid #d4a574;
    }
    section[data-testid="stSidebar"] * { color: #f5f1ed !important; }
    
    /* Banner - GROSS */
    .banner-hero {
        background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%);
        padding: 32px 24px; border-radius: 0;
        text-align: center; color: #2c2417;
        margin-bottom: 32px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .banner-hero-title { 
        font-size: 40px; font-weight: 900; margin: 0; letter-spacing: 0.5px;
    }
    
    .banner-hero-sub { 
        font-size: 14px; letter-spacing: 2px; margin: 6px 0 0 0; opacity: 0.95;
        font-weight: 500;
    }
    
    /* Sidebar */
    .brand { text-align: center; padding: 14px 0; border-bottom: 1px solid #5a4d42; }
    .brand-title { font-size: 18px; font-weight: 800; color: #d4a574; margin: 0; }
    .brand-sub { font-size: 9px; letter-spacing: 1px; color: #a89080; margin: 3px 0 0 0; }
    
    .portrait-container { text-align: center; padding: 14px 0; }
    .portrait-img { width: 90px; height: 90px; border-radius: 50%; border: 3px solid #d4a574; object-fit: cover; }
    
    div[role="radiogroup"] > label {
        display: block; padding: 9px 12px; margin-bottom: 4px;
        border-radius: 8px; cursor: pointer; background-color: #5a4d42;
        color: #f5f1ed; font-size: 13px;
    }
    div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%);
        color: #2c2417 !important; font-weight: 600;
    }
    
    /* Cards für Startseite */
    .card-main {
        background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%);
        border-radius: 12px; padding: 24px; text-align: center;
        color: #2c2417; cursor: pointer; transition: all 0.3s;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .card-main:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    }
    
    .card-main-icon { font-size: 36px; margin-bottom: 12px; }
    .card-main-title { font-size: 18px; font-weight: 700; margin: 0; }
    
    /* Rezept-Karten */
    .recipe-card {
        background: white; border-radius: 12px; overflow: hidden;
        border: 1px solid #e0d5ca; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: all 0.3s; cursor: pointer;
    }
    
    .recipe-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(212, 165, 116, 0.2);
    }
    
    .recipe-card-img {
        font-size: 60px; text-align: center; padding: 32px 0;
        background: linear-gradient(135deg, #f5e6d3 0%, #ede3d6 100%);
        min-height: 150px; display: flex; align-items: center; justify-content: center;
    }
    
    .recipe-card-body { padding: 14px; }
    .recipe-card-title { font-size: 15px; font-weight: 700; margin-bottom: 8px; color: #2c2417; }
    
    .badge {
        display: inline-block; font-size: 10px; padding: 3px 8px;
        border-radius: 16px; margin-right: 4px; margin-bottom: 5px;
        font-weight: 600; white-space: nowrap;
    }
    
    .badge-time { background-color: #f5e6d3; color: #7a5f35; }
    .badge-Frühstück { background-color: #fef3e0; color: #c98f4c; }
    .badge-Mittagessen { background-color: #e8f5e9; color: #558b2f; }
    .badge-Abendessen { background-color: #e3f2fd; color: #1565c0; }
    .badge-Soßen { background-color: #fff3e0; color: #e65100; }
    .badge-Dessert { background-color: #f8e8d8; color: #b8651d; }
    .badge-diet { background-color: #f0e6d2; color: #6d5c47; font-size: 9px; }
    .badge-deal { background-color: #d4a574; color: #2c2417; font-weight: 700; }
    
    .stButton > button {
        border-radius: 10px; border: none;
        background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%);
        color: #2c2417; font-weight: 600; font-size: 14px;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #c98f4c 0%, #b87a2f 100%);
    }
    
    hr { border-color: #e0d5ca; margin: 20px 0; }
    h1, h2, h3 { color: #2c2417; }
</style>
""", unsafe_allow_html=True)


# ============================================================
#  DATEN LADEN
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


@st.cache_data(ttl=7200, show_spinner=False)
def suche_angebot(zutat: str, zip_code: str, retailers: tuple):
    params = {"as": "web", "limit": 5, "offset": 0, "q": zutat, "zipCode": zip_code}
    try:
        r = requests.get(API_URL, headers=HEADERS, params=params, timeout=8)
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
                break  # Nur erste Markt-Option
    if not treffer:
        return None
    return min(treffer, key=lambda t: t["preis"])


# ============================================================
#  SESSION STATE
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
            st.image(img, use_container_width=False, width=90)
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
            "Ernährungsweise", options=list(DIET_OPTIONEN.keys()), 
            index=list(DIET_OPTIONEN.keys()).index(ss["ernaehrungsweise"]),
        )


# ============================================================
#  HILFSFUNKTIONEN
# ============================================================
def angebot_fuer(name):
    return ss.get("angebot_je_zutat", {}).get(name)


def zeige_karte(rezept):
    st.markdown(f"""
    <div class="recipe-card">
        <div class="recipe-card-img">{rezept['icon']}</div>
        <div class="recipe-card-body">
            <div class="recipe-card-title">{rezept['name']}</div>
            <span class="badge badge-time">⏱ {rezept['time_min']}m</span>
            <span class="badge badge-{rezept['category']}">{rezept['category']}</span>
            <span class="badge badge-diet">{rezept['diet']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([3, 1])
    with c1:
        if st.button("Ansehen", key=f"view_{rezept['name']}", use_container_width=True):
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
    if not liste:
        st.info("Keine Rezepte gefunden.")
        return
    cols = st.columns(3, gap="large")
    for idx, rezept in enumerate(liste):
        with cols[idx % 3]:
            zeige_karte(rezept)


def zeige_detail(rezept):
    if st.button("← Zurück"):
        ss["selected_recipe"] = None
        st.rerun()
    
    st.markdown(f"## {rezept['icon']} {rezept['name']}")
    st.markdown(f"⏱ {rezept['time_min']} Min • {rezept['category']} • {rezept['difficulty']} • {rezept['diet']}")
    
    portionen = ss["portionen"]
    basis = rezept.get("base_servings", 4)
    faktor = portionen / basis

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown(f"### Zutaten *(für {portionen})*")
        for z in rezept["ingredients"]:
            name = zutat_name(z)
            if isinstance(z, dict):
                menge = skaliere_menge(z["amount"], z["unit"], faktor)
                mengen_text = formatiere_menge(menge, z["unit"])
            else:
                mengen_text = ""
            angebot = angebot_fuer(name)
            if angebot:
                st.markdown(f"- **{mengen_text} {name}** 🏷️ *{angebot['preis']}€ {angebot['haendler']}*")
            else:
                st.markdown(f"- {mengen_text} {name}")

    with col2:
        st.markdown("### Zubereitung")
        if rezept.get("steps"):
            for i, step in enumerate(rezept["steps"], start=1):
                st.markdown(f"**{i}.** {step}")

    st.divider()
    st.markdown("### Nährwerte *(pro Portion)*")
    n1, n2, n3, n4, n5 = st.columns(5)
    n1.metric("Kalorien", f"{rezept.get('kcal', '–')}")
    n2.metric("Eiweiß", f"{rezept.get('protein', '–')}g")
    n3.metric("KH", f"{rezept.get('carbs', '–')}g")
    n4.metric("Fett", f"{rezept.get('fett', '–')}g")
    n5.metric("Fasern", f"{rezept.get('ballaststoffe', '–')}g")


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
if ss["selected_recipe"] is not None:
    aktuelles = next((r for r in rezepte if r["name"] == ss["selected_recipe"]), None)
    if aktuelles:
        zeige_detail(aktuelles)
    else:
        ss["selected_recipe"] = None

elif ss["nav"] == "Startseite":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">🍽️ EinfachmitTimo</div><div class="banner-hero-sub">EINFACH GUTES ESSEN</div></div>', unsafe_allow_html=True)
    
    st.write("Dein Essensplaner mit Aldi- & Lidl-Angeboten. Wähle eine Option:")
    
    st.markdown("""
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
        <div style="background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%); border-radius: 12px; padding: 24px; text-align: center; color: #2c2417;">
            <div style="font-size: 36px; margin-bottom: 12px;">📖</div>
            <div style="font-size: 18px; font-weight: 700;">Rezepte</div>
        </div>
        <div style="background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%); border-radius: 12px; padding: 24px; text-align: center; color: #2c2417;">
            <div style="font-size: 36px; margin-bottom: 12px;">📋</div>
            <div style="font-size: 18px; font-weight: 700;">Wochenplan</div>
        </div>
        <div style="background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%); border-radius: 12px; padding: 24px; text-align: center; color: #2c2417;">
            <div style="font-size: 36px; margin-bottom: 12px;">❤️</div>
            <div style="font-size: 18px; font-weight: 700;">Favoriten</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3, gap="large")
    
    with c1:
        if st.button("Durchstöbern", key="btn_rezepte", use_container_width=True):
            ss["nav"] = "Rezepte"; st.rerun()
    
    with c2:
        if st.button("Erstellen", key="btn_plan", use_container_width=True):
            ss["nav"] = "Wochenplan"; st.rerun()
    
    with c3:
        if st.button("Ansehen", key="btn_fav", use_container_width=True):
            ss["nav"] = "Favoriten"; st.rerun()

elif ss["nav"] == "Rezepte":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">📖 Alle Rezepte</div></div>', unsafe_allow_html=True)
    
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
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">❤️ Deine Favoriten</div></div>', unsafe_allow_html=True)
    favoriten = [r for r in rezepte if r.get("favorite")]
    zeige_grid(favoriten)

elif ss["nav"] == "Kategorien":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">Kategorien</div></div>', unsafe_allow_html=True)
    cols = st.columns(len(KATEGORIEN), gap="large")
    for col, kat in zip(cols, KATEGORIEN):
        with col:
            anzahl = len([r for r in rezepte if r["category"] == kat])
            st.metric(kat, anzahl)
            if st.button(f"Anschauen", key=f"kat_{kat}", use_container_width=True):
                ss["nav"] = "Rezepte"
                st.rerun()

elif ss["nav"] == "Suche":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">🔍 Suche</div></div>', unsafe_allow_html=True)
    suchtext = st.text_input("Rezept oder Zutat suchen")
    if suchtext:
        ergebnisse = filter_und_suche(rezepte, "Alle", suchtext, ss["ernaehrungsweise"])
        st.write(f"**{len(ergebnisse)} Treffer**")
        zeige_grid(ergebnisse)

elif ss["nav"] == "Wochenplan":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">📋 Wochenplan</div></div>', unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5 = st.columns([0.8, 0.8, 1, 1, 1.5])
    with c1:
        anzahl = st.slider("Rezepte", 3, 15, 7, label_visibility="collapsed")
    with c2:
        ss["zip_code"] = st.text_input("PLZ", value=ss["zip_code"], label_visibility="collapsed")
    with c3:
        ss["wochenplan_choice"] = st.radio(
            "Woche:",
            ["diese_woche", "naechste_woche"],
            format_func=lambda x: "Diese" if x == "diese_woche" else "Nächste",
            label_visibility="collapsed"
        )
    with c4:
        ss["retailer_auswahl"] = st.multiselect(
            "Märkte:",
            options=["lidl", "aldi-sued", "aldi-nord"],
            default=ss["retailer_auswahl"],
            label_visibility="collapsed"
        )
    with c5:
        starten = st.button("🔍 Plan erstellen", type="primary", use_container_width=True)
    
    if starten:
        if not ss["retailer_auswahl"]:
            st.error("Mindestens einen Markt auswählen!")
        else:
            # Nur Top-Zutaten suchen (max 5 pro Rezept)
            alle_top_zutaten = set()
            for r in rezepte:
                top_zutaten = [zutat_name(z) for z in r["ingredients"][:5]]
                alle_top_zutaten.update(top_zutaten)
            
            alle_namen = sorted(alle_top_zutaten)
            fortschritt = st.progress(0, text="Suche Angebote...")
            angebot_je_zutat = {}
            for idx, name in enumerate(alle_namen):
                treffer = suche_angebot(name, ss["zip_code"], tuple(ss["retailer_auswahl"]))
                if treffer:
                    angebot_je_zutat[name] = treffer
                fortschritt.progress((idx + 1) / len(alle_namen), text=f"Suche ({idx+1}/{len(alle_namen)})...")
            fortschritt.empty()
            
            bewertung = []
            for rezept in rezepte:
                namen = [zutat_name(z) for z in rezept["ingredients"][:5]]
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
            
            wochen = "Diese Woche" if ss["wochenplan_choice"] == "diese_woche" else "Nächste Woche"
            st.subheader(f"Top {n} • {wochen} • {ss['portionen']} Portionen")
            
            if len(gefiltert) > n and st.button("🔀 Andere", use_container_width=True):
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
        st.info("Klick oben auf 'Plan erstellen' um zu starten")

elif ss["nav"] == "Über":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">Über EinfachmitTimo</div></div>', unsafe_allow_html=True)
    st.write("Dieser Essensplaner gleicht deine Rezeptsammlung mit aktuellen Aldi- & Lidl-Angeboten ab.")
    st.caption("Angebote via inoffizielle Marktguru-API (privat nur)")
