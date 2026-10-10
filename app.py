import base64
import html
import json
import random
import re
from pathlib import Path

import requests
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
RECIPES_FILE = BASE_DIR / "recipes.json"
LOGO_FILE = BASE_DIR / "EinfachmitTimo_Logo.jpg"
PORTRAIT_FILE = BASE_DIR / "Timo_Portrait.jpg"

st.set_page_config(page_title="EinfachmitTimo – Einfach gutes Essen", page_icon="🍽️", layout="wide", initial_sidebar_state="expanded")

MARKETS = ["Lidl", "ALDI SÜD", "ALDI Nord", "PENNY", "Netto Marken-Discount", "NORMA", "REWE", "EDEKA", "Kaufland"]
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

MARKTGURU_API_URL = "https://api.marktguru.de/api/v1/offers/search"
MARKTGURU_RETAILERS = {
    "Lidl": "lidl",
    "ALDI SÜD": "aldi-sued",
    "ALDI Nord": "aldi-nord",
    "PENNY": "penny",
    "Netto Marken-Discount": "netto",
    "NORMA": "norma",
    "REWE": "rewe",
    "EDEKA": "edeka",
    "Kaufland": "kaufland",
}

def marktguru_headers():
    """Liest Zugangsdaten ausschließlich aus Streamlit Secrets."""
    try:
        config = st.secrets["marktguru"]
        clientkey = str(config["clientkey"]).strip()
        apikey = str(config["apikey"]).strip()
    except Exception:
        return None
    if not clientkey or not apikey:
        return None
    return {"x-clientkey": clientkey, "x-apikey": apikey}

