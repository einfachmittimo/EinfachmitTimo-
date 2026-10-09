#!/usr/bin/env python3
"""
Essensplaner - Web-Oberfläche im "EinfachmitTimo"-Stil

Lokal starten:
    pip install streamlit requests
    streamlit run app.py

Für Hosting (Streamlit Community Cloud) siehe README.md –
API-Keys werden dort über st.secrets statt fest im Code verwaltet.
"""

import json
import math
import requests
import streamlit as st
from pathlib import Path

# ---- Konfiguration ----
RECIPES_FILE = Path(__file__).parent / "recipes.json"
API_URL = "https://api.marktguru.de/api/v1/offers/search"


def hole_marktguru_keys():
    """Liest die Marktguru-API-Keys aus st.secrets (Hosting) oder
    verwendet lokale Fallback-Werte (zum Testen auf dem eigenen Rechner)."""
    try:
        return {
            "x-clientkey": st.secrets["marktguru"]["clientkey"],
            "x-apikey": st.secrets["marktguru"]["apikey"],
        }
    except Exception:
        # Fallback für lokale Entwicklung ohne secrets.toml
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
    "Pescetarisch (kein Fleisch, Fisch ok)": {"vegan", "vegetarisch", "fisch"},
}
KATEGORIEN = ["Frühstück", "Mittagessen", "Abendessen"]

