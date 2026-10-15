#!/usr/bin/env python3
"""
EinfachmitTimo – OPTIMIERT
Workflow: Angebote → Plan (nicht Plan → Angebote)
Max 40 Zutaten, schnelles Caching, ChatGPT-Optimierungen
"""

import json
import math
import requests
import streamlit as st
from pathlib import Path
from PIL import Image
from datetime import datetime, timedelta, date

RECIPES_FILE = Path(__file__).parent / "recipes.json"
PORTRAIT_FILE = Path(__file__).parent / "timo_portrait.png"
API_URL = "https://api.marktguru.de/api/v1/offers/search"

DIET_OPTIONEN = {
    "Alles": {"vegan", "vegetarisch", "fisch", "fleisch"},
    "Vegetarisch": {"vegan", "vegetarisch"},
    "Vegan": {"vegan"},
    "Pescetarisch": {"vegan", "vegetarisch", "fisch"},
}
KATEGORIEN = ["Frühstück", "Mittagessen", "Abendessen", "Soßen", "Dessert"]

st.set_page_config(page_title="EinfachmitTimo", page_icon="🍽️", layout="wide")

st.markdown("""
<style>
    * { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    .stApp { background: #faf8f5; color: #2c2417; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #4a3f34 0%, #3d332a 100%); }
    section[data-testid="stSidebar"] * { color: #f5f1ed !important; }
    .banner-hero {
        background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%);
        padding: 32px 24px; border-radius: 0; text-align: center;
        color: #2c2417; margin-bottom: 24px;
    }
    .banner-hero-title { font-size: 40px; font-weight: 900; margin: 0; }
    .banner-hero-sub { font-size: 14px; letter-spacing: 2px; margin: 6px 0 0 0; }
    .recipe-card {
        background: white; border-radius: 12px; border: 1px solid #e0d5ca;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); transition: all 0.3s;
    }
    .recipe-card:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(212, 165, 116, 0.2); }
    .recipe-card-img {
        font-size: 60px; text-align: center; padding: 32px 0;
        background: linear-gradient(135deg, #f5e6d3 0%, #ede3d6 100%);
        min-height: 150px;
    }
    .stButton > button {
        border-radius: 10px; border: none;
        background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%);
        color: #2c2417; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


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


def get_week_dates(wochenplan_choice):
    """Berechnet Start und End-Datum für diese oder nächste Woche"""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    
    if wochenplan_choice == "diese_woche":
        start = monday
        end = monday + timedelta(days=6)
    else:  # naechste_woche
        start = monday + timedelta(days=7)
        end = start + timedelta(days=6)
    
    return start, end


@st.cache_data(ttl=900, show_spinner=False)
def suche_angebot(zutat: str, plz: str, markt: str):
    """Sucht ein Angebot bei einem bestimmten Markt"""
    params = {"as": "web", "limit": 5, "offset": 0, "q": zutat, "zipCode": plz}
    try:
        r = requests.get(API_URL, headers=HEADERS, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None
    
    markt_map = {
        "lidl": "lidl",
        "aldi-sued": "aldi-sued",
        "aldi-nord": "aldi-nord",
        "edeka": "edeka",
        "rewe": "rewe",
        "netto": "netto",
        "norma": "norma",
    }
    target = markt_map.get(markt, markt)
    
    for result in data.get("results", []):
        preis = result.get("price")
        if preis is None:
            continue
        for adv in result.get("advertisers", []):
            if adv.get("uniqueName", "") == target:
                return {
                    "beschreibung": result.get("description", ""),
                    "preis": preis,
                    "haendler": adv.get("name", markt),
                }
    return None


# ============================================================
#  SESSION STATE
# ============================================================
ss = st.session_state
ss.setdefault("nav", "Startseite")
ss.setdefault("selected_recipe", None)
ss.setdefault("zip_code", "89584")
ss.setdefault("markt", "lidl")
ss.setdefault("portionen", 4)
ss.setdefault("ernaehrungsweise", "Alles")
ss.setdefault("wochenplan_choice", "diese_woche")
ss.setdefault("angebote", {})  # Gefundene Angebote
ss.setdefault("wochenplan", {})  # Generierter Plan

rezepte = lade_rezepte()


# ============================================================
#  SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown(
        '<div style="text-align: center; padding: 16px 0; border-bottom: 1px solid #5a4d42;">'
        '<div style="font-size: 18px; font-weight: 800; color: #d4a574; margin: 0;">🍽️ EinfachmitTimo</div>'
        '<div style="font-size: 9px; letter-spacing: 1px; color: #a89080; margin: 3px 0 0 0;">EINFACH GUTES ESSEN</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    
    if PORTRAIT_FILE.exists():
        try:
            img = Image.open(PORTRAIT_FILE)
            st.markdown('<div style="text-align: center; padding: 14px 0;">', unsafe_allow_html=True)
            st.image(img, use_container_width=False, width=90)
            st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            pass
    
    nav_optionen = ["Startseite", "Rezepte", "Wochenplan", "Favoriten", "Kategorien", "Über"]
    ss["nav"] = st.radio("Navigation", nav_optionen, index=nav_optionen.index(ss["nav"]), label_visibility="collapsed")

    st.divider()
    with st.expander("⚙️ Einstellungen"):
        ss["zip_code"] = st.text_input("PLZ", value=ss["zip_code"])
        markt_optionen = ["lidl", "aldi-sued", "aldi-nord", "edeka", "rewe", "netto", "norma"]
        ss["markt"] = st.selectbox("Markt", markt_optionen, index=markt_optionen.index(ss["markt"]) if ss["markt"] in markt_optionen else 0)
        ss["portionen"] = st.number_input("Portionen", min_value=1, max_value=12, value=ss["portionen"])
        ss["ernaehrungsweise"] = st.selectbox("Ernährungsweise", list(DIET_OPTIONEN.keys()), index=list(DIET_OPTIONEN.keys()).index(ss["ernaehrungsweise"]))


# ============================================================
#  SEITEN
# ============================================================

if ss["nav"] == "Startseite":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">🍽️ EinfachmitTimo</div><div class="banner-hero-sub">EINFACH GUTES ESSEN</div></div>', unsafe_allow_html=True)
    st.write("Dein Essensplaner mit Aldi- & Lidl-Angeboten. Wähle eine Option:")
    
    c1, c2, c3 = st.columns(3, gap="medium")
    
    with c1:
        st.markdown('<div style="background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%); border-radius: 12px; padding: 20px; text-align: center; color: #2c2417; margin-bottom: 10px;"><div style="font-size: 36px; margin-bottom: 10px;">📖</div><div style="font-size: 16px; font-weight: 700;">Rezepte</div></div>', unsafe_allow_html=True)
        if st.button("Durchstöbern", key="btn_rezepte", use_container_width=True):
            ss["nav"] = "Rezepte"; st.rerun()
    
    with c2:
        st.markdown('<div style="background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%); border-radius: 12px; padding: 20px; text-align: center; color: #2c2417; margin-bottom: 10px;"><div style="font-size: 36px; margin-bottom: 10px;">📋</div><div style="font-size: 16px; font-weight: 700;">Wochenplan</div></div>', unsafe_allow_html=True)
        if st.button("Erstellen", key="btn_plan", use_container_width=True):
            ss["nav"] = "Wochenplan"; st.rerun()
    
    with c3:
        st.markdown('<div style="background: linear-gradient(135deg, #d4a574 0%, #c98f4c 100%); border-radius: 12px; padding: 20px; text-align: center; color: #2c2417; margin-bottom: 10px;"><div style="font-size: 36px; margin-bottom: 10px;">❤️</div><div style="font-size: 16px; font-weight: 700;">Favoriten</div></div>', unsafe_allow_html=True)
        if st.button("Ansehen", key="btn_fav", use_container_width=True):
            ss["nav"] = "Favoriten"; st.rerun()

elif ss["nav"] == "Rezepte":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">📖 Alle Rezepte</div></div>', unsafe_allow_html=True)
    
    suchtext = st.text_input("🔍 Suchen...", placeholder="Nach Rezepten suchen...")
    
    erlaubte_diets = DIET_OPTIONEN[ss["ernaehrungsweise"]]
    gefiltert = rezepte
    
    if suchtext:
        s = suchtext.lower()
        gefiltert = [r for r in gefiltert if s in r["name"].lower()
                    or any(s in zutat_name(z).lower() for z in r.get("ingredients", []))]
    
    gefiltert = [r for r in gefiltert if r.get("diet", "vegetarisch") in erlaubte_diets]
    
    tabs = st.tabs(["Alle"] + KATEGORIEN)
    for tab, kat in zip(tabs, ["Alle"] + KATEGORIEN):
        with tab:
            if kat != "Alle":
                kat_rezepte = [r for r in gefiltert if r["category"] == kat]
            else:
                kat_rezepte = gefiltert
            
            if kat_rezepte:
                cols = st.columns(3, gap="large")
                for idx, rezept in enumerate(kat_rezepte):
                    with cols[idx % 3]:
                        st.markdown(f'<div class="recipe-card"><div class="recipe-card-img">{rezept["icon"]}</div><div style="padding: 14px;"><div style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">{rezept["name"]}</div><span style="display: inline-block; background: #f5e6d3; color: #7a5f35; font-size: 10px; padding: 3px 8px; border-radius: 16px; margin-right: 4px;">⏱ {rezept["time_min"]}m</span><span style="display: inline-block; background: #f0e6d2; color: #6d5c47; font-size: 10px; padding: 3px 8px; border-radius: 16px;">{rezept["diet"]}</span></div></div>', unsafe_allow_html=True)
                        
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
            else:
                st.info("Keine Rezepte gefunden.")

elif ss["nav"] == "Wochenplan":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">🛒 Supermarkt Angebote</div></div>', unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns([1, 1, 1.5, 1.5])
    with c1:
        ss["zip_code"] = st.text_input("PLZ", value=ss["zip_code"], label_visibility="collapsed")
    with c2:
        markt_optionen = ["lidl", "aldi-sued", "aldi-nord", "edeka", "rewe", "netto", "norma"]
        ss["markt"] = st.selectbox("Markt", markt_optionen, index=markt_optionen.index(ss["markt"]) if ss["markt"] in markt_optionen else 0, label_visibility="collapsed")
    with c3:
        ss["wochenplan_choice"] = st.radio(
            "Angebote:",
            ["diese_woche", "naechste_woche"],
            format_func=lambda x: "Angebote aus dieser Woche" if x == "diese_woche" else "Angebote der nächsten Woche",
            horizontal=True,
            label_visibility="collapsed"
        )
    with c4:
        starten = st.button("🔍 Wochenplan erstellen", type="primary", use_container_width=True)
    
    if starten:
        # WORKFLOW: Zuerst Angebote suchen, dann Plan generieren
        erlaubte_diets = DIET_OPTIONEN[ss["ernaehrungsweise"]]
        plan_rezepte = [r for r in rezepte if r.get("diet", "vegetarisch") in erlaubte_diets]
        
        # Alle Zutaten sammeln (max 40!)
        alle_zutaten = set()
        for r in plan_rezepte:
            for z in r.get("ingredients", [])[:5]:
                alle_zutaten.add(zutat_name(z))
        
        alle_zutaten = sorted(alle_zutaten)[:40]
        
        # SCHRITT 1: Angebote abfragen
        st.info("📌 Schritt 1: Angebote suchen...")
        fortschritt = st.progress(0, text="Suche Angebote...")
        angebote = {}
        
        for idx, zutat in enumerate(alle_zutaten):
            treffer = suche_angebot(zutat, ss["zip_code"], ss["markt"])
            if treffer:
                angebote[zutat] = treffer
            fortschritt.progress((idx + 1) / len(alle_zutaten), text=f"Suche ({idx+1}/{len(alle_zutaten)})...")
        
        fortschritt.empty()
        st.success(f"✅ {len(angebote)} Angebote gefunden!")
        
        # SCHRITT 2: Plan generieren basierend auf Angeboten
        st.info("📌 Schritt 2: Wochenplan generieren...")
        
        bewertung = []
        for rezept in plan_rezepte:
            zutaten = [zutat_name(z) for z in rezept.get("ingredients", [])[:5]]
            treffer = sum(1 for z in zutaten if z in angebote)
            bewertung.append((rezept, treffer))
        
        bewertung.sort(key=lambda x: x[1], reverse=True)
        
        ss["wochenplan"] = [(r, t) for r, t in bewertung[:7]]
        ss["angebote"] = angebote
        
        st.success(f"✅ Wochenplan mit 7 Top-Rezepten erstellt!")
    
    if ss["wochenplan"]:
        st.markdown("### 🍽️ Dein Wochenplan")
        st.markdown(f"**Markt:** {ss['markt'].upper()} | **PLZ:** {ss['zip_code']} | **Portionen:** {ss['portionen']}")
        
        cols = st.columns(1)
        for idx, (rezept, angebote_count) in enumerate(ss["wochenplan"]):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.markdown(f"### {rezept['icon']} {rezept['name']}")
                st.caption(f"⏱ {rezept['time_min']} Min • {rezept['category']} • {angebote_count} Angebote gefunden")
            with c2:
                if st.button("📖 Details", key=f"detail_{idx}"):
                    ss["selected_recipe"] = rezept["name"]
                    st.rerun()
            with c3:
                if st.button("❤️", key=f"fav_plan_{idx}"):
                    for r in rezepte:
                        if r["name"] == rezept["name"]:
                            r["favorite"] = not r.get("favorite", False)
                    speichere_rezepte(rezepte)
                    st.rerun()

elif ss["nav"] == "Favoriten":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">❤️ Deine Favoriten</div></div>', unsafe_allow_html=True)
    favoriten = [r for r in rezepte if r.get("favorite")]
    
    if favoriten:
        cols = st.columns(3, gap="large")
        for idx, rezept in enumerate(favoriten):
            with cols[idx % 3]:
                st.markdown(f'<div class="recipe-card"><div class="recipe-card-img">{rezept["icon"]}</div><div style="padding: 14px;"><div style="font-size: 15px; font-weight: 700;">{rezept["name"]}</div></div></div>', unsafe_allow_html=True)
                if st.button("Ansehen", key=f"fav_view_{rezept['name']}", use_container_width=True):
                    ss["selected_recipe"] = rezept["name"]
                    st.rerun()
    else:
        st.info("Noch keine Favoriten. Markiere Rezepte mit ❤️!")

elif ss["nav"] == "Kategorien":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">Kategorien</div></div>', unsafe_allow_html=True)
    cols = st.columns(len(KATEGORIEN), gap="medium")
    for col, kat in zip(cols, KATEGORIEN):
        with col:
            anzahl = len([r for r in rezepte if r["category"] == kat])
            st.metric(kat, anzahl)

elif ss["nav"] == "Über":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">Über EinfachmitTimo</div></div>', unsafe_allow_html=True)
    st.write("Dein Essensplaner mit aktuellen Aldi- & Lidl-Angeboten.")
    st.caption("Angebote via Marktguru-API (privat)")
    st.metric("Rezepte gesamt", len(rezepte))

# Detailansicht
if ss.get("selected_recipe"):
    aktuelles = next((r for r in rezepte if r["name"] == ss["selected_recipe"]), None)
    if aktuelles:
        if st.button("← Zurück"):
            ss["selected_recipe"] = None
            st.rerun()
        
        st.markdown(f"## {aktuelles['icon']} {aktuelles['name']}")
        st.caption(f"⏱ {aktuelles['time_min']} Min | {aktuelles['category']} | {aktuelles['difficulty']} | {aktuelles['diet']}")
        
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("### Zutaten")
            for z in aktuelles.get("ingredients", []):
                name = zutat_name(z)
                if isinstance(z, dict):
                    menge = z["amount"]
                    unit = z["unit"]
                    st.write(f"- {menge} {unit} {name}")
                else:
                    st.write(f"- {name}")
        
        with c2:
            st.markdown("### Zubereitung")
            for i, step in enumerate(aktuelles.get("steps", []), 1):
                st.write(f"{i}. {step}")
