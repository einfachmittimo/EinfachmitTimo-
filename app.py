import base64
import html
import json
import random
import re
from datetime import date, datetime, timedelta
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

def angebot_datum(value):
    """Parst gängige Datumsangaben aus Marktguru-Antworten, sofern vorhanden."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            # Unix-Zeitstempel (Sekunden oder Millisekunden)
            stamp = float(value)
            if stamp > 10_000_000_000:
                stamp /= 1000
            return datetime.fromtimestamp(stamp).date()
        except (ValueError, OverflowError, OSError):
            return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def angebot_gueltig_im_zeitraum(result, advertiser, start_date, end_date):
    """Filtert anhand von Gültigkeitsdaten, falls die API diese mitliefert.

    Für „Diese Woche“ werden Treffer ohne Datumsfelder akzeptiert, da die
    Suchschnittstelle standardmäßig laufende Angebote zurückliefert. Für
    zukünftige Wochen werden undatierte Treffer vorsichtshalber ausgeschlossen.
    """
    start_keys = ("validFrom", "valid_from", "startDate", "start_date", "validityStart", "validFromDate", "fromDate", "validityStartDate")
    end_keys = ("validTo", "valid_to", "endDate", "end_date", "validityEnd", "validToDate", "toDate", "validityEndDate")
    containers = [result, advertiser]
    start_value = end_value = None
    for container in containers:
        if not isinstance(container, dict):
            continue
        for key in start_keys:
            if container.get(key) not in (None, ""):
                start_value = container.get(key)
                break
        for key in end_keys:
            if container.get(key) not in (None, ""):
                end_value = container.get(key)
                break
        if start_value is not None or end_value is not None:
            break
    valid_from = angebot_datum(start_value)
    valid_to = angebot_datum(end_value)
    if valid_from is None and valid_to is None:
        return start_date <= date.today() <= end_date
    if valid_from and valid_from > end_date:
        return False
    if valid_to and valid_to < start_date:
        return False
    return True


@st.cache_data(ttl=900, show_spinner=False)
def marktguru_angebot(zutat, plz, markt, zeitraum_start=None, zeitraum_ende=None):
    """Sucht ein passendes Marktguru-Angebot im ausgewählten Angebotszeitraum."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    zeitraum_start = zeitraum_start or monday.isoformat()
    zeitraum_ende = zeitraum_ende or (monday + timedelta(days=6)).isoformat()
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
            if not angebot_gueltig_im_zeitraum(
                result, advertiser, date.fromisoformat(zeitraum_start), date.fromisoformat(zeitraum_ende)
            ):
                continue
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

def recipe_image_uri(r):
    """Findet ein zum Rezept gehörendes lokales Foto, ohne fremde Gerichte zuzuordnen.

    Unterstützt r['image'] / r['image_file'] sowie automatisch benannte Dateien
    im Ordner images (jpg, jpeg, png, webp). Fehlt ein passendes Bild, bleibt
    der neutrale Rezept-Platzhalter sichtbar.
    """
    raw = r.get("image") or r.get("image_file") or r.get("bild")
    candidates = []
    if raw:
        raw_path = Path(str(raw))
        candidates.append(raw_path if raw_path.is_absolute() else BASE_DIR / raw_path)
    slug = re.sub(r"[^a-z0-9]+", "_", title(r).casefold()).strip("_")
    for ext in ("webp", "jpg", "jpeg", "png"):
        candidates.extend([BASE_DIR / "images" / f"{slug}.{ext}", BASE_DIR / "Bilder" / f"{slug}.{ext}"])
    for candidate in candidates:
        try:
            if candidate.is_file():
                mime = {".jpg":"image/jpeg", ".jpeg":"image/jpeg", ".png":"image/png", ".webp":"image/webp"}.get(candidate.suffix.lower(), "image/jpeg")
                return f"data:{mime};base64," + base64.b64encode(candidate.read_bytes()).decode("ascii")
        except OSError:
            pass
    return ""

