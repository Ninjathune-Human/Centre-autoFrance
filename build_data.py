"""Construit centres.json : All The Places (sites officiels des enseignes) + OpenStreetMap."""
import io, json, re, sys, unicodedata, urllib.parse, urllib.request, zipfile
from datetime import date

BRANDS = [
    ("Norauto", r"norauto"), ("Feu Vert", r"feu ?vert"), ("Speedy", r"speedy"),
    ("Midas", r"midas"), ("Point S", r"point s( |$)"), ("Euromaster", r"euromaster"),
    ("Vulco", r"vulco"), ("Profil Plus", r"profil( ?plus|\+)"), ("Roady", r"roady"),
    ("Carter-Cash", r"carter.?cash"), ("Eurorepar", r"eurorepar"), ("Motrio", r"motrio"),
    ("Top Garage", r"top ?garage"),
]
RES = [re.compile(r) for _, r in BRANDS]
SPIDERS = {"norauto_fr": "Norauto", "feu_vert_fr": "Feu Vert", "speedy_fr_ma": "Speedy", "midas": "Midas",
           "point_s_fr": "Point S", "euromaster_fr": "Euromaster", "motrio": "Motrio", "top_garage_fr": "Top Garage"}
FRANCE = {"FR", "GP", "MQ", "GF", "RE", "YT", "PM", "BL", "MF"}
ATP = "https://data.alltheplaces.xyz"
OVERPASS = "https://overpass-api.de/api/interpreter"
RX = "Norauto|Feu ?Vert|Speedy|Midas|Point S( |$)|Euromaster|Vulco|Profil( ?Plus|[+])|Roady|Carter.?Cash|Eurorepar|Motrio|Top ?Garage"
QUERY = f"""[out:json][timeout:300];
area["ISO3166-1"="FR"][admin_level=2]->.fr;
(
  nwr["brand"~"^(Norauto|Feu Vert|Speedy|Midas|Point S|Euromaster|Vulco|Roady|Motrio|Top Garage)$"](area.fr);
  nwr["shop"="car_repair"]["name"~"{RX}",i](area.fr);
  nwr["shop"="tyres"]["name"~"{RX}",i](area.fr);
  nwr["shop"="car_parts"]["name"~"{RX}",i](area.fr);
);
out center tags;"""


def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "centres-auto-france (GitHub Actions)"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def norm(s):
    return unicodedata.normalize("NFD", (s or "").lower()).encode("ascii", "ignore").decode()


def brand_of(*values):
    for v in values:
        for i, rx in enumerate(RES):
            if rx.search(norm(v)):
                return i
    return -1


def item(b, lat, lng, t, street):
    return {k: v for k, v in {
        "lat": round(float(lat), 5), "lng": round(float(lng), 5), "b": b,
        "n": t.get("name") or BRANDS[b][0], "s": street,
        "p": t.get("addr:postcode"), "c": t.get("addr:city"),
        "tel": t.get("phone") or t.get("contact:phone"),
        "web": t.get("website") or t.get("contact:website"),
        "mail": t.get("email") or t.get("contact:email"),
        "h": t.get("opening_hours"), "siret": t.get("ref:FR:SIRET"),
    }.items() if v not in (None, "")}


def features(raw):
    """GeoJSON classique ou une entité par ligne."""
    try:
        return json.loads(raw)["features"]
    except ValueError:
        return [json.loads(l) for l in raw.splitlines() if l.strip().startswith("{")]


def atp():
    latest = json.loads(get(f"{ATP}/runs/latest.json"))
    raws = {}
    if "groups" in latest:
        for g in latest["groups"]:
            try:
                manifest = json.loads(get(f"{ATP}/runs/latest/{g['name']}.manifest.json"))
            except Exception as e:
                print(f"Manifeste {g['name']} ignoré : {e}")
                continue
            for name, entry in manifest.get("spiders", {}).items():
                if name in SPIDERS:
                    raws[name] = get(entry["geojson_url"]).decode()
    else:
        with zipfile.ZipFile(io.BytesIO(get(latest["output_url"]))) as z:
            for name in SPIDERS:
                try:
                    raws[name] = z.read(f"output/{name}.geojson").decode()
                except KeyError:
                    pass
    out = []
    for name, raw in raws.items():
        b = [n for n, _ in BRANDS].index(SPIDERS[name])
        for f in features(raw):
            p, g = f.get("properties") or {}, f.get("geometry") or {}
            if g.get("type") != "Point" or p.get("end_date") or p.get("addr:country", "FR") not in FRANCE:
                continue
            street = p.get("addr:street_address") or " ".join(x for x in (p.get("addr:housenumber"), p.get("addr:street")) if x)
            out.append(item(b, g["coordinates"][1], g["coordinates"][0], p, street))
    return out


def osm():
    data = json.loads(get(OVERPASS, urllib.parse.urlencode({"data": QUERY}).encode()))
    if not data.get("elements"):
        raise RuntimeError(data.get("remark") or "réponse vide")
    out = []
    for e in data["elements"]:
        t = e.get("tags", {})
        lat, lng = e.get("lat", e.get("center", {}).get("lat")), e.get("lon", e.get("center", {}).get("lon"))
        b = brand_of(t.get("brand"), t.get("name"))
        if lat is None or b < 0:
            continue
        street = " ".join(x for x in (t.get("addr:housenumber"), t.get("addr:street")) if x)
        out.append(item(b, lat, lng, t, street))
    return out


def main():
    try:
        official = atp()
    except Exception as e:
        print(f"All The Places indisponible : {e}")
        official = []
    try:
        community = osm()
    except Exception as e:
        print(f"OpenStreetMap indisponible : {e}")
        community = []
    covered = {it["b"] for it in official}
    items = official + [it for it in community if it["b"] not in covered]
    if not items:
        sys.exit("Aucune donnée récupérée, centres.json non écrit.")
    for i, (name, _) in enumerate(BRANDS):
        n = sum(it["b"] == i for it in items)
        print(f"{name:12} {n:5}  {'sites officiels' if i in covered else 'OpenStreetMap'}")
    with open("centres.json", "w", encoding="utf-8") as f:
        json.dump({"maj": date.today().isoformat(), "items": items}, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