# ============================================================
#  Styling – dunkles Theme mit Sidebar-Navigation
# ============================================================
st.set_page_config(page_title="EinfachmitTimo – Essensplaner", page_icon="🍽️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #121212; color: #eee; }
    section[data-testid="stSidebar"] {
        background-color: #181818;
        border-right: 1px solid #2a2a2a;
    }
    section[data-testid="stSidebar"] * { color: #eee; }
    div[role="radiogroup"] > label {
        display: block; padding: 10px 14px; margin-bottom: 4px;
        border-radius: 8px; cursor: pointer;
    }
    div[role="radiogroup"] > label:hover { background-color: #262626; }
    div[role="radiogroup"] input[type="radio"] { display: none; }
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: #E8791A; color: #111 !important; font-weight: 600;
    }
    div[role="radiogroup"] > label:has(input:checked) * { color: #111 !important; }

    .brand { text-align:center; padding: 10px 0 20px 0; }
    .brand-title { font-size: 22px; font-weight: 800; color: #E8791A; }
    .brand-sub { font-size: 11px; letter-spacing: 2px; color: #999; }

    .recipe-card {
        background-color: #1e1e1e; border-radius: 14px; padding: 0;
        overflow: hidden; border: 1px solid #2a2a2a; margin-bottom: 8px;
    }
    .recipe-card-img {
        font-size: 60px; text-align: center; padding: 28px 0;
        background: linear-gradient(135deg,#2a2a2a,#1a1a1a);
    }
    .recipe-card-body { padding: 12px 14px 4px 14px; }
    .recipe-card-title { font-size: 16px; font-weight: 700; margin-bottom: 6px; color:#fff; }
    .badge {
        display: inline-block; font-size: 11px; padding: 2px 9px;
        border-radius: 20px; margin-right: 6px; margin-bottom: 6px;
    }
    .badge-time { background-color: #2a2a2a; color: #ccc; }
    .badge-Frühstück { background-color: #3a2f14; color: #f0b429; }
    .badge-Mittagessen { background-color: #142a1f; color: #4ade80; }
    .badge-Abendessen { background-color: #1c2438; color: #7aa2f7; }
    .badge-diet { background-color: #24303d; color: #9fd3ff; }
    .badge-deal { background-color: #E8791A; color: #111; font-weight:700; }

    .detail-header { display:flex; gap:20px; align-items:flex-start; margin-bottom: 10px;}
    .detail-icon { font-size: 90px; }

    .stButton>button {
        border-radius: 8px; border: 1px solid #333; background-color:#232323; color:#eee;
    }
    .stButton>button:hover { border-color:#E8791A; color:#E8791A; }
    hr { border-color: #2a2a2a; }
</style>
""", unsafe_allow_html=True)


# ============================================================
#  Daten laden / speichern
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
#  Session State Grundwerte
# ============================================================
ss = st.session_state
ss.setdefault("nav", "Startseite")
ss.setdefault("selected_recipe", None)
ss.setdefault("kategorie_filter", "Alle")
ss.setdefault("suchtext", "")
ss.setdefault("zip_code", "89584")
ss.setdefault("retailer_auswahl", ["lidl", "aldi-sued"])
ss.setdefault("portionen", 4)
ss.setdefault("ernaehrungsweise", "Alles")

rezepte = lade_rezepte()


# ============================================================
#  Sidebar
# ============================================================
with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-title">🍽️ EinfachmitTimo</div>'
        '<div class="brand-sub">EINFACH GUTES ESSEN</div></div>',
        unsafe_allow_html=True,
    )
    nav_optionen = ["Startseite", "Rezepte", "Wochenplan", "Favoriten", "Kategorien", "Suche", "Über"]
    ss["nav"] = st.radio("Navigation", nav_optionen, index=nav_optionen.index(ss["nav"]), label_visibility="collapsed")

    st.divider()
    with st.expander("⚙️ Einstellungen (Angebote)"):
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
#  Hilfsfunktionen für Ansicht
# ============================================================
def angebot_fuer(name):
    angebote = ss.get("angebot_je_zutat")
    if angebote:
        return angebote.get(name)
    return None


def zeige_karte(rezept, spalte):
    with spalte:
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


def zeige_grid(liste, spalten_anzahl=3):
    if not liste:
        st.info("Keine Rezepte gefunden.")
        return
    spalten = st.columns(spalten_anzahl)
    for idx, rezept in enumerate(liste):
        zeige_karte(rezept, spalten[idx % spalten_anzahl])


def zeige_detail(rezept):
    if st.button("← Zurück zur Übersicht"):
        ss["selected_recipe"] = None
        st.rerun()

    st.markdown(f"""
    <div class="detail-header">
        <div class="detail-icon">{rezept['icon']}</div>
        <div>
            <h2 style="margin-bottom:4px;">{rezept['name']}</h2>
            <span class="badge badge-time">⏱ {rezept['time_min']} Min</span>
            <span class="badge badge-{rezept['category']}">{rezept['category']}</span>
            <span class="badge badge-diet">{rezept['difficulty']}</span>
            <span class="badge badge-diet">{rezept['diet']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    portionen = ss["portionen"]
    basis = rezept.get("base_servings", 4)
    faktor = portionen / basis

    col_zutaten, col_zubereitung = st.columns([1, 1])

    with col_zutaten:
        st.markdown(f"#### Zutaten *(für {portionen} Portionen)*")
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
                    f"- **{mengen_text} {name}** &nbsp; "
                    f"<span class='badge badge-deal'>🏷️ {angebot['preis']}€ bei {angebot['haendler']}</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"- {mengen_text} {name}")

    with col_zubereitung:
        st.markdown("#### Zubereitung")
        if rezept.get("steps"):
            for i, step in enumerate(rezept["steps"], start=1):
                st.markdown(f"**{i}.** {step}")
        else:
            st.caption("Keine Zubereitungsschritte hinterlegt.")

    st.divider()
    st.markdown("#### Nährwerte pro Portion *(geschätzt)*")
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
#  Seiten
# ============================================================
if ss["selected_recipe"] is not None and ss["nav"] in ("Rezepte", "Favoriten", "Suche", "Kategorien"):
    aktuelles = next((r for r in rezepte if r["name"] == ss["selected_recipe"]), None)
    if aktuelles:
        zeige_detail(aktuelles)
    else:
        ss["selected_recipe"] = None

elif ss["nav"] == "Startseite":
    st.title("🍽️ Willkommen bei EinfachmitTimo")
    st.caption("Dein Essensplaner mit aktuellen Aldi- & Lidl-Angeboten")
    st.markdown("#### Was möchtest du tun?")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**📖 Rezepte durchstöbern**")
        st.write("Alle Rezepte ansehen, filtern und Favoriten markieren.")
        if st.button("Zu den Rezepten", use_container_width=True):
            ss["nav"] = "Rezepte"; st.rerun()
    with c2:
        st.markdown("**📋 Wochenplan erstellen**")
        st.write("Angebote prüfen und passende Rezepte für die Woche finden.")
        if st.button("Wochenplan starten", use_container_width=True):
            ss["nav"] = "Wochenplan"; st.rerun()
    with c3:
        st.markdown("**❤️ Favoriten**")
        st.write("Deine gespeicherten Lieblingsrezepte auf einen Blick.")
        if st.button("Favoriten ansehen", use_container_width=True):
            ss["nav"] = "Favoriten"; st.rerun()

    st.divider()
    st.markdown("#### Übersicht")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Rezepte", len(rezepte))
    s2.metric("Frühstück", len([r for r in rezepte if r["category"] == "Frühstück"]))
    s3.metric("Mittagessen", len([r for r in rezepte if r["category"] == "Mittagessen"]))
    s4.metric("Abendessen", len([r for r in rezepte if r["category"] == "Abendessen"]))
    s5.metric("Favoriten", len([r for r in rezepte if r.get("favorite")]))

elif ss["nav"] == "Rezepte":
    st.title(f"Rezepte ({len(rezepte)})")
    such_col, sort_col = st.columns([3, 1])
    with such_col:
        ss["suchtext"] = st.text_input("🔍 Rezepte durchsuchen...", value=ss["suchtext"], label_visibility="collapsed", placeholder="🔍 Rezepte durchsuchen...")
    with sort_col:
        sortierung = st.selectbox("Sortierung", ["Name (A-Z)", "Kürzeste Zeit zuerst", "Kalorien aufsteigend"], label_visibility="collapsed")

    tabs = st.tabs(["Alle"] + KATEGORIEN)
    tab_namen = ["Alle"] + KATEGORIEN
    for tab, kat in zip(tabs, tab_namen):
        with tab:
            gefiltert = filter_und_suche(rezepte, kat, ss["suchtext"], ss["ernaehrungsweise"])
            if sortierung == "Name (A-Z)":
                gefiltert = sorted(gefiltert, key=lambda r: r["name"])
            elif sortierung == "Kürzeste Zeit zuerst":
                gefiltert = sorted(gefiltert, key=lambda r: r["time_min"])
            else:
                gefiltert = sorted(gefiltert, key=lambda r: r.get("kcal", 0))
            zeige_grid(gefiltert)

elif ss["nav"] == "Favoriten":
    st.title("❤️ Deine Favoriten")
    favoriten = [r for r in rezepte if r.get("favorite")]
    zeige_grid(favoriten)

elif ss["nav"] == "Kategorien":
    st.title("Kategorien")
    cols = st.columns(3)
    for col, kat in zip(cols, KATEGORIEN):
        anzahl = len([r for r in rezepte if r["category"] == kat])
        with col:
            st.markdown(f"### {kat}")
            st.metric("Rezepte", anzahl)
            if st.button(f"{kat} ansehen", key=f"kat_{kat}", use_container_width=True):
                ss["nav"] = "Rezepte"
                ss["kategorie_filter"] = kat
                st.rerun()

elif ss["nav"] == "Suche":
    st.title("🔍 Rezepte suchen")
    suchtext = st.text_input("Suchbegriff (Name oder Zutat)")
    if suchtext:
        ergebnisse = filter_und_suche(rezepte, "Alle", suchtext, ss["ernaehrungsweise"])
        st.caption(f"{len(ergebnisse)} Treffer")
        zeige_grid(ergebnisse)
    else:
        st.info("Gib oben einen Suchbegriff ein.")

elif ss["nav"] == "Über":
    st.title("Über EinfachmitTimo")
    st.write(
        "Dieser Essensplaner gleicht deine eigene Rezeptsammlung mit den "
        "aktuellen Angeboten von Aldi und Lidl ab und schlägt dir passende "
        "Gerichte für die Woche vor – inklusive Einkaufsliste."
    )
    st.caption(
        "Hinweis: Die Angebotsdaten stammen von einer inoffiziellen "
        "Schnittstelle von marktguru.de und sind nur für die private Nutzung gedacht."
    )

elif ss["nav"] == "Wochenplan":
    st.title("📋 Wochenplan")
    c1, c2 = st.columns([1, 3])
    with c1:
        anzahl_rezepte = st.slider("Rezepte im Plan", 3, 15, 7)
    with c2:
        starten = st.button("🔍 Angebote prüfen & Plan erstellen", type="primary")

    if starten:
        if not ss["retailer_auswahl"]:
            st.error("Bitte mindestens einen Markt in den Einstellungen (Sidebar) auswählen.")
        else:
            alle_namen = sorted({zutat_name(z) for r in rezepte for z in r["ingredients"]})
            fortschritt = st.progress(0, text="Suche Angebote...")
            angebot_je_zutat = {}
            for idx, name in enumerate(alle_namen):
                treffer = suche_angebot(name, ss["zip_code"], tuple(ss["retailer_auswahl"]))
                if treffer:
                    angebot_je_zutat[name] = treffer
                fortschritt.progress((idx + 1) / len(alle_namen), text=f"Suche Angebote... ({name})")
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
            st.warning("Keine Rezepte für diese Ernährungsweise gefunden.")
        else:
            offset = ss.get("offset", 0) % len(gefiltert)
            n = min(anzahl_rezepte, len(gefiltert))
            auswahl = [gefiltert[(offset + i) % len(gefiltert)] for i in range(n)]

            hcol1, hcol2 = st.columns([4, 1])
            with hcol1:
                st.subheader(f"Top {n} Rezepte · {ss['ernaehrungsweise']} · für {ss['portionen']} Portionen")
            with hcol2:
                if len(gefiltert) > n and st.button("🔀 Andere vorschlagen", use_container_width=True):
                    ss["offset"] = offset + n
                    st.rerun()

            spalten = st.columns(3)
            for idx, (rezept, treffer_namen) in enumerate(auswahl):
                zeige_karte(rezept, spalten[idx % 3])

            st.divider()
            st.subheader("🛒 Einkaufsliste")
            angebot_je_zutat = ss["angebot_je_zutat"]
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
            spalten2 = st.columns(3)
            for idx, name in enumerate(sorted(summe.keys())):
                info = summe[name]
                gerundet = skaliere_menge(info["amount"], info["unit"], 1)
                mengen_text = formatiere_menge(gerundet, info["unit"])
                markiert = name in angebot_je_zutat
                label = f"{mengen_text} {name} 🏷️" if markiert else f"{mengen_text} {name}"
                spalten2[idx % 3].checkbox(label, key=f"item_{name}")
    else:
        st.info("Klick oben auf 'Angebote prüfen & Plan erstellen', um zu starten.")
