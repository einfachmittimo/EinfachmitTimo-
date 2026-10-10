import base64
import html
import json
import math
import re
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
RECIPES_FILE = BASE_DIR / "recipes.json"
LOGO_FILE = BASE_DIR / "EinfachmitTimo_Logo.jpg"
PORTRAIT_FILE = BASE_DIR / "Timo_Portrait.jpg"

st.set_page_config(
    page_title="EinfachmitTimo – Einfach gutes Essen",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------- Daten ----------
@st.cache_data
def lade_rezepte():
    with RECIPES_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []

rezepte = lade_rezepte()

def titel(r):
    return str(r.get("name") or r.get("titel") or "Ohne Titel").strip()

def kategorie(r):
    return str(r.get("kategorie") or r.get("category") or "Mittagessen").strip()

def diat(r):
    return str(r.get("diet") or r.get("ernaehrung") or "Alles").strip()

def zubereitung(r):
    p = r.get("zubereitung") or r.get("preparation") or r.get("instructions") or r.get("steps")
    if isinstance(p, list):
        return p
    return [str(p)] if p else ["Keine Zubereitung hinterlegt."]

def bild_fallback(r):
    # Es werden bewusst keine falschen oder recycelten Rezeptfotos zugeordnet.
    return None

def naehrwerte(r):
    nv = r.get("nutrition") or {}
    if nv:
        return {
            "kcal": nv.get("kcal", "–"),
            "protein": nv.get("protein", "–"),
            "carbs": nv.get("carbs", "–"),
            "fat": nv.get("fat", "–"),
        }
    # Fallback: Nährwerte aus der Textquelle lesen, sofern vorhanden.
    text = str(r.get("nutrition_source") or "")
    patterns = {
        "kcal": r"([0-9]+(?:[.,][0-9]+)?)\\s*kcal",
        "protein": r"([0-9]+(?:[.,][0-9]+)?)\\s*g?\\s*Protein",
        "carbs": r"([0-9]+(?:[.,][0-9]+)?)\\s*g?\\s*Kohlenhydrate",
        "fat": r"([0-9]+(?:[.,][0-9]+)?)\\s*g?\\s*Fett",
    }
    out = {key: "–" for key in patterns}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            out[key] = match.group(1).replace(",", ".")
    return out

def img_data(path):
    try:
        b = path.read_bytes()
        return "data:image/jpeg;base64," + base64.b64encode(b).decode()
    except Exception:
        return ""

logo_uri = img_data(LOGO_FILE)
portrait_uri = img_data(PORTRAIT_FILE)

# ---------- Session ----------
st.session_state.setdefault("seite", "Rezepte")
st.session_state.setdefault("auswahl", None)
st.session_state.setdefault("favoriten", set())
st.session_state.setdefault("suche", "")
st.session_state.setdefault("wochenplan", {})
st.session_state.setdefault("wochenplan_diaet", "Alle")
st.session_state.setdefault("wochenplan_portionen", 1)
st.session_state.setdefault("einkaufsliste", [])

TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

def zutaten_fuer_plan(plan, portionen=1):
    """Fasst Zutaten aller geplanten Rezepte zusammen und skaliert sie auf Portionen."""
    gesammelt = {}
    for rezept_name in plan.values():
        rezept = next((x for x in rezepte if titel(x) == rezept_name), None)
        if not rezept:
            continue
        basis = rezept.get("base_servings") or 1
        try:
            faktor = float(portionen) / float(basis)
        except (TypeError, ValueError, ZeroDivisionError):
            faktor = 1
        for z in rezept.get("ingredients", []):
            if not isinstance(z, dict):
                continue
            name = str(z.get("name") or "").strip()
            unit = str(z.get("unit") or "").strip()
            amount = z.get("amount")
            if not name:
                continue
            key = (name.casefold(), unit.casefold())
            if key not in gesammelt:
                gesammelt[key] = {"name": name, "unit": unit, "amount": 0.0, "unknown": False}
            try:
                if amount in (None, ""):
                    gesammelt[key]["unknown"] = True
                else:
                    gesammelt[key]["amount"] += float(amount) * faktor
            except (TypeError, ValueError):
                gesammelt[key]["unknown"] = True
    return list(gesammelt.values())

def format_menge(z):
    if z.get("unknown"):
        menge = "Menge nach Rezept"
    else:
        n = z.get("amount", 0)
        menge = str(int(n)) if float(n).is_integer() else f"{n:.1f}".rstrip("0").rstrip(".")
        menge = f"{menge} {z.get('unit', '')}".strip()
    return f"{menge} {z['name']}".strip()

# ---------- Design ----------
st.markdown("""
<style>
html, body, [class*="css"] { font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.stApp { background: #f8f5ee; color: #172018; }
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#111714 0%,#17201a 55%,#111714 100%);
    min-width: 265px !important;
}
section[data-testid="stSidebar"] > div { padding: 18px 14px 22px; }
section[data-testid="stSidebar"] { color: #f6f2e9; }
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .et-nav-title,
section[data-testid="stSidebar"] .et-brand,
section[data-testid="stSidebar"] .et-profile { color: #f6f2e9 !important; }

/* Navigation: high-contrast buttons on the dark sidebar.
   Do not apply the sidebar's light text color to white buttons. */
section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    width: 100% !important;
    min-height: 48px !important;
    margin: 3px 0 !important;
    padding: 10px 14px !important;
    border-radius: 13px !important;
    border: 1px solid #34483a !important;
    background: #202d24 !important;
    color: #f8f5ee !important;
    text-align: left !important;
    font-weight: 650 !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] > button p,
section[data-testid="stSidebar"] div[data-testid="stButton"] > button span {
    color: #f8f5ee !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
    background: #2d4935 !important;
    border-color: #d89b35 !important;
    color: #ffffff !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] > button:focus:not(:active) {
    border-color: #d89b35 !important;
    box-shadow: 0 0 0 2px rgba(216,155,53,.24) !important;
}
.et-brand {
    border-radius: 18px; padding: 18px 14px 14px; margin-bottom: 16px;
    background: linear-gradient(160deg,#1b241f,#0e120f);
    border: 1px solid rgba(255,255,255,.09);
    text-align:center;
}
.et-brand img { max-width: 190px; border-radius: 10px; }
.et-brand-title { font-size: 25px; font-weight: 800; letter-spacing:-.8px; }
.et-brand-sub { font-size: 10px; letter-spacing: 2.8px; opacity:.78; margin-top:2px; }
.et-nav-title { font-size: 12px; text-transform:uppercase; letter-spacing:1.5px; opacity:.55; margin:18px 4px 7px; }
.et-main-head {
    background: #173b28; color:white; border-radius: 0 0 26px 26px;
    padding: 28px 34px 24px; margin: -1rem -1rem 22px;
    box-shadow: 0 8px 26px rgba(20,50,35,.16);
}
.et-main-head h1 { margin:0; font-size:38px; letter-spacing:-1.5px; }
.et-main-head p { margin:5px 0 0; opacity:.78; }
.et-search {
    background:#fff; border:1px solid #e4ddd0; border-radius:16px;
    padding:12px 16px; margin:8px 0 16px;
}
.et-card {
    background:#fff; border:1px solid #e6dfd2; border-radius:18px;
    overflow:hidden; box-shadow:0 4px 15px rgba(30,35,30,.06);
    margin-bottom:16px;
}
.et-photo {
    height:178px; background:linear-gradient(135deg,#d7dfce 0%,#8ca18b 48%,#355b42 100%);
    display:flex; align-items:center; justify-content:center; color:#fff; font-size:48px;
}
.et-card:hover { transform: translateY(-2px); box-shadow:0 8px 22px rgba(30,35,30,.12); }
.et-card { transition: transform .15s ease, box-shadow .15s ease; }
.et-card-body { padding:14px 16px 16px; }
.et-card-title { font-size:18px; font-weight:800; margin-bottom:8px; color:#172018; }
.et-pill { display:inline-block; background:#eef3e9; color:#285c36; border-radius:999px; padding:5px 9px; font-size:11px; font-weight:700; }
.et-pill.orange { background:#fff0d8; color:#9a5a0c; }
.et-pill.blue { background:#e9f1f8; color:#286083; }
.et-detail {
    background:#fff; border:1px solid #e4ddd0; border-radius:22px; padding:22px;
    box-shadow:0 7px 22px rgba(30,35,30,.07);
}
.et-detail h1 { font-size:32px; margin:0 0 7px; letter-spacing:-1px; }
.et-nut { display:flex; gap:8px; flex-wrap:wrap; margin:14px 0 18px; }
.et-nut span { background:#f1f5ee; border-radius:12px; padding:10px 13px; font-size:13px; }
.et-section { font-size:19px; font-weight:800; margin:20px 0 9px; }
.et-steps { counter-reset: step; }
.et-step { margin:0 0 12px; padding:11px 12px 11px 44px; background:#faf8f3; border-radius:12px; position:relative; }
.et-step:before {
    counter-increment: step; content:counter(step);
    position:absolute; left:11px; top:11px; width:24px; height:24px; border-radius:50%;
    background:#d89b35; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:12px;
}
.et-bottom {
    margin-top:26px; background:#eee4d2; border-radius:22px; padding:17px 18px;
    display:flex; justify-content:space-around; gap:10px; text-align:center;
}
.et-stat strong { display:block; font-size:24px; }
.et-stat small { color:#65655e; }
.et-profile {
    margin-top:18px; border-radius:18px; overflow:hidden; background:#151b17;
    border:1px solid rgba(255,255,255,.08);
}
.et-profile img { width:100%; height:225px; object-fit:cover; object-position:center 28%; display:block; }
.et-profile div { padding:12px 14px 14px; }
.et-profile b { font-size:17px; }
.et-profile small { display:block; opacity:.62; margin-top:3px; }
div[data-testid="stButton"] > button {
    border-radius:12px !important; border:1px solid #ded6c8 !important;
    background:#fff !important; color:#1b2d21 !important; font-weight:700 !important;
}
div[data-testid="stButton"] > button:hover { border-color:#c58a2c !important; }
section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    background:#202d24 !important;
    color:#f8f5ee !important;
    border-color:#34483a !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
    background:#2d4935 !important;
    border-color:#d89b35 !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    if logo_uri:
        st.markdown(
            f'<div class="et-brand"><img src="{logo_uri}"><div class="et-brand-sub">EINFACH GUTES ESSEN</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="et-brand"><div class="et-brand-title">EinfachmitTimo</div><div class="et-brand-sub">EINFACH GUTES ESSEN</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="et-nav-title">Navigation</div>', unsafe_allow_html=True)
    nav = [
        ("⌂", "Startseite"),
        ("🍴", "Rezepte"),
        ("▧", "Rezeptkarten"),
        ("▣", "Wochenpläne"),
        ("♡", "Favoriten"),
        ("🛒", "Einkaufsliste"),
        ("▦", "Kategorien"),
        ("⌕", "Suche"),
        ("ⓘ", "Über EinfachmitTimo"),
    ]
    for icon, label in nav:
        active = st.session_state.seite == label or (label == "Rezepte" and st.session_state.seite == "Rezept")
        button_label = f"{'● ' if active else ''}{icon}   {label}"
        if st.button(button_label, key="nav_"+label, use_container_width=True):
            st.session_state.seite = label
            st.session_state.auswahl = None
            st.rerun()

    if portrait_uri:
        st.markdown(
            f'<div class="et-profile"><img src="{portrait_uri}"><div><b>EinfachmitTimo</b><small>Einfach gutes Essen</small></div></div>',
            unsafe_allow_html=True,
        )

# ---------- Seiten ----------
seite = st.session_state.seite

if seite == "Startseite":
    st.markdown('<div class="et-main-head"><h1>Einfach gutes Essen.</h1><p>Rezepte entdecken, planen und clever einkaufen.</p></div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    c1.metric("Rezepte", len(rezepte))
    c2.metric("Frühstück", sum(kategorie(r)=="Frühstück" for r in rezepte))
    c3.metric("Mittagessen", sum(kategorie(r)=="Mittagessen" for r in rezepte))
    st.markdown("### Deine Rezeptwelt")
    st.write("Nutze links Rezepte, Rezeptkarten, Wochenpläne, Favoriten und Einkaufsliste.")

elif seite in ("Rezepte", "Suche", "Kategorien", "Rezeptkarten"):
    st.markdown('<div class="et-main-head"><h1>Rezepte</h1><p>Entdecke deine Rezepte und öffne die vollständige Rezeptansicht.</p></div>', unsafe_allow_html=True)

    search = st.text_input("🔎 Rezepte durchsuchen …", value=st.session_state.suche, placeholder="z. B. Chicken, Pasta, Bowl …")
    st.session_state.suche = search

    f1,f2,f3 = st.columns(3)
    with f1:
        kat = st.selectbox("Kategorie", ["Alle","Frühstück","Mittagessen","Abendessen"])
    with f2:
        diet = st.selectbox("Ernährung", ["Alle","vegetarisch","vegan","fisch","fleisch"])
    with f3:
        show_fav = st.checkbox("Nur Favoriten")

    filtered = rezepte
    if kat != "Alle":
        filtered = [r for r in filtered if kategorie(r)==kat]
    if diet != "Alle":
        filtered = [r for r in filtered if diat(r).lower()==diet]
    if search.strip():
        q = search.lower().strip()
        filtered = [r for r in filtered if q in titel(r).lower()]
    if show_fav:
        filtered = [r for r in filtered if titel(r) in st.session_state.favoriten]

    st.caption(f"{len(filtered)} Rezepte")

    cols = st.columns(3)
    for i,r in enumerate(filtered):
        with cols[i % 3]:
            # Sichere Platzhalter statt falsch zugeordneter Rezeptbilder.
            emoji = "🥣" if kategorie(r)=="Frühstück" else ("🍲" if kategorie(r)=="Mittagessen" else "🥗")
            st.markdown(
                f'<div class="et-card"><div class="et-photo">{emoji}</div><div class="et-card-body">'
                f'<div class="et-card-title">{html.escape(titel(r))}</div>'
                f'<span class="et-pill">{html.escape(kategorie(r))}</span></div></div>',
                unsafe_allow_html=True
            )
            if st.button("Rezept öffnen", key=f"open_{i}_{titel(r)}", use_container_width=True):
                st.session_state.auswahl = titel(r)
                st.session_state.seite = "Rezept"
                st.rerun()

elif seite == "Rezept":
    r = next((x for x in rezepte if titel(x)==st.session_state.auswahl), None)
    if not r:
        st.session_state.seite = "Rezepte"
        st.rerun()

    st.markdown('<div class="et-main-head"><h1>Rezept</h1><p>Alles auf einen Blick.</p></div>', unsafe_allow_html=True)
    if st.button("← Zurück zu den Rezepten"):
        st.session_state.seite = "Rezepte"
        st.rerun()

    left,right = st.columns([1.05,1.25], gap="large")
    with left:
        emoji = "🥣" if kategorie(r)=="Frühstück" else ("🍲" if kategorie(r)=="Mittagessen" else "🥗")
        st.markdown(f'<div class="et-detail"><div class="et-photo" style="height:360px;border-radius:16px">{emoji}</div></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="et-detail">', unsafe_allow_html=True)
        st.markdown(f"# {html.escape(titel(r))}")
        st.markdown(f'<span class="et-pill">{html.escape(kategorie(r))}</span>', unsafe_allow_html=True)
        nv = naehrwerte(r)
        st.markdown(
            '<div class="et-nut">'
            f'<span>🔥 <b>{nv.get("kcal","–")}</b> kcal</span>'
            f'<span>💪 <b>{nv.get("protein","–")}</b> g Protein</span>'
            f'<span>🍚 <b>{nv.get("carbs","–")}</b> g Kohlenhydrate</span>'
            f'<span>🥑 <b>{nv.get("fat","–")}</b> g Fett</span>'
            '</div>',
            unsafe_allow_html=True
        )
        if st.button("♡ Favorit" if titel(r) not in st.session_state.favoriten else "♥ Favorit", key="fav_detail"):
            if titel(r) in st.session_state.favoriten:
                st.session_state.favoriten.remove(titel(r))
            else:
                st.session_state.favoriten.add(titel(r))
            st.rerun()

        st.markdown('<div class="et-section">Zutaten</div>', unsafe_allow_html=True)
        for z in r.get("ingredients", []):
            if isinstance(z, dict):
                a = z.get("amount")
                u = z.get("unit") or ""
                n = z.get("name") or ""
                amount = "" if a in (None,"") else str(a)
                st.write(f"**{amount} {u}** {n}".strip())

        st.markdown('<div class="et-section">Zubereitung</div>', unsafe_allow_html=True)
        steps = "".join(f'<div class="et-step">{html.escape(str(s))}</div>' for s in zubereitung(r))
        st.markdown(f'<div class="et-steps">{steps}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif seite == "Favoriten":
    favs = [r for r in rezepte if titel(r) in st.session_state.favoriten]
    st.markdown('<div class="et-main-head"><h1>Favoriten</h1><p>Deine gespeicherten Rezepte.</p></div>', unsafe_allow_html=True)
    if not favs:
        st.info("Noch keine Favoriten gespeichert.")
    else:
        for r in favs:
            if st.button(titel(r), key="fav_"+titel(r)):
                st.session_state.auswahl = titel(r)
                st.session_state.seite = "Rezept"
                st.rerun()

elif seite == "Wochenpläne":
    st.markdown('<div class="et-main-head"><h1>Wochenplan</h1><p>Plane sieben warme Hauptgerichte – manuell oder automatisch.</p></div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("### Einstellungen")
        e1, e2 = st.columns(2)
        with e1:
            diaet_plan = st.selectbox(
                "Ernährungsform",
                ["Alle", "fleisch", "fisch", "vegetarisch", "vegan"],
                index=["Alle", "fleisch", "fisch", "vegetarisch", "vegan"].index(st.session_state.wochenplan_diaet),
                key="plan_diaet_select",
            )
            st.session_state.wochenplan_diaet = diaet_plan
        with e2:
            portionen_plan = st.number_input(
                "Portionen pro Gericht",
                min_value=1, max_value=12,
                value=int(st.session_state.wochenplan_portionen),
                step=1,
                key="plan_portionen_select",
            )
            st.session_state.wochenplan_portionen = int(portionen_plan)

        st.caption("Der Plan enthält standardmäßig ein warmes Hauptgericht pro Tag. Du kannst jeden Tag anschließend selbst ändern.")
        p1, p2 = st.columns(2)
        with p1:
            automatisch = st.button("✨ Woche automatisch planen", use_container_width=True, type="primary")
        with p2:
            leer = st.button("Plan leeren", use_container_width=True)

    passende = [r for r in rezepte if kategorie(r).lower() in ("mittagessen", "hauptgericht", "lunch")]
    if diaet_plan != "Alle":
        passende = [r for r in passende if diat(r).lower() == diaet_plan.lower()]
    if not passende:
        passende = [r for r in rezepte if diaet_plan == "Alle" or diat(r).lower() == diaet_plan.lower()]

    if leer:
        st.session_state.wochenplan = {}
        st.session_state.einkaufsliste = []
        st.rerun()

    if automatisch:
        import random
        pool = passende[:]
        random.shuffle(pool)
        if len(pool) >= len(TAGE):
            auswahl_woche = pool[:len(TAGE)]
        else:
            auswahl_woche = [random.choice(pool) for _ in TAGE] if pool else []
        st.session_state.wochenplan = {
            tag: titel(auswahl_woche[i]) for i, tag in enumerate(TAGE)
        } if auswahl_woche else {}
        st.session_state.einkaufsliste = zutaten_fuer_plan(
            st.session_state.wochenplan, st.session_state.wochenplan_portionen
        )
        st.rerun()

    st.markdown("### Deine Woche")
    if not passende:
        st.warning("Für diese Ernährungsform wurden keine passenden Rezepte gefunden.")
    else:
        options = ["— Gericht auswählen —"] + [titel(r) for r in passende]
        plan_neu = dict(st.session_state.wochenplan)
        for tag in TAGE:
            aktuelle = plan_neu.get(tag, "— Gericht auswählen —")
            index = options.index(aktuelle) if aktuelle in options else 0
            selected = st.selectbox(
                f"{tag} · warmes Hauptgericht",
                options,
                index=index,
                key=f"wochenplan_{tag}",
            )
            if selected == "— Gericht auswählen —":
                plan_neu.pop(tag, None)
            else:
                plan_neu[tag] = selected

        if st.button("💾 Wochenplan speichern", use_container_width=True, type="primary"):
            st.session_state.wochenplan = plan_neu
            st.session_state.einkaufsliste = zutaten_fuer_plan(
                plan_neu, st.session_state.wochenplan_portionen
            )
            st.success("Wochenplan gespeichert. Die Einkaufsliste wurde aktualisiert.")
            st.rerun()

    if st.session_state.wochenplan:
        st.markdown("### Zusammenfassung")
        for tag in TAGE:
            gericht = st.session_state.wochenplan.get(tag)
            if gericht:
                st.write(f"**{tag}:** {gericht}")
        st.caption("Die Einkaufsliste wird aus den gespeicherten Gerichten und der gewählten Portionszahl erstellt.")

elif seite == "Einkaufsliste":
    st.markdown('<div class="et-main-head"><h1>Einkaufsliste</h1><p>Automatisch aus deinem gespeicherten Wochenplan zusammengestellt.</p></div>', unsafe_allow_html=True)
    if not st.session_state.wochenplan:
        st.info("Erstelle zuerst unter „Wochenpläne“ einen Plan. Danach erscheinen hier die benötigten Zutaten.")
    else:
        st.caption(f"Für {st.session_state.wochenplan_portionen} Portion(en) pro Gericht")
        einkauf = zutaten_fuer_plan(st.session_state.wochenplan, st.session_state.wochenplan_portionen)
        st.session_state.einkaufsliste = einkauf
        for z in einkauf:
            st.checkbox(format_menge(z), key="einkauf_" + re.sub(r"[^a-zA-Z0-9]", "_", z["name"] + z["unit"]))
        if st.button("Einkaufsliste als Text anzeigen"):
            st.code("\\n".join(format_menge(z) for z in einkauf), language=None)

elif seite == "Über EinfachmitTimo":
    st.markdown('<div class="et-main-head"><h1>Über EinfachmitTimo</h1><p>Einfach gutes Essen.</p></div>', unsafe_allow_html=True)
    if portrait_uri:
        st.image(str(PORTRAIT_FILE), width=260)
    st.write("Rezepte, Wochenplanung und cleveres Einkaufen in einer App.")

# ---------- Footer ----------
st.markdown(
    f'<div class="et-bottom">'
    f'<div class="et-stat"><strong>{len(rezepte)}</strong><small>Rezepte</small></div>'
    f'<div class="et-stat"><strong>{sum(kategorie(r)=="Frühstück" for r in rezepte)}</strong><small>Frühstück</small></div>'
    f'<div class="et-stat"><strong>{sum(kategorie(r)=="Mittagessen" for r in rezepte)}</strong><small>Mittagessen</small></div>'
    f'<div class="et-stat"><strong>{sum(kategorie(r)=="Abendessen" for r in rezepte)}</strong><small>Abendessen</small></div>'
    f'<div class="et-stat"><strong>{len(rezepte)}</strong><small>Rezeptkarten</small></div>'
    f'</div>',
    unsafe_allow_html=True,
)