@st.cache_data(ttl=3600, show_spinner=False)
def marktguru_angebot(zutat, plz, markt):
    """Sucht ein passendes aktuelles Angebot für eine Zutat und einen Markt."""
    headers = marktguru_headers()
    if not headers:
        return {"error": "Marktguru-Zugangsdaten fehlen. Bitte [marktguru] mit clientkey und apikey in den Streamlit Secrets hinterlegen."}
    params = {"as": "web", "limit": 20, "offset": 0, "q": str(zutat), "zipCode": str(plz)}
    try:
        response = requests.get(MARKTGURU_API_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return {"error": "Die Marktguru-Schnittstelle ist aktuell nicht erreichbar."}
    except ValueError:
        return {"error": "Marktguru hat keine gültige JSON-Antwort geliefert."}

    target = MARKTGURU_RETAILERS.get(markt, "")
    offers = []
    for result in payload.get("results", []) if isinstance(payload, dict) else []:
        price = result.get("price")
        if price is None:
            continue
        for advertiser in result.get("advertisers", []) or []:
            unique = str(advertiser.get("uniqueName", "")).casefold()
            name = str(advertiser.get("name", "")).strip()
            # Exact retailer identifier first; fall back to a conservative name match.
            matches = unique == target.casefold() if target else False
            if not matches and name:
                norm_name = name.casefold()
                aliases = {
                    "ALDI SÜD": ("aldi süd", "aldi sud"),
                    "ALDI Nord": ("aldi nord",),
                    "Netto Marken-Discount": ("netto",),
                }.get(markt, (markt.casefold(),))
                matches = any(alias in norm_name for alias in aliases)
            if not matches:
                continue
            try:
                numeric_price = float(str(price).replace(",", "."))
            except (TypeError, ValueError):
                continue
            offers.append({
                "description": str(result.get("description") or result.get("name") or zutat),
                "price": numeric_price,
                "retailer": name or markt,
                "url": str(result.get("url") or result.get("webUrl") or ""),
            })
    if not offers:
        return {"not_found": True}
    return min(offers, key=lambda item: item["price"])

@st.cache_data
def load_recipes():
    if not RECIPES_FILE.exists():
        return []
    try:
        with RECIPES_FILE.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []

recipes = load_recipes()

def title(r):
    return str(r.get("name") or r.get("titel") or "Rezept ohne Titel").strip()

def category(r):
    return str(r.get("kategorie") or r.get("category") or "Mittagessen").strip()

def diet(r):
    value = r.get("diet") or r.get("ernaehrung") or "Alles"
    if isinstance(value, (list, tuple, set)):
        value = next(iter(value), "Alles")
    text = str(value).strip().lower()
    # Manche importierten Rezepte speichern die Ernährungsform als Liste-Text.
    text = text.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    return text.split(",")[0].strip()

def steps_for(r):
    p = r.get("zubereitung") or r.get("preparation") or r.get("instructions") or r.get("steps") or []
    return p if isinstance(p, list) else [str(p)]

def nutrition(r):
    n = r.get("nutrition") or {}
    text = str(r.get("nutrition_source") or "")
    out = {"kcal": n.get("kcal", "–"), "protein": n.get("protein", "–"), "carbs": n.get("carbs", "–"), "fat": n.get("fat", "–")}
    patterns = {"kcal": r"([0-9]+(?:[.,][0-9]+)?)\s*kcal", "protein": r"([0-9]+(?:[.,][0-9]+)?)\s*g?\s*Protein", "carbs": r"([0-9]+(?:[.,][0-9]+)?)\s*g?\s*Kohlenhydrate", "fat": r"([0-9]+(?:[.,][0-9]+)?)\s*g?\s*Fett"}
    for k, pat in patterns.items():
        if out[k] == "–":
            m = re.search(pat, text, re.I)
            if m: out[k] = m.group(1).replace(",", ".")
    return out

def image_uri(path):
    try:
        return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""

def category_emoji(r):
    c = category(r).lower()
    name = title(r).lower()
    if any(x in name for x in ("pancake", "porridge", "oat", "skyr", "chia", "müsli", "frühstück", "omelett", "rührei")) or c == "frühstück":
        return "🥣"
    if any(x in name for x in ("lachs", "thunfisch", "fisch", "garnelen")):
        return "🐟"
    if any(x in name for x in ("hähnchen", "chicken", "pute", "döner")):
        return "🍗"
    if any(x in name for x in ("salat", "bowl")):
        return "🥗"
    if any(x in name for x in ("pasta", "nudel", "lasagne", "reis", "risotto")):
        return "🍝"
    return "🍲"

def scaled_ingredients(r, portions):
    base = r.get("base_servings") or 1
    try: factor = float(portions) / float(base)
    except (ValueError, TypeError, ZeroDivisionError): factor = 1
    result = []
    for z in r.get("ingredients", []):
        if not isinstance(z, dict):
            result.append(str(z)); continue
        name = str(z.get("name") or "").strip()
        amount = z.get("amount")
        unit = str(z.get("unit") or "").strip()
        if amount in (None, ""):
            quantity = "Menge nach Rezept"
        else:
            try:
                n = float(amount) * factor
                quantity = str(int(n)) if n.is_integer() else f"{n:.1f}".rstrip("0").rstrip(".")
            except (TypeError, ValueError):
                quantity = str(amount)
            quantity = f"{quantity} {unit}".strip()
        result.append(f"{quantity} {name}".strip())
    return result

def ingredients_for_plan(plan, portions):
    merged = {}
    by_title = {title(r): r for r in recipes}
    for recipe_title in plan.values():
        r = by_title.get(recipe_title)
        if not r: continue
        base = r.get("base_servings") or 1
        try: factor = float(portions) / float(base)
        except (TypeError, ValueError, ZeroDivisionError): factor = 1
        for z in r.get("ingredients", []):
            if not isinstance(z, dict): continue
            name = str(z.get("name") or "").strip()
            unit = str(z.get("unit") or "").strip()
            if not name: continue
            key = (name.casefold(), unit.casefold())
            merged.setdefault(key, {"name": name, "unit": unit, "amount": 0.0, "unknown": False})
            try:
                if z.get("amount") in (None, ""): merged[key]["unknown"] = True
                else: merged[key]["amount"] += float(z.get("amount")) * factor
            except (ValueError, TypeError): merged[key]["unknown"] = True
    return list(merged.values())

def ingredient_label(z):
    if z["unknown"]: amount = "Menge nach Rezept"
    else:
        n = z["amount"]
        amount = str(int(n)) if float(n).is_integer() else f"{n:.1f}".rstrip("0").rstrip(".")
        amount = f"{amount} {z['unit']}".strip()
    return f"{amount} {z['name']}".strip()

def render_detail(r, compact=False):
    st.markdown(f'<div class="detail-top"><div class="detail-visual">{category_emoji(r)}</div><div class="detail-copy"><div class="pill">{html.escape(category(r))}</div><h2>{html.escape(title(r))}</h2><p>Einfach. Schnell. Lecker.</p></div></div>', unsafe_allow_html=True)
    nv = nutrition(r)
    st.markdown('<div class="nutrition-grid">' + ''.join([
        f'<div><strong>🔥 {html.escape(str(nv["kcal"]))}</strong><small>kcal</small></div>',
        f'<div><strong>💪 {html.escape(str(nv["protein"]))} g</strong><small>Protein</small></div>',
        f'<div><strong>🌾 {html.escape(str(nv["carbs"]))} g</strong><small>Kohlenhydrate</small></div>',
        f'<div><strong>💧 {html.escape(str(nv["fat"]))} g</strong><small>Fett</small></div>'
    ]) + '</div>', unsafe_allow_html=True)
    portions = st.number_input("Portionen", min_value=1, max_value=20, value=2, step=1, key="detail_portions_" + re.sub(r"\W+", "_", title(r)))
    left, right = st.columns(2)
    with left:
        st.markdown("#### Zutaten")
        for item in scaled_ingredients(r, portions): st.markdown(f"- {html.escape(item)}")
    with right:
        st.markdown("#### Zubereitung")
        steps = steps_for(r)
        for i, s in enumerate(steps, 1):
            st.markdown(f'<div class="step"><b>{i}</b><span>{html.escape(str(s))}</span></div>', unsafe_allow_html=True)
    if st.button("♡ Zu Favoriten hinzufügen" if title(r) not in st.session_state.favorites else "♥ Aus Favoriten entfernen", key="fav_toggle_" + re.sub(r"\W+", "_", title(r))):
        if title(r) in st.session_state.favorites: st.session_state.favorites.remove(title(r))
        else: st.session_state.favorites.add(title(r))
        st.rerun()

# State
st.session_state.setdefault("page", "Rezepte")
st.session_state.setdefault("selected_recipe", title(recipes[0]) if recipes else None)
st.session_state.setdefault("favorites", set())
st.session_state.setdefault("search", "")
st.session_state.setdefault("market", "Lidl")
st.session_state.setdefault("postcode", "89584")
st.session_state.setdefault("diet_filter", "Alle")
st.session_state.setdefault("portions", 2)
st.session_state.setdefault("week_plan", {})
st.session_state.setdefault("week_diet", "Alle")
st.session_state.setdefault("week_portions", 2)
st.session_state.setdefault("shopping_checked", set())
st.session_state.setdefault("marketguru_offers", {})
st.session_state.setdefault("marketguru_error", "")

# Styling
st.markdown("""
<style>
:root{--forest:#173b28;--forest2:#102319;--cream:#f8f5ee;--gold:#d89b35;--line:#e5ddcf;--ink:#202720}
.stApp{background:var(--cream);color:var(--ink);font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
[data-testid="stHeader"]{background:rgba(248,245,238,.94)}
.block-container{padding-top:1rem;padding-bottom:1rem;max-width:1700px}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#101713,#17231b 70%,#101713);min-width:260px!important}
section[data-testid="stSidebar"]>div{padding:15px 13px 20px}
section[data-testid="stSidebar"] p,section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] small{color:#f6f2e9!important}
.brand{padding:13px 10px 15px;border-radius:17px;background:#101511;border:1px solid #344238;text-align:center;margin-bottom:12px}
.brand img{width:100%;max-width:210px;border-radius:10px}
.brand small{display:block;color:#e6dfd0;letter-spacing:2.3px;font-size:9px;margin-top:6px}
.nav-heading{color:#b8c2b9;letter-spacing:2px;text-transform:uppercase;font-size:11px;margin:22px 6px 8px}
section[data-testid="stSidebar"] div[data-testid="stButton"]>button{background:#202d24!important;color:#f8f5ee!important;border:1px solid #34483a!important;border-radius:12px!important;text-align:left!important;min-height:42px!important;font-weight:650!important}
section[data-testid="stSidebar"] div[data-testid="stButton"]>button:hover{background:#2d4935!important;border-color:var(--gold)!important}
.sidebar-profile{margin-top:16px;background:#0f1511;border:1px solid #344238;border-radius:15px;overflow:hidden}
.sidebar-profile img{width:100%;height:190px;object-fit:cover;object-position:center 30%;display:block}
.sidebar-profile div{padding:10px 12px;color:#fff}.sidebar-profile small{opacity:.7}
.et-header{background:linear-gradient(120deg,#153b28,#20573a);color:#fff;padding:25px 28px;border-radius:0 0 24px 24px;margin:-.5rem -1rem 20px;box-shadow:0 8px 25px #142d1b22}
.et-header h1{font-size:32px;margin:0;letter-spacing:-1px}.et-header p{margin:5px 0 0;color:#d8e5d9}
.section-label{font-size:12px;letter-spacing:1.5px;text-transform:uppercase;color:#77796f;font-weight:800;margin:8px 0}
.recipe-card{background:white;border:1px solid var(--line);border-radius:15px;overflow:hidden;margin-bottom:9px;box-shadow:0 3px 12px #1720180b}
.recipe-visual{height:105px;background:linear-gradient(135deg,#dbe5d5,#a5b99d 48%,#42694d);display:flex;align-items:center;justify-content:center;font-size:44px}
.recipe-card-body{padding:10px 11px 12px}.recipe-card-title{font-size:14px;font-weight:800;line-height:1.25;min-height:36px;color:#202720}
.pill{display:inline-block;background:#eef3e9;color:#285c36;border-radius:999px;padding:4px 8px;font-size:10px;font-weight:800}
.pill.gold{background:#fff0d8;color:#9a5a0c}
.detail-panel{background:#fff;border:1px solid var(--line);border-radius:20px;padding:16px;box-shadow:0 5px 18px #1720180c}
.detail-top{display:flex;gap:13px;align-items:center;margin-bottom:12px}.detail-visual{width:105px;min-width:105px;height:100px;border-radius:15px;background:linear-gradient(135deg,#dbe5d5,#779b78,#234f35);display:flex;align-items:center;justify-content:center;font-size:48px}
.detail-copy h2{font-size:23px;line-height:1.08;margin:7px 0 5px;letter-spacing:-.6px}.detail-copy p{font-size:12px;color:#6c726a;margin:0}
.nutrition-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin:12px 0 18px}.nutrition-grid>div{background:#f2f5ed;border-radius:10px;padding:9px 5px;text-align:center}.nutrition-grid strong{font-size:13px;display:block}.nutrition-grid small{font-size:10px;color:#6e746b}
.step{display:flex;gap:9px;align-items:flex-start;background:#faf8f3;border-radius:9px;padding:8px;margin:7px 0;font-size:12px}.step b{background:#d89b35;color:white;min-width:23px;height:23px;border-radius:50%;display:flex;align-items:center;justify-content:center}.step span{padding-top:3px}
.et-bottom{margin-top:22px;background:#eee4d2;border-radius:18px;padding:15px 8px;display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px;text-align:center}.et-stat strong{display:block;font-size:22px}.et-stat small{color:#65655e;font-size:11px}
div[data-testid="stButton"]>button{border-radius:10px!important;border:1px solid #ded6c8!important;background:#fff!important;color:#1b2d21!important;font-weight:700!important}div[data-testid="stButton"]>button:hover{border-color:var(--gold)!important}
@media(max-width:1000px){.nutrition-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.et-bottom{grid-template-columns:repeat(3,minmax(0,1fr))}.detail-top{align-items:flex-start}.detail-copy h2{font-size:20px}}
</style>
""", unsafe_allow_html=True)

logo = image_uri(LOGO_FILE)
portrait = image_uri(PORTRAIT_FILE)
with st.sidebar:
    if logo:
        st.markdown(f'<div class="brand"><img src="{logo}"><small>EINFACH GUTES ESSEN</small></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="brand"><h2 style="color:white">EinfachmitTimo</h2><small>EINFACH GUTES ESSEN</small></div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-heading">Navigation</div>', unsafe_allow_html=True)
    navigation = [("⌂", "Startseite"), ("🍴", "Rezepte"), ("▧", "Rezeptkarten"), ("▣", "Wochenpläne"), ("♡", "Favoriten"), ("🛒", "Einkaufsliste"), ("▦", "Kategorien"), ("⌕", "Suche"), ("ⓘ", "Über EinfachmitTimo")]
    for icon, label in navigation:
        if st.button(f"{icon}  {label}{'  •' if st.session_state.page == label else ''}", key="nav_" + label, use_container_width=True):
            st.session_state.page = label
            st.rerun()
    st.markdown('<div class="nav-heading">Einkaufen</div>', unsafe_allow_html=True)
    st.session_state.market = st.selectbox("Markt auswählen", MARKETS, index=MARKETS.index(st.session_state.market) if st.session_state.market in MARKETS else 0, key="sidebar_market")
    st.session_state.postcode = st.text_input("Postleitzahl", value=st.session_state.postcode, max_chars=5, key="sidebar_postcode")
    st.caption("Der ausgewählte Markt wird im Wochenplan und in der Einkaufsliste angezeigt.")
    if portrait:
        st.markdown(f'<div class="sidebar-profile"><img src="{portrait}"><div><b>EinfachmitTimo</b><br><small>Einfach gutes Essen</small></div></div>', unsafe_allow_html=True)

page = st.session_state.page

if page == "Startseite":
    st.markdown('<div class="et-header"><h1>Einfach gutes Essen.</h1><p>Rezepte entdecken, Wochen planen und clever einkaufen.</p></div>', unsafe_allow_html=True)
    st.markdown("### Deine Rezeptwelt")
    a,b,c,d = st.columns(4)
    a.metric("Rezepte", len(recipes)); b.metric("Frühstück", sum(category(r).lower()=="frühstück" for r in recipes)); c.metric("Mittagessen", sum(category(r).lower()=="mittagessen" for r in recipes)); d.metric("Abendessen", sum(category(r).lower()=="abendessen" for r in recipes))
    x,y = st.columns(2)
    with x:
        if st.button("🍴 Rezepte entdecken", use_container_width=True): st.session_state.page="Rezepte"; st.rerun()
    with y:
        if st.button("▣ Wochenplan erstellen", use_container_width=True): st.session_state.page="Wochenpläne"; st.rerun()

elif page in ("Rezepte", "Rezeptkarten", "Kategorien", "Suche", "Favoriten"):
    heading = "Favoriten" if page == "Favoriten" else ("Rezeptkarten" if page == "Rezeptkarten" else "Rezepte")
    st.markdown(f'<div class="et-header"><h1>{heading}</h1><p>Entdecke deine Rezepte – mit Zutaten, Zubereitung und Nährwerten.</p></div>', unsafe_allow_html=True)
    search = st.text_input("🔎 Rezepte durchsuchen", value=st.session_state.search, placeholder="z. B. Chicken, Pasta, Bowl …", key="recipe_search")
    st.session_state.search = search
    f1,f2,f3 = st.columns([1,1,1])
    with f1: cat = st.selectbox("Kategorie", ["Alle", "Frühstück", "Mittagessen", "Abendessen"], key="recipe_category")
    with f2: diet_filter = st.selectbox("Ernährung", ["Alle", "vegetarisch", "vegan", "fisch", "fleisch"], key="recipe_diet")
    with f3: sort_by = st.selectbox("Sortierung", ["A–Z", "Neueste zuerst"], key="recipe_sort")
    filtered = recipes[:]
    if page == "Favoriten": filtered = [r for r in filtered if title(r) in st.session_state.favorites]
    if cat != "Alle": filtered = [r for r in filtered if category(r).lower() == cat.lower()]
    if diet_filter != "Alle": filtered = [r for r in filtered if diet(r) == diet_filter]
    if search.strip(): filtered = [r for r in filtered if search.lower().strip() in title(r).lower()]
    if sort_by == "A–Z": filtered.sort(key=lambda r: title(r).casefold())
    if not filtered:
        st.info("Keine Rezepte gefunden. Ändere deine Suche oder Filter.")
    else:
        current_titles = [title(r) for r in filtered]
        if st.session_state.selected_recipe not in current_titles: st.session_state.selected_recipe = current_titles[0]
        left, right = st.columns([1.15, 1], gap="large")
        with left:
            st.markdown(f'<div class="section-label">{len(filtered)} Rezepte</div>', unsafe_allow_html=True)
            cols = st.columns(3)
            for i, r in enumerate(filtered):
                with cols[i % 3]:
                    selected = title(r) == st.session_state.selected_recipe
                    st.markdown(f'<div class="recipe-card" style="border-color:{"#d89b35" if selected else "#e5ddcf"}"><div class="recipe-visual">{category_emoji(r)}</div><div class="recipe-card-body"><div class="recipe-card-title">{html.escape(title(r))}</div><span class="pill">{html.escape(category(r))}</span></div></div>', unsafe_allow_html=True)
                    if st.button("Ausgewählt ✓" if selected else "Rezept ansehen", key=f"select_{page}_{i}_{re.sub(r'[^a-zA-Z0-9]', '_', title(r))}", use_container_width=True):
                        st.session_state.selected_recipe = title(r); st.rerun()
        with right:
            chosen = next((r for r in filtered if title(r) == st.session_state.selected_recipe), filtered[0])
            st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
            render_detail(chosen, compact=True)
            st.markdown('</div>', unsafe_allow_html=True)

elif page == "Wochenpläne":
    st.markdown('<div class="et-header"><h1>Wochenplan</h1><p>Plane deine Woche, wähle deinen Supermarkt und erstelle direkt die Einkaufsliste.</p></div>', unsafe_allow_html=True)
    st.markdown("### Einstellungen")
    c1,c2,c3 = st.columns(3)
    with c1:
        market_plan = st.selectbox("Markt für diese Woche", MARKETS, index=MARKETS.index(st.session_state.market) if st.session_state.market in MARKETS else 0, key="week_market")
        st.session_state.market = market_plan
    with c2:
        postcode_plan = st.text_input("Postleitzahl", value=st.session_state.postcode, max_chars=5, key="week_postcode")
        st.session_state.postcode = postcode_plan
    with c3:
        st.session_state.week_portions = int(st.number_input("Portionen pro Gericht", min_value=1, max_value=12, value=int(st.session_state.week_portions), step=1, key="week_portion_count"))
    c4,c5 = st.columns(2)
    with c4: st.session_state.week_diet = st.selectbox("Ernährungsform", ["Alle", "fleisch", "fisch", "vegetarisch", "vegan"], index=["Alle", "fleisch", "fisch", "vegetarisch", "vegan"].index(st.session_state.week_diet), key="week_diet_select")
    with c5:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        auto = st.button("✨ Woche automatisch planen", type="primary", use_container_width=True)
    st.caption("Die automatische Planung nutzt deine Rezeptdatenbank und die gewählte Ernährungsform. Eine Live-Angebotsoptimierung benötigt eine konfigurierte Angebots-API.")
    pool = [r for r in recipes if category(r).lower() in ("mittagessen", "abendessen", "hauptgericht", "lunch")]
    if st.session_state.week_diet != "Alle": pool = [r for r in pool if diet(r) == st.session_state.week_diet]
    if not pool: pool = [r for r in recipes if st.session_state.week_diet == "Alle" or diet(r) == st.session_state.week_diet]
    if auto:
        shuffled = pool[:]
        random.shuffle(shuffled)
        picked = []
        seen = set()
        for r in shuffled:
            if title(r) not in seen:
                picked.append(r); seen.add(title(r))
            if len(picked) == 7: break
        st.session_state.week_plan = {TAGE[i]: title(r) for i, r in enumerate(picked)}
        # Alte Formularwerte entfernen, damit die neuen Gerichte sofort angezeigt werden.
        for day in TAGE:
            st.session_state.pop(f"week_choice_{day}", None)
        st.rerun()
    st.markdown("### Deine Woche")
    options = ["— Gericht auswählen —"] + [title(r) for r in pool]
    planned = dict(st.session_state.week_plan)
    with st.form("weekly_plan_form"):
        cols = st.columns(2)
        for i, day in enumerate(TAGE):
            with cols[i % 2]:
                old = planned.get(day, "— Gericht auswählen —")
                idx = options.index(old) if old in options else 0
                choice = st.selectbox(f"{day} · warmes Hauptgericht", options, index=idx, key=f"week_choice_{day}")
                if choice == "— Gericht auswählen —": planned.pop(day, None)
                else: planned[day] = choice
        save = st.form_submit_button("💾 Wochenplan speichern", type="primary", use_container_width=True)
    if save:
        st.session_state.week_plan = planned
        st.success("Wochenplan gespeichert. Deine Einkaufsliste wurde aktualisiert.")
        st.rerun()
    if st.session_state.week_plan:
        st.markdown("### Wochenübersicht")
        for day in TAGE:
            recipe_name = st.session_state.week_plan.get(day)
            if recipe_name: st.markdown(f"**{day}:** {recipe_name}")
        st.info(f"Einkauf für **{st.session_state.week_portions} Portion(en)** bei **{st.session_state.market}** · PLZ {st.session_state.postcode}")
        if st.button("🛒 Zur Einkaufsliste", use_container_width=True): st.session_state.page = "Einkaufsliste"; st.rerun()
    else:
        st.info("Wähle Gerichte für die einzelnen Tage oder klicke auf „Woche automatisch planen“.")

elif page == "Einkaufsliste":
    st.markdown('<div class="et-header"><h1>Einkaufsliste</h1><p>Alle Zutaten aus deinem Wochenplan, nach Menge zusammengefasst.</p></div>', unsafe_allow_html=True)
    st.markdown(f"**Supermarkt:** {st.session_state.market} &nbsp; · &nbsp; **PLZ:** {html.escape(st.session_state.postcode)} &nbsp; · &nbsp; **Portionen:** {st.session_state.week_portions}", unsafe_allow_html=True)
    if not st.session_state.week_plan:
        st.info("Erstelle zuerst unter „Wochenpläne“ deinen Plan.")
    else:
        items = ingredients_for_plan(st.session_state.week_plan, st.session_state.week_portions)
        st.caption(f"{len(items)} unterschiedliche Zutaten")
        if st.button("🏷️ Marktguru-Angebote für diese Einkaufsliste suchen", type="primary", use_container_width=True):
            headers_ok = marktguru_headers()
            if not headers_ok:
                st.session_state.marketguru_error = "Marktguru-Zugangsdaten fehlen. Bitte die Secrets im Streamlit-Deployment prüfen."
                st.session_state.marketguru_offers = {}
            elif not re.fullmatch(r"\d{5}", str(st.session_state.postcode).strip()):
                st.session_state.marketguru_error = "Bitte eine gültige fünfstellige Postleitzahl eingeben."
                st.session_state.marketguru_offers = {}
            else:
                st.session_state.marketguru_error = ""
                names = list(dict.fromkeys(z["name"] for z in items if z.get("name")))[:40]
                found = {}
                progress = st.progress(0, text="Suche aktuelle Marktguru-Angebote …")
                for index, ingredient_name in enumerate(names, start=1):
                    result = marktguru_angebot(ingredient_name, str(st.session_state.postcode).strip(), st.session_state.market)
                    if result.get("error"):
                        st.session_state.marketguru_error = result["error"]
                        break
                    if not result.get("not_found"):
                        found[ingredient_name] = result
                    progress.progress(index / max(1, len(names)), text=f"Prüfe Angebote … ({index}/{len(names)})")
                progress.empty()
                st.session_state.marketguru_offers = found
            st.rerun()
        if st.session_state.marketguru_error:
            st.warning(st.session_state.marketguru_error)
        if st.session_state.marketguru_offers:
            st.markdown("### Gefundene Marktguru-Angebote")
            st.caption(f"Markt: {st.session_state.market} · PLZ {st.session_state.postcode} · Angebote können unvollständig sein und müssen vor dem Einkauf geprüft werden.")
            for ingredient_name, offer in st.session_state.marketguru_offers.items():
                price_text = f'{offer["price"]:.2f} €'.replace(".", ",")
                st.markdown(f'**{html.escape(ingredient_name)}** — {html.escape(offer["description"])} · **{price_text}** · {html.escape(offer["retailer"])}')
                if offer.get("url"):
                    st.markdown(f'[Angebot öffnen]({offer["url"]})')
        for z in items:
            label = ingredient_label(z)
            st.checkbox(label, value=label in st.session_state.shopping_checked, key="shop_" + re.sub(r"[^a-zA-Z0-9]", "_", label), on_change=lambda lab=label: st.session_state.shopping_checked.add(lab) if st.session_state.get("shop_" + re.sub(r"[^a-zA-Z0-9]", "_", lab), False) else st.session_state.shopping_checked.discard(lab))
        st.download_button("📥 Einkaufsliste als TXT herunterladen", "\n".join(ingredient_label(z) for z in items), file_name="EinfachmitTimo_Einkaufsliste.txt", mime="text/plain", use_container_width=True)

elif page == "Über EinfachmitTimo":
    st.markdown('<div class="et-header"><h1>Über EinfachmitTimo</h1><p>Einfach gutes Essen.</p></div>', unsafe_allow_html=True)
    if portrait: st.image(PORTRAIT_FILE, width=260)
    st.write("Deine Rezeptwelt für einfache Mahlzeiten, Wochenplanung und cleveres Einkaufen.")

# Footer statistics
counts = {name: sum(category(r).lower() == name.lower() for r in recipes) for name in ["Frühstück", "Mittagessen", "Abendessen"]}
st.markdown(f'<div class="et-bottom"><div class="et-stat"><strong>🍳 {len(recipes)}</strong><small>Rezepte</small></div><div class="et-stat"><strong>🥣 {counts["Frühstück"]}</strong><small>Frühstück</small></div><div class="et-stat"><strong>🍽️ {counts["Mittagessen"]}</strong><small>Mittagessen</small></div><div class="et-stat"><strong>🥗 {counts["Abendessen"]}</strong><small>Abendessen</small></div><div class="et-stat"><strong>🖼️ {len(recipes)}</strong><small>Rezeptvorschauen</small></div><div class="et-stat"><strong>▤ {len(recipes)}</strong><small>Rezeptkarten</small></div></div><p style="color:#888;font-size:10px;text-align:right">Individuelle Food-Fotos sind noch nicht für jedes Rezept vorhanden.</p>', unsafe_allow_html=True)
