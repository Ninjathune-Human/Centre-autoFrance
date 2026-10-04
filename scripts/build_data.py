"""Construit centres.json : All The Places (sites officiels des enseignes) + OpenStreetMap."""
import io, json, re, sys, time, unicodedata, urllib.parse, urllib.request, zipfile
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
OVERPASS = ["https://overpass-api.de/api/interpreter",  # serveur principal, puis miroirs mondiaux
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
            "https://overpass.private.coffee/api/interpreter"]
DEPTS = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
DOM = {"971": (15.8, 16.6, -61.9, -60.9), "972": (14.3, 14.95, -61.3, -60.75), "973": (2.0, 6.0, -54.7, -51.5),
       "974": (-21.5, -20.8, 55.1, 55.9), "976": (-13.1, -12.6, 44.9, 45.4)}
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
        "n": t.get("name") or " ".join(x for x in (BRANDS[b][0], t.get("branch")) if x), "s": street,
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
    for attempt, url in enumerate(OVERPASS * 2):
        try:
            data = json.loads(get(url, urllib.parse.urlencode({"data": QUERY}).encode()))
            if not data.get("elements"):
                raise RuntimeError(data.get("remark") or "réponse vide")
            break
        except Exception as e:
            print(f"Overpass {url} : {e}")
            if attempt == len(OVERPASS) * 2 - 1:
                raise
            time.sleep(30)
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


def in_ring(x, y, ring):
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def departements():
    """Contours IGN simplifiés des départements métropolitains."""
    out = []
    for f in json.loads(get(DEPTS))["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        xs = [pt[0] for poly in polys for pt in poly[0]]
        ys = [pt[1] for poly in polys for pt in poly[0]]
        out.append((f["properties"]["code"], polys, (min(xs), max(xs), min(ys), max(ys))))
    return out


def dep_of(it, deps):
    x, y, p = it["lng"], it["lat"], it.get("p", "")
    for code, (y0, y1, x0, x1) in DOM.items():
        if y0 <= y <= y1 and x0 <= x <= x1:
            return code
    for code, polys, (x0, x1, y0, y1) in deps:
        if x0 <= x <= x1 and y0 <= y <= y1 and any(
                in_ring(x, y, poly[0]) and not any(in_ring(x, y, h) for h in poly[1:]) for poly in polys):
            return code
    if re.fullmatch(r"\d{5}", p):  # point sur la côte, hors contour simplifié
        return p[:3] if p.startswith("97") else ("2A" if p < "20200" else "2B") if p.startswith("20") else p[:2]
    if deps:  # ni contour ni code postal : département le plus proche
        return min(deps, key=lambda d: min((pt[0] - x) ** 2 + (pt[1] - y) ** 2 for poly in d[1] for pt in poly[0]))[0]
    return None


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
    # Fusion : un centre OpenStreetMap à moins de 200 m d'un centre officiel de la même enseigne
    # est un doublon ; il complète seulement les champs manquants (SIRET, téléphone…).
    items, added = list(official), [0] * len(BRANDS)
    for o in community:
        twin = next((it for it in official if it["b"] == o["b"]
                     and abs(it["lat"] - o["lat"]) < 0.002 and abs(it["lng"] - o["lng"]) < 0.003), None)
        if twin:
            for k, v in o.items():
                twin.setdefault(k, v)
        else:
            items.append(o)
            added[o["b"]] += 1
    if not items:
        sys.exit("Aucune donnée récupérée, centres.json non écrit.")
    try:
        deps = departements()
    except Exception as e:
        print(f"Contours des départements indisponibles : {e}")
        deps = []
    for it in items:
        if d := dep_of(it, deps):
            it["d"] = d
    print(f"Centres sans département : {sum('d' not in it for it in items)}")
    for i, (name, _) in enumerate(BRANDS):
        n = sum(it["b"] == i for it in items)
        print(f"{name:12} {n:5}  (sites officiels {n - added[i]}, OpenStreetMap {added[i]})")
    with open("centres.json", "w", encoding="utf-8") as f:
        json.dump({"maj": date.today().isoformat(), "items": items}, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