def recipe_visual(r, class_name="recipe-visual"):
    photo = recipe_image_uri(r)
    if photo:
        return f'<div class="{class_name}"><img src="{photo}" alt="{html.escape(title(r))}"></div>'
    return f'<div class="{class_name} placeholder"><span>{category_emoji(r)}</span></div>'

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
    photo = recipe_image_uri(r)
    if photo:
        visual = f'<div class="detail-visual photo"><img src="{photo}" alt="{html.escape(title(r))}"></div>'
    else:
        visual = f'<div class="detail-visual placeholder">{category_emoji(r)}</div>'
    st.markdown(f'<div class="detail-top">{visual}<div class="detail-copy"><div class="pill">{html.escape(category(r))}</div><h2>{html.escape(title(r))}</h2><p>Einfach. Schnell. Lecker.</p></div></div>', unsafe_allow_html=True)
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
st.session_state.setdefault("week_offer_scan", {})
st.session_state.setdefault("week_offer_snapshot", {})
st.session_state.setdefault("week_offer_scan_error", "")
st.session_state.setdefault("week_plan_offer_hits", {})

# Styling
st.markdown("""
<style>
:root{--forest:#173b28;--forest2:#102319;--cream:#f8f5ee;--gold:#d89b35;--line:#e5ddcf;--ink:#202720}
.stApp{background:var(--cream);color:var(--ink);font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
[data-testid="stHeader"]{background:rgba(248,245,238,.94)}
.block-container{padding-top:2.25rem;padding-bottom:1rem;max-width:1700px}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#101713,#17231b 70%,#101713);min-width:260px!important}
section[data-testid="stSidebar"]>div{padding:15px 13px 20px}
section[data-testid="stSidebar"] p,section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] small{color:#f6f2e9!important}
.brand{padding:13px 10px 15px;border-radius:17px;background:#101511;border:1px solid #344238;text-align:center;margin-bottom:12px}
.brand img{width:100%;max-width:210px;border-radius:10px}
.brand small{display:block;color:#e6dfd0;letter-spacing:2.3px;font-size:9px;margin-top:6px}
.nav-heading{color:#b8c2b9;letter-spacing:2px;text-transform:uppercase;font-size:11px;margin:22px 6px 8px}
section[data-testid="stSidebar"] div[data-testid="stButton"]>button,
section[data-testid="stSidebar"] div[data-testid="stButton"]>button p{background:#202d24!important;color:#f8f5ee!important;border:1px solid #34483a!important;border-radius:12px!important;text-align:left!important;min-height:42px!important;font-weight:650!important;opacity:1!important}
section[data-testid="stSidebar"] div[data-testid="stButton"]>button:hover,
section[data-testid="stSidebar"] div[data-testid="stButton"]>button:hover p{background:#2d4935!important;color:#fff!important;border-color:var(--gold)!important}
.sidebar-profile{margin-top:16px;background:#0f1511;border:1px solid #344238;border-radius:15px;overflow:hidden}
.sidebar-profile img{width:100%;height:190px;object-fit:cover;object-position:center 30%;display:block}
.sidebar-profile div{padding:10px 12px;color:#fff}.sidebar-profile small{opacity:.7}
.main-brand-banner{display:flex;align-items:center;gap:18px;background:linear-gradient(115deg,#101713,#1c3e2a);color:#fff;padding:14px 20px;border-radius:0 0 18px 18px;margin:0 0 16px;box-shadow:0 8px 25px #142d1b18}.main-brand-banner img{width:74px;height:74px;object-fit:cover;border-radius:50%;border:2px solid #e0b36b}.main-brand-banner strong{display:block;font-family:Georgia,serif;font-size:clamp(21px,2.4vw,32px);font-weight:600;letter-spacing:.2px}.main-brand-banner span{display:block;color:#e4d8c4;font-size:10px;letter-spacing:3px;margin-top:3px}.et-header{background:linear-gradient(120deg,#153b28,#20573a);color:#fff;padding:23px 26px;border-radius:18px;margin:0 0 20px;box-shadow:0 8px 25px #142d1b22}
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
div[data-testid="stButton"]>button{border-radius:10px!important;border:1px solid #ded6c8!important;background:#fff!important;color:#1b2d21!important;font-weight:700!important;min-height:42px!important}div[data-testid="stButton"]>button:hover{border-color:var(--gold)!important;background:#fffaf1!important}div[data-testid="stButton"]>button[kind="primary"]{background:#1d5033!important;color:#fff!important;border-color:#1d5033!important}div[data-testid="stButton"]>button[kind="primary"] p{color:#fff!important}
/* Zieloberfläche nach der Referenz: größere Fotos, klare Rezeptkarten und Detailpanel */
.recipe-card{border-radius:13px;box-shadow:0 3px 12px rgba(20,30,20,.08);transition:transform .16s ease,box-shadow .16s ease}
.recipe-card:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(20,30,20,.13)}
.recipe-visual{height:118px;overflow:hidden;position:relative}
.recipe-visual img{width:100%;height:100%;object-fit:cover;display:block}
.recipe-visual.placeholder{background:linear-gradient(135deg,#e8e5d9 0%,#c7d3bd 45%,#416849 100%);color:white}
.recipe-visual.placeholder span{filter:drop-shadow(0 2px 4px #23352b66)}
.detail-panel{position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto;padding:17px}
.detail-top{align-items:flex-start}
.detail-visual{width:116px;min-width:116px;height:112px;overflow:hidden}
.detail-visual img{width:100%;height:100%;object-fit:cover;display:block}
.detail-visual.placeholder{background:linear-gradient(135deg,#e8e5d9,#91ad8e 55%,#285239);color:#fff}
.et-header{border-radius:0 0 24px 24px;background:linear-gradient(120deg,#173b28,#245b3a);padding:24px 28px}
.et-bottom{position:relative;grid-template-columns:repeat(6,minmax(0,1fr));border:1px solid #e4d8c4}
@media(max-width:1000px){
 .nutrition-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
 .et-bottom{grid-template-columns:repeat(3,minmax(0,1fr))}
 .detail-top{align-items:flex-start}
 .detail-copy h2{font-size:20px}
 .main-brand-banner{padding:12px}
 .main-brand-banner img{width:58px;height:58px}
 .block-container{padding-left:.75rem;padding-right:.75rem}
 .recipe-visual{height:100px}
 .detail-panel{position:static;max-height:none;overflow:visible}
}
@media(max-width:650px){
 .block-container{padding-top:5.25rem;padding-left:.65rem;padding-right:.65rem}
 .main-brand-banner{gap:10px;margin:0 0 14px;padding:12px;border-radius:0 0 20px 20px;align-items:center}
 .main-brand-banner img{width:54px;height:54px;flex:0 0 54px}
 .main-brand-banner strong{font-size:clamp(18px,5vw,22px);line-height:1.1}
 .main-brand-banner span{font-size:8px;letter-spacing:1.7px}
 .main-brand-banner strong{font-size:22px}
 .et-header{padding:18px 17px;margin:0 0 18px;border-radius:0 0 22px 22px}
 .et-header h1{font-size:25px}
 .recipe-visual{height:88px}
 .recipe-card-body{padding:8px}
 .recipe-card-title{font-size:12px;min-height:42px}
 .pill{font-size:9px;padding:4px 6px}
 .detail-visual{width:86px;min-width:86px;height:86px}
 .detail-copy h2{font-size:18px}
 .nutrition-grid{gap:5px}
 .nutrition-grid>div{padding:8px 3px}
 .nutrition-grid strong{font-size:12px}
 .et-bottom{padding:10px 5px;gap:4px}
 .et-stat strong{font-size:17px}
 .et-stat small{font-size:9px}
 section[data-testid="stSidebar"]{min-width:0!important;width:min(86vw,300px)!important}
 /* Mobile: content starts below Streamlit's fixed toolbar; no header overlap. */
 .st-key-mobile_nav{display:none}
 [data-testid="stHeader"]{height:3.25rem;background:rgba(248,245,238,.98)!important}
 [data-testid="stToolbar"]{top:.35rem}
 .st-key-mobile_nav{display:block;margin:0 0 14px}
 .st-key-mobile_nav div[data-testid="stButton"]>button{font-size:11px;padding:.35rem .15rem;min-height:40px}
 .main-brand-banner{min-height:78px;box-sizing:border-box}
 .main-brand-banner img{object-fit:contain;background:#fff}
 .et-header p{font-size:14px;line-height:1.45}
 .detail-panel{padding:12px}
 .step{font-size:13px}
 div[data-testid="stButton"]>button{white-space:normal;line-height:1.2}
 /* Keep the page from expanding beyond the phone width. */
 .stApp, [data-testid="stAppViewContainer"], section.main{max-width:100vw;overflow-x:hidden}
}
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
        active = st.session_state.page == label
        if st.button(f"{icon}  {label}", key="nav_" + label, use_container_width=True, type="primary" if active else "secondary"):
            st.session_state.page = label
            st.rerun()
    st.markdown('<div class="nav-heading">Einkaufen</div>', unsafe_allow_html=True)
    st.session_state.market = st.selectbox("Markt auswählen", MARKETS, index=MARKETS.index(st.session_state.market) if st.session_state.market in MARKETS else 0, key="sidebar_market")
    st.session_state.postcode = st.text_input("Postleitzahl", value=st.session_state.postcode, max_chars=5, key="sidebar_postcode")
    st.caption("Der ausgewählte Markt wird im Wochenplan und in der Einkaufsliste angezeigt.")
    if portrait:
        st.markdown(f'<div class="sidebar-profile"><img src="{portrait}"><div><b>EinfachmitTimo</b><br><small>Einfach gutes Essen</small></div></div>', unsafe_allow_html=True)

page = st.session_state.page
st.markdown(
    f'<div class="main-brand-banner"><img src="{logo}" alt="EinfachmitTimo Logo"><div><strong>EinfachmitTimo</strong><span>EINFACH GUTES ESSEN</span></div></div>',
    unsafe_allow_html=True,
)

# Mobile-first quick navigation: makes page changes possible without opening the sidebar.
with st.container(key="mobile_nav"):
    mobile_nav_cols = st.columns(4, gap="small")
    mobile_pages = [("⌂", "Start", "Startseite"), ("🍴", "Rezepte", "Rezepte"), ("▣", "Woche", "Wochenpläne"), ("🛒", "Einkauf", "Einkaufsliste")]
    for nav_col, (nav_icon, nav_label, nav_page) in zip(mobile_nav_cols, mobile_pages):
        with nav_col:
            if st.button(f"{nav_icon} {nav_label}", key=f"mobile_nav_{nav_page}", use_container_width=True, type="primary" if page == nav_page else "secondary"):
                st.session_state.page = nav_page
                st.rerun()

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
                    visual_html = recipe_visual(r)
                    st.markdown(f'<div class="recipe-card" style="border-color:{"#d89b35" if selected else "#e5ddcf"}">{visual_html}<div class="recipe-card-body"><div class="recipe-card-title">{html.escape(title(r))}</div><span class="pill">{html.escape(category(r))}</span></div></div>', unsafe_allow_html=True)
                    if st.button("Rezeptkarte öffnen  ↗", key=f"select_{page}_{i}_{re.sub(r'[^a-zA-Z0-9]', '_', title(r))}", use_container_width=True):
                        st.session_state.selected_recipe = title(r)
                        st.session_state.page = "Rezeptdetail"
                        st.rerun()
        with right:
            chosen = next((r for r in filtered if title(r) == st.session_state.selected_recipe), filtered[0])
            st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
            st.markdown("### Vorschau")
            render_detail(chosen, compact=True)
            if st.button("Rezeptkarte groß öffnen", key="open_detail_from_preview", type="primary", use_container_width=True):
                st.session_state.selected_recipe = title(chosen)
                st.session_state.page = "Rezeptdetail"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

elif page == "Rezeptdetail":
    by_title = {title(r): r for r in recipes}
    chosen = by_title.get(st.session_state.selected_recipe)
    top_left, top_right = st.columns([1, 4])
    with top_left:
        if st.button("← Zurück zu den Rezepten", use_container_width=True):
            st.session_state.page = "Rezepte"
            st.rerun()
    if chosen:
        st.markdown(f'<div class="et-header"><h1>{html.escape(title(chosen))}</h1><p>Deine Rezeptkarte mit Zutaten, Zubereitung und Nährwerten.</p></div>', unsafe_allow_html=True)
        st.markdown('<div class="detail-panel recipe-detail-full">', unsafe_allow_html=True)
        render_detail(chosen)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button("Zum Wochenplan hinzufügen", type="primary", use_container_width=True, key="add_detail_to_week"):
            # Für den nächsten freien Tag übernehmen; falls die Woche voll ist, den Sonntag ersetzen.
            target_day = next((day for day in TAGE if not st.session_state.week_plan.get(day)), "Sonntag")
            st.session_state.week_plan[target_day] = title(chosen)
            st.session_state.page = "Wochenpläne"
            st.rerun()
    else:
        st.warning("Das ausgewählte Rezept wurde nicht gefunden.")
        if st.button("Zur Rezeptübersicht"):
            st.session_state.page = "Rezepte"
            st.rerun()

elif page == "Wochenpläne":
    st.markdown('<div class="et-header"><h1>Dein Wochenplan</h1><p>Markt wählen, Woche erstellen – dein fertiger Plan erscheint direkt unter dem Button.</p></div>', unsafe_allow_html=True)
    st.markdown("### Planung einstellen")
    c1, c2, c3 = st.columns([1.2, 1, 0.8])
    with c1:
        market_plan = st.selectbox("Supermarkt", MARKETS, index=MARKETS.index(st.session_state.market) if st.session_state.market in MARKETS else 0, key="week_market")
        st.session_state.market = market_plan
    with c2:
        postcode_plan = st.text_input("Postleitzahl", value=st.session_state.postcode, max_chars=5, key="week_postcode")
        st.session_state.postcode = postcode_plan
    with c3:
        portion_value = st.number_input("Portionen je Gericht", min_value=1, max_value=12, value=int(st.session_state.week_portions), step=1, key="week_portion_count")
        st.session_state.week_portions = int(portion_value)
    period_options = ["Diese Woche", "Nächste Woche"]
    st.session_state.setdefault("week_offer_period", "Diese Woche")
    st.session_state.week_offer_period = st.selectbox(
        "Angebotszeitraum",
        period_options,
        index=period_options.index(st.session_state.week_offer_period) if st.session_state.week_offer_period in period_options else 0,
        key="week_offer_period_select",
        help="Der ausgewählte Zeitraum wird beim Abfragen der Marktguru-Angebote und bei der Rezeptauswahl berücksichtigt.",
    )
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    if st.session_state.week_offer_period == "Nächste Woche":
        period_start = this_monday + timedelta(days=7)
    else:
        period_start = this_monday
    period_end = period_start + timedelta(days=6)
    period_start_iso = period_start.isoformat()
    period_end_iso = period_end.isoformat()

    diet_options = ["Alle", "fleisch", "fisch", "vegetarisch", "vegan"]
    st.session_state.week_diet = st.selectbox("Ernährungsform", diet_options, index=diet_options.index(st.session_state.week_diet) if st.session_state.week_diet in diet_options else 0, key="week_diet_select")

    pool = [r for r in recipes if category(r).casefold() in ("mittagessen", "abendessen", "hauptgericht", "lunch", "dinner")]
    if st.session_state.week_diet != "Alle":
        pool = [r for r in pool if diet(r) == st.session_state.week_diet]
    if not pool:
        pool = [r for r in recipes if st.session_state.week_diet == "Alle" or diet(r) == st.session_state.week_diet]

    # Die Auswahl des Zeitraums ist Bestandteil der Marktguru-Abfrage und der Rezeptplanung.
    offer_snapshot = {
        "market": str(st.session_state.market),
        "postcode": str(st.session_state.postcode).strip(),
        "diet": str(st.session_state.week_diet),
        "period": str(st.session_state.week_offer_period),
        "period_start": period_start_iso,
        "period_end": period_end_iso,
    }
    offers_match_current_settings = (
        bool(st.session_state.week_offer_snapshot)
        and st.session_state.week_offer_snapshot == offer_snapshot
        and not st.session_state.week_offer_scan_error
    )

    if st.button("✨ Angebote prüfen & Wochenplan erstellen", type="primary", use_container_width=True, key="scan_week_offers"):
        if not re.fullmatch(r"\d{5}", offer_snapshot["postcode"]):
            st.session_state.week_offer_scan_error = "Bitte gib eine gültige fünfstellige Postleitzahl ein."
            st.session_state.week_offer_scan = {}
            st.session_state.week_offer_snapshot = {}
        elif not marktguru_headers():
            st.session_state.week_offer_scan_error = "Marktguru-Zugangsdaten fehlen. Prüfe in Streamlit unter Secrets den Bereich [marktguru] mit clientkey und apikey."
            st.session_state.week_offer_scan = {}
            st.session_state.week_offer_snapshot = {}
        elif not pool:
            st.session_state.week_offer_scan_error = "Für diese Ernährungsform wurden keine passenden Rezepte gefunden."
            st.session_state.week_offer_scan = {}
            st.session_state.week_offer_snapshot = {}
        else:
            # Häufig vorkommende, sinnvoll suchbare Zutaten aus der gefilterten Rezeptmenge priorisieren.
            ignored_terms = {
                "salz", "pfeffer", "wasser", "öl", "olivenöl", "rapsöl", "gewürze",
                "paprikapulver", "currypulver", "italienische kräuter", "kräuter", "nach geschmack",
                "etwas", "optional", "zum garnieren", "zitronensaft", "knoblauchpulver"
            }
            frequency = {}
            display_names = {}
            for recipe in pool:
                seen_for_recipe = set()
                for ingredient in recipe.get("ingredients", []):
                    if not isinstance(ingredient, dict):
                        continue
                    name = re.sub(r"\s*\([^)]*\)\s*", " ", str(ingredient.get("name") or "")).strip(" ,.-")
                    normalized = re.sub(r"\s+", " ", name).casefold()
                    if not normalized or normalized in ignored_terms or len(normalized) < 3:
                        continue
                    if any(term in normalized for term in ("salz", "pfeffer", "wasser", "gewürz", "nach geschmack", "zum garnieren")):
                        continue
                    if normalized not in seen_for_recipe:
                        frequency[normalized] = frequency.get(normalized, 0) + 1
                        display_names.setdefault(normalized, name)
                        seen_for_recipe.add(normalized)
            # Nicht mehr als 20 API-Suchen pro Lauf; häufige Grundzutaten erhöhen die Trefferchance.
            search_names = [display_names[key] for key, _ in sorted(frequency.items(), key=lambda item: (-item[1], item[0]))[:20]]
            found = {}
            errors = []
            progress = st.progress(0, text=f"Frage Marktguru-Angebote für {offer_snapshot['period']} ab …")
            for index, ingredient_name in enumerate(search_names, start=1):
                result = marktguru_angebot(
                    ingredient_name,
                    offer_snapshot["postcode"],
                    offer_snapshot["market"],
                    offer_snapshot["period_start"],
                    offer_snapshot["period_end"],
                )
                if result.get("error"):
                    errors.append(result["error"])
                    break
                if not result.get("not_found"):
                    found[ingredient_name.casefold()] = {**result, "search_term": ingredient_name}
                progress.progress(index / max(1, len(search_names)), text=f"Prüfe {offer_snapshot['period']}: {ingredient_name} … ({index}/{len(search_names)})")
            progress.empty()
            st.session_state.week_offer_scan = found
            st.session_state.week_offer_snapshot = offer_snapshot if not errors else {}
            st.session_state.week_offer_scan_error = errors[0] if errors else ""
            st.session_state.marketguru_offers = {
                item["search_term"]: item for item in found.values()
            }

            # In einem einzigen Klick: erst Angebote abfragen, danach sofort den Wochenplan daraus erstellen.
            if not errors:
                offered_terms = set(found.keys())
                scored = []
                for recipe in pool:
                    recipe_terms = set()
                    for ingredient in recipe.get("ingredients", []):
                        if not isinstance(ingredient, dict):
                            continue
                        name = re.sub(r"\s*\([^)]*\)\s*", " ", str(ingredient.get("name") or "")).strip()
                        normalized = re.sub(r"\s+", " ", name).casefold()
                        if normalized:
                            recipe_terms.add(normalized)
                    hits = sum(1 for term in offered_terms if any(term == item or term in item or item in term for item in recipe_terms))
                    scored.append((hits, random.random(), recipe))
                scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
                picked = []
                seen = set()
                for hits, _, recipe in scored:
                    recipe_title = title(recipe)
                    if not recipe_title or recipe_title in seen:
                        continue
                    if found and hits == 0:
                        continue
                    picked.append(recipe)
                    seen.add(recipe_title)
                    if len(picked) == 7:
                        break
                # Wenn Angebote nicht für sieben Gerichte reichen, restliche Plätze mit passenden Rezepten auffüllen.
                if len(picked) < 7:
                    for _, _, recipe in scored:
                        recipe_title = title(recipe)
                        if recipe_title and recipe_title not in seen:
                            picked.append(recipe)
                            seen.add(recipe_title)
                        if len(picked) == 7:
                            break
                if len(picked) == 7:
                    st.session_state.week_plan = {TAGE[i]: title(recipe) for i, recipe in enumerate(picked)}
                    st.session_state.week_plan_offer_hits = {
                        title(recipe): next((hits for hits, _, item in scored if title(item) == title(recipe)), 0)
                        for recipe in picked
                    }
                    st.session_state.shopping_checked = set()
                    st.session_state.marketguru_error = ""
        st.rerun()

    if st.session_state.week_offer_scan_error:
        st.error(st.session_state.week_offer_scan_error)

    # Absichtlich direkt unter dem Erstellen-Button: keine manuelle Wochenplan-Eingabe und kein Speichern-Button.
    st.markdown("### Dein erstellter Wochenplan")
    if st.session_state.week_plan:
        st.markdown(
            f'<div style="background:#e9e0cd;border:1px solid #ded3bc;border-radius:14px;padding:12px 16px;margin-bottom:14px"><b>🛒 {html.escape(st.session_state.market)}</b> · PLZ {html.escape(str(st.session_state.postcode))} · {st.session_state.week_portions} Portion(en) pro Gericht</div>',
            unsafe_allow_html=True,
        )
        by_title = {title(r): r for r in recipes}
        day_cols = st.columns(2, gap="medium")
        for i, day in enumerate(TAGE):
            with day_cols[i % 2]:
                recipe_name = st.session_state.week_plan.get(day)
                recipe = by_title.get(recipe_name)
                nv = nutrition(recipe) if recipe else {"kcal": "–", "protein": "–"}
                emoji = category_emoji(recipe) if recipe else "🍽️"
                if recipe:
                    plan_visual = recipe_visual(recipe, "recipe-visual")
                else:
                    plan_visual = f'<div class="recipe-visual placeholder"><span>{emoji}</span></div>'
                st.markdown(
                    f'<div class="recipe-card"><div style="display:flex;gap:12px;align-items:center;padding:14px">{plan_visual}<div style="min-width:0;flex:1"><div class="section-label">{html.escape(day)} · warmes Hauptgericht</div><div class="recipe-card-title" style="font-size:16px;min-height:0">{html.escape(recipe_name or "Kein Gericht zugeordnet")}</div><div style="margin-top:7px"><span class="pill">{html.escape(category(recipe) if recipe else "Hauptgericht")}</span></div><div style="font-size:12px;color:#62685f;margin-top:7px">🔥 {html.escape(str(nv["kcal"]))} kcal · 💪 {html.escape(str(nv["protein"]))} g Protein</div></div></div></div>',
                    unsafe_allow_html=True,
                )
                if recipe and st.button("📖 Rezeptkarte öffnen", key="open_plan_recipe_" + day, type="primary", use_container_width=True):
                    st.session_state.selected_recipe = title(recipe)
                    st.session_state.page = "Rezeptdetail"
                    st.rerun()
                if st.button("↻ Gericht austauschen", key="swap_" + day, use_container_width=True):
                    current = st.session_state.week_plan.get(day)
                    alternatives = [r for r in pool if title(r) != current and title(r) not in {v for k, v in st.session_state.week_plan.items() if k != day}]
                    if alternatives:
                        st.session_state.week_plan[day] = title(random.choice(alternatives))
                        st.session_state.shopping_checked = set()
                        st.session_state.marketguru_offers = {}
                    else:
                        st.warning("Es gibt keine weiteren unterschiedlichen Gerichte für diese Auswahl.")
                    st.rerun()
        st.markdown("### Nächster Schritt: Einkauf")
        items = ingredients_for_plan(st.session_state.week_plan, st.session_state.week_portions)
        st.caption(f"{len(items)} unterschiedliche Zutaten aus deinem Wochenplan.")
        a, b = st.columns(2)
        with a:
            if st.button("🛒 Einkaufsliste öffnen", type="primary", use_container_width=True):
                st.session_state.page = "Einkaufsliste"
                st.rerun()
        with b:
            if st.button("🔄 Neue Woche erstellen", use_container_width=True):
                st.session_state.week_plan = {}
                st.session_state.shopping_checked = set()
                st.session_state.marketguru_offers = {}
                st.session_state.marketguru_error = ""
                st.session_state.week_offer_scan = {}
                st.session_state.week_offer_snapshot = {}
                st.session_state.week_offer_scan_error = ""
                st.rerun()
    else:
        st.info("Dein erstellter Wochenplan erscheint hier direkt nach dem Klick auf „Woche automatisch planen“. Du musst keine Gerichte einzeln auswählen und nichts separat speichern.")


    # Angebote bewusst unter dem fertigen Wochenplan anzeigen.
    if offers_match_current_settings:
        scanned_offers = st.session_state.week_offer_scan
        st.markdown(f"### Angebote für deine Rezeptauswahl · {offer_snapshot['period']}")
        st.caption(f"Markt: {offer_snapshot['market']} · PLZ {offer_snapshot['postcode']} · Zeitraum {period_start.strftime('%d.%m.%Y')}–{period_end.strftime('%d.%m.%Y')} · {len(scanned_offers)} passende Angebots-Treffer bei den geprüften Zutaten.")
        if scanned_offers:
            offer_cols = st.columns(2, gap="small")
            for index, offer in enumerate(scanned_offers.values()):
                with offer_cols[index % 2]:
                    price_text = f"{offer['price']:.2f} €".replace(".", ",")
                    st.markdown(
                        f"<div class='recipe-card' style='padding:10px 12px'><b>{html.escape(offer['description'])}</b><br><small>{html.escape(offer['retailer'])} · Suchzutat: {html.escape(offer['search_term'])}</small><br><strong>{price_text}</strong></div>",
                        unsafe_allow_html=True,
                    )
                    if offer.get("url"):
                        st.markdown(f"[Angebot ansehen]({offer['url']})")
        else:
            st.info("Für die geprüften Zutaten wurden bei diesem Markt keine passenden Angebote gefunden. Du kannst trotzdem einen normalen Wochenplan aus deiner Rezeptdatenbank erstellen.")


    else:
        st.caption("Mit einem Klick werden zuerst die aktuellen Marktguru-Angebote geprüft und anschließend direkt dein Wochenplan erstellt.")

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
st.markdown(f'<div class="et-bottom"><div class="et-stat"><strong>🍳 {len(recipes)}</strong><small>Rezepte</small></div><div class="et-stat"><strong>🥣 {counts["Frühstück"]}</strong><small>Frühstück</small></div><div class="et-stat"><strong>🍽️ {counts["Mittagessen"]}</strong><small>Mittagessen</small></div><div class="et-stat"><strong>🥗 {counts["Abendessen"]}</strong><small>Abendessen</small></div><div class="et-stat"><strong>🖼️ {len(recipes)}</strong><small>Rezeptvorschauen</small></div><div class="et-stat"><strong>▤ {len(recipes)}</strong><small>Rezeptdatensätze</small></div></div><p style="color:#888;font-size:10px;text-align:right">Individuelle Food-Fotos sind noch nicht für jedes Rezept vorhanden.</p>', unsafe_allow_html=True)
