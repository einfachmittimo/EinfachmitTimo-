#!/usr/bin/env python3
"""
EinfachmitTimo – OPTIMIERT
Workflow: Angebote → Plan (nicht Plan → Angebote)
Max 40 Zutaten, schnelles Caching, ChatGPT-Optimierungen
"""

import json
import requests
import streamlit as st
from pathlib import Path
from PIL import Image
from datetime import timedelta, date

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
:root{--cream:#f7f3ec;--paper:#fffdf9;--ink:#20201d;--muted:#77736d;--gold:#a97732;--line:#e8e0d4}
*{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.stApp{background:var(--cream);color:var(--ink)}
[data-testid="stHeader"]{background:rgba(247,243,236,.94)}
.block-container{padding-top:1rem;padding-bottom:5rem;max-width:1440px}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#171918,#292720);border-right:1px solid #39362e}
section[data-testid="stSidebar"] *{color:#f7f3ec}
section[data-testid="stSidebar"] [data-testid="stRadio"] label{padding:.55rem .7rem;border-radius:12px}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:#403627}
.banner-hero{background:linear-gradient(110deg,#191b19,#292821 62%,#5b472d);padding:24px 28px;border-radius:22px;color:#fffaf0;margin:0 0 22px;border:1px solid #403a2e;box-shadow:0 8px 24px #231d141a}
.banner-hero-title{font-size:clamp(25px,3vw,38px);font-weight:850;letter-spacing:-.8px;margin:0}.home-hero{padding:20px 24px;margin-bottom:16px}.home-hero .banner-hero-sub{font-size:10px}.home-recipe-title{font-weight:750;font-size:15px;line-height:1.3;padding:10px 2px 0;color:#24231f}.home-stats{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 18px}.home-stat{flex:1 1 85px;background:#f0e5d5;border:1px solid #e3d2b8;border-radius:12px;padding:8px 10px;color:#5a452b;font-size:12px}.home-stat strong{display:block;font-size:18px;color:#29251f}.home-actions{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 18px}.home-actions-note{font-size:12px;color:var(--muted)}.home-food-card{background:#fffdf9;border:1px solid #e8e0d4;border-radius:15px;padding:8px 8px 12px;margin-bottom:12px;overflow:hidden}.home-food-card img{border-radius:10px}
.banner-hero-sub{color:#d9b77b;font-size:11px;letter-spacing:3px;margin-top:5px}
.recipe-card{background:var(--paper);border-radius:18px;border:1px solid var(--line);box-shadow:0 3px 12px #2c24170e;overflow:hidden;transition:transform .18s ease,box-shadow .18s ease}
.recipe-card:hover{transform:translateY(-2px);box-shadow:0 8px 20px #2c24171a}
.recipe-card-img{font-size:46px;text-align:center;padding:23px 0;background:linear-gradient(135deg,#f0e3d1,#e8ddcb);min-height:92px}
.recipe-card-meta{display:flex;gap:6px;flex-wrap:wrap;color:#61594f;font-size:11px;margin-top:8px}
.section-title{font-size:24px;font-weight:850;letter-spacing:-.5px;margin:0 0 4px}
.section-subtitle{color:var(--muted);font-size:13px;margin-bottom:18px}
div[data-testid="stMetric"]{background:var(--paper);border:1px solid var(--line);padding:10px 12px;border-radius:14px;box-shadow:0 2px 8px #2c24170a}div[data-testid="stMetricLabel"]{font-size:12px}div[data-testid="stMetricValue"]{font-size:22px}
.stButton>button{border-radius:12px;border:1px solid #e5d6bd;background:#fffdf9;color:#3b3020;font-weight:650;min-height:42px}
.stButton>button:hover{border-color:#b88a4a;color:#80591e;background:#fbf3e6}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#b78948,#8f632a);color:white;border:0}
input,textarea,[data-baseweb="select"]>div{border-radius:12px!important}
[data-testid="stTabs"] button{border-radius:18px;padding:.45rem .9rem}
[data-testid="stTabs"] [aria-selected="true"]{color:#8d6025!important}
@media(max-width:760px){.block-container{padding:.55rem .55rem 3rem}.banner-hero{padding:16px;border-radius:16px;margin-bottom:13px}.banner-hero-title{font-size:24px}.home-hero{padding:15px 14px;margin-bottom:10px}.home-hero .banner-hero-sub{font-size:9px;letter-spacing:1.3px;line-height:1.5}.home-stats{gap:6px;margin-bottom:12px}.home-stat{flex:1 1 70px;padding:7px 8px;font-size:10px}.home-stat strong{font-size:16px}.home-actions{gap:6px;margin:5px 0 14px}.home-recipe-title{font-size:13px}.section-title{font-size:21px}.section-subtitle{margin-bottom:10px}.recipe-card-img{min-height:70px;padding:14px 0;font-size:36px}.recipe-card{border-radius:14px}.stButton>button{min-height:38px;font-size:12px;padding:.35rem .45rem}[data-testid="stHorizontalBlock"]{gap:.45rem}div[data-testid="stMetric"]{padding:8px 8px}div[data-testid="stMetricValue"]{font-size:18px}div[data-testid="stMetricLabel"]{font-size:10px}.home-recipe-title{font-size:14px}}
</style>
""", unsafe_allow_html=True)


def hole_marktguru_keys():
    """Lädt API-Zugangsdaten ausschließlich aus Streamlit-Secrets."""
    try:
        secrets = st.secrets["marktguru"]
        clientkey = str(secrets.get("clientkey", "")).strip()
        apikey = str(secrets.get("apikey", "")).strip()
    except Exception:
        clientkey = apikey = ""

    if not clientkey or not apikey:
        return None
    return {"x-clientkey": clientkey, "x-apikey": apikey}


HEADERS = hole_marktguru_keys()


def _normalisiere_rezept(r):
    """Vereinheitlicht englische und deutsche JSON-Feldnamen, ohne Quelldatei umzuschreiben."""
    r = dict(r)
    r["name"] = str(r.get("name", r.get("titel", "Rezept ohne Titel")))
    r["category"] = str(r.get("category", r.get("kategorie", "Mittagessen")))
    r["diet"] = str(r.get("diet", r.get("ernaehrung", "vegetarisch"))).lower()
    r["icon"] = str(r.get("icon", "🍽️"))
    r["time_min"] = r.get("time_min", r.get("zubereitungszeit_min", r.get("zubereitungszeit", 20)))
    r["difficulty"] = str(r.get("difficulty", r.get("schwierigkeit", "Einfach")))
    r["steps"] = r.get("steps", r.get("zubereitung", [])) or []
    r["ingredients"] = r.get("ingredients", r.get("zutaten", [])) or []
    r["nutrition"] = r.get("nutrition", r.get("naehrwerte_pro_portion", {})) or {}
    for z in r["ingredients"]:
        if isinstance(z, dict):
            z.setdefault("name", z.get("name", ""))
            z.setdefault("amount", z.get("menge", ""))
            z.setdefault("unit", z.get("einheit", ""))
    # Kompatible Ernährungsbegriffe für Filter
    mapping = {
        "fleisch": "fleisch", "fleischhaltig": "fleisch",
        "fisch": "fisch", "pescetarisch": "fisch",
        "vegetarisch": "vegetarisch", "vegan": "vegan",
    }
    r["diet"] = mapping.get(r["diet"], r["diet"])
    r.setdefault("favorite", False)
    return r


def lade_rezepte():
    if not RECIPES_FILE.exists():
        st.error(f"Die Datei {RECIPES_FILE.name} wurde nicht gefunden. Bitte im selben Ordner wie app.py ablegen.")
        st.stop()
    try:
        with RECIPES_FILE.open(encoding="utf-8") as f:
            daten = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        st.error(f"Rezepte konnten nicht geladen werden: {exc}")
        st.stop()
    if not isinstance(daten, list):
        st.error("recipes.json muss eine JSON-Liste mit Rezepten enthalten.")
        st.stop()
    return [_normalisiere_rezept(r) for r in daten if isinstance(r, dict)]


def rezeptbild_pfad(rezept):
    """Findet ein lokales Rezeptbild anhand von ID oder Bildangabe.

    Unterstützt Bilder im Projekt-Hauptordner sowie in üblichen Bildordnern.
    Dateiendungen und Groß-/Kleinschreibung werden berücksichtigt.
    """
    basis = Path(__file__).resolve().parent
    endungen = {".jpg", ".jpeg", ".png", ".webp", ".jfif"}

    bildangaben = []
    for feld in ("image", "bild", "image_path", "bild_pfad", "photo", "foto", "filename"):
        wert = rezept.get(feld)
        if isinstance(wert, str) and wert.strip():
            bildangaben.append(wert.strip())

    rezept_id = str(rezept.get("id", "")).strip()
    suchnamen = []
    for wert in bildangaben + ([rezept_id] if rezept_id else []):
        if "://" in wert:
            continue
        pfad = Path(wert)
        suchnamen.append(pfad.name)
        if pfad.suffix:
            suchnamen.append(pfad.stem)

    ordner = [
        basis,
        basis / "assets" / "recipes",
        basis / "assets",
        basis / "images" / "recipes",
        basis / "images",
        basis / "static" / "images",
        basis / "static",
        basis / "recipe_images",
        basis / "recipe-images",
        basis / "media",
    ]

    for suchname in suchnamen:
        kandidat = Path(suchname)
        if kandidat.is_absolute():
            kandidaten = [kandidat]
        else:
            kandidaten = []
            for ordner_pfad in ordner:
                if kandidat.suffix.lower() in endungen:
                    kandidaten.append(ordner_pfad / kandidat.name)
                else:
                    kandidaten.extend(
                        ordner_pfad / f"{kandidat.name}{endung}"
                        for endung in (".jpg", ".jpeg", ".png", ".webp", ".jfif")
                    )
        for bild in kandidaten:
            try:
                if bild.is_file() and bild.suffix.lower() in endungen:
                    return bild
            except OSError:
                continue

    # Fallback für verschachtelte Ordner und Endungen wie "102.JPG".
    ordner_zum_scannen = [
        basis, basis / "assets", basis / "images", basis / "static",
        basis / "recipe_images", basis / "recipe-images", basis / "media",
    ]
    gesuchte_stems = {Path(n).stem.casefold() for n in suchnamen if n}
    for wurzel in ordner_zum_scannen:
        if not wurzel.is_dir():
            continue
        try:
            for bild in wurzel.rglob("*"):
                if not bild.is_file() or bild.suffix.lower() not in endungen:
                    continue
                if any(
                    teil in {".git", ".venv", "venv", "__pycache__", "node_modules"}
                    for teil in bild.parts
                ):
                    continue
                if bild.stem.casefold() in gesuchte_stems:
                    return bild
        except OSError:
            continue

    return None


def speichere_rezepte(rezepte):
    """Speichert Favoriten atomar und erhält unbekannte Felder der Originaldatensätze."""
    try:
        with RECIPES_FILE.open(encoding="utf-8") as f:
            original = json.load(f)
        by_name = {str(r.get("name", r.get("titel", ""))): r for r in original if isinstance(r, dict)}
        for r in rezepte:
            name = r.get("name", "")
            if name in by_name:
                by_name[name]["favorite"] = bool(r.get("favorite", False))
        tmp = RECIPES_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(RECIPES_FILE)
    except (OSError, json.JSONDecodeError) as exc:
        st.error(f"Favoriten konnten nicht gespeichert werden: {exc}")


def zutat_name(z):
    if isinstance(z, dict):
        return str(z.get("name", z.get("zutat", "")))
    return str(z)


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
    """Sucht ein Angebot. Liefert bei fehlender Konfiguration/Fehlern None."""
    if not HEADERS:
        return None
    params = {"as": "web", "limit": 10, "offset": 0, "q": zutat, "zipCode": plz}
    try:
        response = requests.get(API_URL, headers=HEADERS, params=params, timeout=(3.05, 8))
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            return None
    except (requests.RequestException, ValueError):
        return None

    target = markt.lower()
    for result in data.get("results", []):
        if not isinstance(result, dict) or result.get("price") is None:
            continue
        for advertiser in result.get("advertisers", []):
            if str(advertiser.get("uniqueName", "")).lower() == target:
                return {
                    "beschreibung": str(result.get("description", "")),
                    "preis": result.get("price"),
                    "haendler": str(advertiser.get("name", markt)),
                    "gueltig_von": result.get("validFrom") or result.get("startDate"),
                    "gueltig_bis": result.get("validTo") or result.get("endDate"),
                }
    return None


def plz_gueltig(plz):
    return bool(__import__("re").fullmatch(r"\d{5}", str(plz).strip()))


def html_sicher(wert):
    """Escaped dynamische Inhalte vor der Ausgabe in HTML."""
    import html
    return html.escape(str(wert), quote=True)


def zutat_menge_einheit(z):
    if not isinstance(z, dict):
        return "", "", zutat_name(z)
    menge = z.get("amount", z.get("menge", ""))
    einheit = z.get("unit", z.get("einheit", ""))
    name = zutat_name(z)
    return menge, einheit, name


def ernaehrung_kompatibel(diet, erlaubte):
    diet = str(diet or "").lower()
    aliases = {"fleischhaltig": "fleisch", "pescetarisch": "fisch"}
    diet = aliases.get(diet, diet)
    if diet in erlaubte:
        return True
    if diet == "vegetarisch" and "vegan" in erlaubte:
        return False
    return False


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
ss.setdefault("meal_types", "Alles")
ss.setdefault("angebote", {})  # Gefundene Angebote
ss.setdefault("wochenplan", [])  # Generierter Plan
ss.setdefault("plan_rezepte_names", [])
ss.setdefault("einkauf_abgehakt", [])

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
    
    nav_optionen = ["Startseite", "Rezepte", "Wochenplan", "Einkaufsliste", "Favoriten", "Kategorien", "Über"]
    ss["nav"] = st.radio("Navigation", nav_optionen, index=nav_optionen.index(ss["nav"]), label_visibility="collapsed")

    st.divider()
    with st.expander("⚙️ Einstellungen"):
        ss["zip_code"] = st.text_input("PLZ", value=ss["zip_code"], max_chars=5)
        markt_optionen = ["lidl", "aldi-sued", "aldi-nord", "edeka", "rewe", "penny", "netto", "norma"]
        ss["markt"] = st.selectbox("Markt", markt_optionen, index=markt_optionen.index(ss["markt"]) if ss["markt"] in markt_optionen else 0)
        ss["portionen"] = st.number_input("Portionen", min_value=1, max_value=12, value=ss["portionen"])
        ss["ernaehrungsweise"] = st.selectbox("Ernährungsweise", list(DIET_OPTIONEN.keys()), index=list(DIET_OPTIONEN.keys()).index(ss["ernaehrungsweise"]))
        meal_types_optionen = ["Alles", "Frühstück", "Mittagessen", "Abendessen"]
        ss["meal_types"] = st.selectbox("Mahlzeiten", meal_types_optionen, index=meal_types_optionen.index(ss["meal_types"]))


# ============================================================
#  SEITEN
# ============================================================
st.markdown('<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px;"><div style="font-weight:850;font-size:16px;">♨️ Einfachmit<span style="color:#a97732;">Timo</span><div style="font-size:9px;letter-spacing:2px;color:#81796e;font-weight:600;">EINFACH GUTES ESSEN</div></div><div style="font-size:12px;color:#77736d;background:#fffdf9;border:1px solid #e8e0d4;padding:8px 12px;border-radius:20px;">Dein Rezept- & Wochenplaner</div></div>', unsafe_allow_html=True)

if ss["nav"] == "Startseite":
    st.markdown('<div class="banner-hero home-hero"><div class="banner-hero-title">🍽️ EinfachmitTimo</div><div class="banner-hero-sub">EINFACH GUTES ESSEN · DEIN REZEPT- & WOCHENPLANER</div></div>', unsafe_allow_html=True)

    # Kompakte Kennzahlen statt großer Metric-Karten.
    fav_count = sum(bool(r.get("favorite")) for r in rezepte)
    plan_count = len(ss.get("wochenplan", []))
    st.markdown(
        f'<div class="home-stats">'
        f'<div class="home-stat"><strong>{len(rezepte)}</strong>Rezepte</div>'
        f'<div class="home-stat"><strong>{fav_count}</strong>Favoriten</div>'
        f'<div class="home-stat"><strong>{plan_count}/7</strong>Wochenplan</div>'
        f'</div>', unsafe_allow_html=True
    )

    st.markdown('<div class="section-title">Inspiration für heute</div><div class="section-subtitle">Entdecke leckere Ideen aus deiner Sammlung.</div>', unsafe_allow_html=True)
    bevorzugt = ["102", "12", "221", "25", "10", "113"]
    featured = []
    for rid in bevorzugt:
        match = next((r for r in rezepte if str(r.get("id", "")) == rid), None)
        if match and match not in featured:
            featured.append(match)
    if not featured:
        featured = rezepte[:6]

    cols = st.columns(2, gap="small")
    for idx, rezept in enumerate(featured[:6]):
        with cols[idx % 2]:
            st.markdown('<div class="home-food-card">', unsafe_allow_html=True)
            bild_pfad = rezeptbild_pfad(rezept)
            if bild_pfad:
                st.image(str(bild_pfad), use_container_width=True)
            else:
                st.markdown(f'<div class="recipe-card-img">{html_sicher(rezept.get("icon", "🍽️"))}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="home-recipe-title">{html_sicher(rezept.get("name", "Rezept"))}</div>', unsafe_allow_html=True)
            nutrition = rezept.get("nutrition", {}) or {}
            kcal = nutrition.get("kcal", nutrition.get("calories", "–")) if isinstance(nutrition, dict) else "–"
            st.caption(f'⏱ {rezept.get("time_min", 20)} Min  ·  {kcal} kcal')
            if st.button("Rezept ansehen", key=f"home_view_{rezept.get('id', idx)}", use_container_width=True):
                ss["selected_recipe"] = rezept.get("name", "Rezept")
                ss["nav"] = "Rezepte"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title" style="margin-top:.4rem">Schnellzugriff</div>', unsafe_allow_html=True)
    q1, q2, q3 = st.columns(3, gap="small")
    with q1:
        if st.button("🍴 Rezepte", key="btn_rezepte", use_container_width=True):
            ss["nav"] = "Rezepte"; st.rerun()
    with q2:
        if st.button("📅 Wochenplan", key="btn_plan", use_container_width=True):
            ss["nav"] = "Wochenplan"; st.rerun()
    with q3:
        if st.button("♡ Favoriten", key="btn_fav", use_container_width=True):
            ss["nav"] = "Favoriten"; st.rerun()

elif ss["nav"] == "Rezepte":
    st.markdown('<div class="section-title">Rezepte</div><div class="section-subtitle">Durchsuche deine Sammlung und speichere deine Lieblingsgerichte.</div>', unsafe_allow_html=True)
    
    suchtext = st.text_input("🔍 Suchen...", placeholder="Nach Rezepten suchen...")
    
    erlaubte_diets = DIET_OPTIONEN[ss["ernaehrungsweise"]]
    gefiltert = rezepte
    
    if suchtext:
        s = suchtext.lower()
        gefiltert = [r for r in gefiltert if s in str(r.get("name", "")).lower()
                    or any(s in zutat_name(z).lower() for z in r.get("ingredients", []))]
    
    gefiltert = [r for r in gefiltert if ernaehrung_kompatibel(r.get("diet", "vegetarisch"), erlaubte_diets)]
    
    tabs = st.tabs(["Alle"] + KATEGORIEN)
    for tab, kat in zip(tabs, ["Alle"] + KATEGORIEN):
        with tab:
            if kat != "Alle":
                kat_rezepte = [r for r in gefiltert if r["category"] == kat]
            else:
                kat_rezepte = gefiltert
            
            if kat_rezepte:
                cols = st.columns(3, gap="medium")
                for idx, rezept in enumerate(kat_rezepte):
                    with cols[idx % 3]:
                        bild_pfad = rezeptbild_pfad(rezept)
                        if bild_pfad:
                            st.image(str(bild_pfad), use_container_width=True)
                        else:
                            st.markdown(f'<div class="recipe-card-img">{html_sicher(rezept.get("icon", "🍽️"))}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="recipe-card"><div style="padding: 14px;"><div style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">{html_sicher(rezept.get("name", "Rezept"))}</div><span style="display: inline-block; background: #f5e6d3; color: #7a5f35; font-size: 10px; padding: 3px 8px; border-radius: 16px; margin-right: 4px;">⏱ {rezept.get("time_min", 20)}m</span><span style="display: inline-block; background: #f0e6d2; color: #6d5c47; font-size: 10px; padding: 3px 8px; border-radius: 16px;">{html_sicher(rezept["diet"])}</span></div></div>', unsafe_allow_html=True)
                        
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            if st.button("Ansehen", key=f"view_{idx}_{rezept.get('name', 'Rezept')}", use_container_width=True):
                                ss["selected_recipe"] = rezept.get("name", "Rezept")
                                st.rerun()
                        with c2:
                            herz = "❤️" if rezept.get("favorite") else "🤍"
                            if st.button(herz, key=f"fav_{idx}_{rezept.get('name', 'Rezept')}", use_container_width=True):
                                for r in rezepte:
                                    if r.get("name") == rezept.get("name"):
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
        markt_optionen = ["lidl", "aldi-sued", "aldi-nord", "edeka", "rewe", "penny", "netto", "norma"]
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
        plan_rezepte = [r for r in rezepte if ernaehrung_kompatibel(r.get("diet", "vegetarisch"), erlaubte_diets)]
        
        # Filter nach Mahlzeiten
        if ss["meal_types"] != "Alles":
            plan_rezepte = [r for r in plan_rezepte if r.get("category") == ss["meal_types"]]
        
        # Alle Zutaten sammeln (max 40!)
        alle_zutaten = set()
        for r in plan_rezepte:
            for z in r.get("ingredients", []):
                alle_zutaten.add(zutat_name(z))
        
        alle_zutaten = sorted(alle_zutaten)[:40]
        
        if not plz_gueltig(ss["zip_code"]):
            st.error("Bitte gib eine gültige fünfstellige deutsche PLZ ein.")
            st.stop()
        if not HEADERS:
            st.error("Marktguru-Zugangsdaten fehlen. Hinterlege clientkey und apikey unter [marktguru] in .streamlit/secrets.toml.")
            st.stop()

        # Marktguru liefert je nach Treffer keine verlässlichen Gültigkeitsdaten.
        # Für die nächste Woche deshalb keine zukünftige Angebotsgültigkeit vortäuschen.
        if ss["wochenplan_choice"] == "naechste_woche":
            st.warning("Marktguru liefert nicht bei jedem Treffer ein Gültigkeitsdatum. Angebote ohne Datum können nicht sicher der nächsten Woche zugeordnet werden.")

        # SCHRITT 1: Angebote abfragen
        st.info("Schritt 1: Angebote suchen, danach Rezepte auswählen...")
        fortschritt = st.progress(0, text="Suche Angebote...")
        angebote = {}
        
        for idx, zutat in enumerate(alle_zutaten):
            treffer = suche_angebot(zutat, ss["zip_code"], ss["markt"])
            if treffer:
                angebote[zutat] = treffer
            fortschritt.progress((idx + 1) / len(alle_zutaten), text=f"Suche ({idx+1}/{len(alle_zutaten)})...")
        
        fortschritt.empty()
        st.success(f"{len(angebote)} passende Angebotstreffer gefunden.")
        if alle_zutaten and not angebote:
            st.warning("Es wurden keine passenden Angebote gefunden. Der Plan wird dann nach Rezeptnamen sortiert und nicht nach Angebotsvorteilen.")
        
        # SCHRITT 2: Plan generieren basierend auf Angeboten
        st.info("📌 Schritt 2: Wochenplan generieren...")
        
        bewertung = []
        for rezept in plan_rezepte:
            zutaten = [zutat_name(z) for z in rezept.get("ingredients", [])]
            treffer = sum(1 for z in zutaten if z in angebote)
            bewertung.append((rezept, treffer))
        
        # Stabil sortieren; keine zufälligen Änderungen bei jedem Neuladen.
        bewertung_sorted = sorted(bewertung, key=lambda x: (-x[1], str(x[0].get("name", "")).casefold()))
        ss["wochenplan"] = [(r, t) for r, t in bewertung_sorted[:7]]
        ss["plan_rezepte_names"] = [r.get("name", "") for r, _ in ss["wochenplan"]]
        ss["angebote"] = angebote
        if not ss["wochenplan"]:
            st.warning("Mit diesen Filtern wurden keine passenden Rezepte gefunden.")
        else:
            st.success(f"Wochenplan mit {len(ss['wochenplan'])} Rezepten erstellt.")
    
    if ss["wochenplan"]:
        st.markdown("### 🍽️ Dein Wochenplan")
        start_datum, end_datum = get_week_dates(ss["wochenplan_choice"])
        wochen_label = "diese Woche" if ss["wochenplan_choice"] == "diese_woche" else "nächste Woche"
        st.markdown(f"**Markt:** {ss['markt'].upper()} | **PLZ:** {ss['zip_code']} | **Portionen:** {ss['portionen']} | **Zeitraum:** {start_datum:%d.%m.}–{end_datum:%d.%m.%Y} ({wochen_label})")
        
        # Speicher aktuelle Plan-Rezept-Namen
        ss["plan_rezepte_names"] = [r.get("name", "") for r, _ in ss["wochenplan"]]
        
        for idx, (rezept, angebote_count) in enumerate(ss["wochenplan"]):
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
            with col1:
                st.markdown(f"### {html_sicher(rezept.get('icon', '🍽️'))} {html_sicher(rezept.get('name', 'Rezept'))}")
                st.caption(f"⏱ {rezept['time_min']} Min • {rezept['category']} • {angebote_count} Angebote gefunden")
            with col2:
                if st.button("📖", key=f"detail_{idx}", help="Details anschauen"):
                    ss["selected_recipe"] = rezept.get("name", "Rezept")
                    st.rerun()
            with col3:
                herz = "❤️" if rezept.get("favorite") else "🤍"
                if st.button(herz, key=f"fav_plan_{idx}", help="Zu Favoriten"):
                    for r in rezepte:
                        if r.get("name") == rezept.get("name"):
                            r["favorite"] = not r.get("favorite", False)
                    speichere_rezepte(rezepte)
                    st.rerun()
            with col4:
                if st.button("🔄", key=f"swap_{idx}", help="Austauschen"):
                    # Nächstes Rezept aus gleicher Kategorie finden
                    kategorie = rezept.get("category", "Mittagessen")
                    andere = [r for r in rezepte 
                             if r["category"] == kategorie 
                             and r.get("name") != rezept.get("name")
                             and r["name"] not in ss["plan_rezepte_names"]]
                    
                    if andere:
                        neues = andere[0]
                        ss["wochenplan"][idx] = (neues, 0)
                        ss["plan_rezepte_names"][idx] = neues["name"]
                        st.rerun()
                    else:
                        st.warning(f"Keine anderen {kategorie}-Rezepte verfügbar")
            with col5:
                if st.button("✕", key=f"remove_{idx}", help="Aus Plan entfernen"):
                    ss["wochenplan"].pop(idx)
                    ss["plan_rezepte_names"].pop(idx)
                    st.rerun()

elif ss["nav"] == "Einkaufsliste":
    st.markdown('<div class="section-title">Einkaufsliste</div><div class="section-subtitle">Zutaten aus deinem Wochenplan gesammelt an einem Ort.</div>', unsafe_allow_html=True)
    alle = {}
    for rezept, _treffer in ss.get("wochenplan", []):
        for z in rezept.get("ingredients", []):
            menge, einheit, name = zutat_menge_einheit(z)
            name = str(name).strip()
            if not name: continue
            key = (name.casefold(), str(einheit).casefold())
            try: amount_num = float(str(menge).replace(",", "."))
            except (TypeError, ValueError): amount_num = None
            if key not in alle: alle[key] = {"name":name,"unit":str(einheit),"amount":amount_num,"raw":str(menge)}
            elif amount_num is not None and alle[key]["amount"] is not None: alle[key]["amount"] += amount_num
            else: alle[key]["amount"] = None; alle[key]["raw"] = ""
    if not alle:
        st.info("Deine Einkaufsliste ist noch leer. Erstelle zuerst einen Wochenplan.")
        if st.button("Zum Wochenplan", type="primary"): ss["nav"] = "Wochenplan"; st.rerun()
    else:
        st.metric("Zutaten auf der Liste", len(alle))
        st.caption("Gleiche Zutaten mit derselben Einheit werden zusammengefasst.")
        for i, item in enumerate(sorted(alle.values(), key=lambda x:x["name"].casefold())):
            menge = item["raw"] if item["amount"] is None else str(round(item["amount"],2)).replace(".",",")
            label = f'{item["name"]} — {menge} {item["unit"]}'.strip()
            value = st.checkbox(label, value=label in ss["einkauf_abgehakt"], key=f"shop_{i}")
            if value and label not in ss["einkauf_abgehakt"]: ss["einkauf_abgehakt"].append(label)
            elif not value and label in ss["einkauf_abgehakt"]: ss["einkauf_abgehakt"].remove(label)
        st.caption(f'{len(ss["einkauf_abgehakt"])} Zutaten abgehakt.')

elif ss["nav"] == "Favoriten":
    st.markdown('<div class="banner-hero"><div class="banner-hero-title">❤️ Deine Favoriten</div></div>', unsafe_allow_html=True)
    favoriten = [r for r in rezepte if r.get("favorite")]
    
    if favoriten:
        cols = st.columns(3, gap="medium")
        for idx, rezept in enumerate(favoriten):
            with cols[idx % 3]:
                bild_pfad = rezeptbild_pfad(rezept)
                if bild_pfad:
                    st.image(str(bild_pfad), use_container_width=True)
                else:
                    st.markdown(f'<div class="recipe-card-img">{html_sicher(rezept.get("icon", "🍽️"))}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="recipe-card"><div style="padding: 14px;"><div style="font-size: 15px; font-weight: 700;">{html_sicher(rezept.get("name", "Rezept"))}</div></div></div>', unsafe_allow_html=True)
                if st.button("Ansehen", key=f"fav_view_{rezept['name']}", use_container_width=True):
                    ss["selected_recipe"] = rezept.get("name", "Rezept")
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
    st.caption("Angebote werden über Marktguru gesucht. Ob ein Angebot in der gewählten Kalenderwoche gültig ist, wird nur angezeigt, wenn die API dazu ein Gültigkeitsdatum liefert.")
    st.metric("Rezepte gesamt", len(rezepte))

# Detailansicht
if ss.get("selected_recipe"):
    aktuelles = next((r for r in rezepte if r.get("name") == ss["selected_recipe"]), None)
    if aktuelles:
        if st.button("← Zurück"):
            ss["selected_recipe"] = None
            st.rerun()
        
        st.markdown(f"## {html_sicher(aktuelles.get('icon', '🍽️'))} {html_sicher(aktuelles.get('name', 'Rezept'))}")
        st.caption(f"⏱ {aktuelles.get('time_min', 20)} Min | {aktuelles.get('category', 'Mittagessen')} | {aktuelles.get('difficulty', 'Einfach')} | {aktuelles.get('diet', 'vegetarisch')}")
        detail_bild = rezeptbild_pfad(aktuelles)
        if detail_bild:
            st.image(str(detail_bild), use_container_width=True)
        portions_basis = aktuelles.get("portionen", aktuelles.get("portions", 4))
        try:
            portions_basis = max(1, int(portions_basis))
        except (TypeError, ValueError):
            portions_basis = 4
        faktor = ss["portionen"] / portions_basis
        st.caption(f"Zutatenmengen angepasst auf {ss['portionen']} Portion(en).")
        
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("### Zutaten")
            for z in aktuelles.get("ingredients", []):
                name = zutat_name(z)
                if isinstance(z, dict):
                    menge, unit, name = zutat_menge_einheit(z)
                    try:
                        menge_anzeige = float(str(menge).replace(",", ".")) * faktor
                        menge_anzeige = int(menge_anzeige) if menge_anzeige.is_integer() else round(menge_anzeige, 2)
                        menge = str(menge_anzeige).replace(".", ",")
                    except (TypeError, ValueError):
                        pass
                    st.write(f"- {menge} {unit} {name}".strip())
                else:
                    st.write(f"- {name}")
        
        nutrition = aktuelles.get("nutrition", {})
        if nutrition:
            st.markdown("### Nährwerte pro Portion")
            if isinstance(nutrition, dict):
                ncols = st.columns(min(4, max(1, len(nutrition))))
                for col, (label, value) in zip(ncols, nutrition.items()):
                    with col:
                        st.metric(str(label).replace("_", " ").capitalize(), str(value))
            else:
                st.write(nutrition)

        with c2:
            st.markdown("### Zubereitung")
            for i, step in enumerate(aktuelles.get("steps", []), 1):
                st.write(f"{i}. {step}")
