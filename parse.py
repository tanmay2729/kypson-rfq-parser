import re

# category rules - checked in this order, so specific ones come first
CATEGORIES = [
    ("fibc", r"fibc|jumbo|bulk\s*bag|big\s*bag"),
    ("bopp_bag", r"\bbo+p+"),
    ("woven_sack", r"woven|cement|ad\s*star|pp\s*bag|hdpe|sack"),
    ("film", r"shrink|stre?t?ch|film|wrap|cling|ldpe"),
    ("pouch", r"pouch|zipper|stand\s*up|sachet"),
    ("mono_carton", r"mono\s*carton|folding|duplex"),
    ("corrugated_box", r"cor+[ou]g|box|carton"),
]

MULT = {"k": 1000, "thousand": 1000, "hazaar": 1000, "lakh": 100000, "crore": 10000000}
WEIGHT = {"kg": "kg", "kgs": "kg", "mt": "mt", "mts": "mt", "ton": "mt",
          "tons": "mt", "tonne": "mt", "tonnes": "mt"}
COUNT = {"pcs", "pc", "nos", "no", "piece", "pieces", "bag", "bags", "box", "boxes",
         "carton", "cartons", "sack", "sacks", "pouch", "pouches", "roll", "rolls", "units"}
NOT_QTY = {"gsm", "mic", "micron", "microns", "mm", "cm", "inch", "ft", "ply",
           "layer", "x", "day", "days", "percent"}
FILL = {"capacity", "cap", "bag", "bags", "sack", "sacks", "pouch", "pouches",
        "each", "per", "pack", "packing", "wala", "wale", "x"}

CITIES = ("mumbai,navi mumbai,delhi,new delhi,noida,gurgaon,gurugram,faridabad,ghaziabad,"
          "bangalore,bengaluru,chennai,hyderabad,kolkata,pune,ahmedabad,surat,vadodara,"
          "rajkot,jamnagar,gandhinagar,morbi,vapi,jaipur,jodhpur,udaipur,kota,ajmer,"
          "bikaner,lucknow,kanpur,agra,varanasi,meerut,nagpur,nashik,aurangabad,solapur,"
          "kolhapur,thane,bhiwandi,indore,bhopal,gwalior,jabalpur,raipur,bilaspur,ranchi,"
          "jamshedpur,patna,bhubaneswar,cuttack,guwahati,siliguri,kochi,cochin,coimbatore,"
          "madurai,salem,tiruppur,trichy,erode,hosur,mysore,mangalore,hubli,vijayawada,"
          "visakhapatnam,vizag,guntur,chandigarh,mohali,panchkula,ludhiana,amritsar,"
          "jalandhar,patiala,ambala,panipat,sonipat,karnal,rohtak,dehradun,haridwar,"
          "shimla,baddi,jammu,goa,silvassa,india,usa,uae,uk,dubai,abu dhabi,oman,qatar,"
          "kuwait,saudi arabia,nepal,bangladesh,sri lanka,germany,france,italy,singapore,"
          "malaysia,china,australia,canada,kenya,nigeria").split(",")
CITY_RE = re.compile(r"\b(" + "|".join(sorted(CITIES, key=len, reverse=True)) + r")\b")

# words that can never be a place name (used for the "last word" guess)
NOT_PLACE = set("""need quote quotation urgent urgently please pls chahiye chaiye chahie
bhej bhejo send rate price sample export bulk jaldi abhi medicine hai bhai sir thanks
required require delivery kg kgs mt pcs nos gsm mic micron ply lakh hazaar ton tonne
required stock supply order plain printed""".split())


def get_category(t):
    for name, pattern in CATEGORIES:
        if re.search(pattern, t):
            return name
    return "corrugated_box"


def get_quantity(t, category):
    found = []  # (strength, value, unit)
    pattern = r"(?<![\w.])(\d+(?:\.\d+)?)\s*(lakh|crore|hazaar|thousand|k(?![a-z]))?(?:\s*([a-z]+))?(?:\s+([a-z]+))?"
    for m in re.finditer(pattern, t):
        num, mult, w1, w2 = m.group(1), m.group(2), m.group(3) or "", m.group(4) or ""
        value = float(num) * MULT[mult] if mult else float(num)

        if w1 in NOT_QTY:                       # gsm, mic, inch, ply ...
            continue
        if not mult and not w1 and len(num) >= 6:   # phone number / pincode
            continue

        unit = WEIGHT.get(w1) or ("pcs" if w1 in COUNT else None)

        # a weight can really be the bag capacity ("1000 kg capacity", "25 kg bags")
        fill = False
        if unit in ("kg", "mt"):
            before = t[:m.start()]
            fill = w2 in FILL or bool(re.search(r"(capacity|of|each|per|swl)\s*$", before))
            if unit == "kg" and category != "film" and value <= 100:
                fill = True

        if fill:
            found.append((0, value, unit))
        elif unit or mult:
            found.append((2, value, unit or "pcs"))
        else:
            found.append((1, value, "pcs"))

    if not found:
        return None, "pcs"

    top = max(f[0] for f in found)
    best = [f for f in found if f[0] == top]
    if category != "film":              # bags/boxes are ordered by count
        counts = [f for f in best if f[2] == "pcs"]
        best = counts or best
    value, unit = best[0][1], best[0][2]
    return (int(value) if value == int(value) else value), unit


def get_location(original, t):
    m = CITY_RE.search(t)
    if m:
        name = m.group(1)
        return name.upper() if name in ("usa", "uae", "uk") else name.title()

    # city we don't know: look for hints
    guesses = []
    m = re.search(r"\b(?:to|at|deliver|delivery|dispatch)\s+([a-z]{3,})", t)
    if m:
        guesses.append(m.group(1))
    m = re.search(r"\b(?:for|in|from)\s+([A-Z][a-z]{2,})", original)
    if m:
        guesses.append(m.group(1).lower())
    m = re.search(r"\b([a-z]{3,})\s+(?:mein|me|ke liye)\b", t)
    if m:
        guesses.append(m.group(1))
    words = re.findall(r"[a-z]+", t)
    if len(words) > 1:
        guesses.append(words[-1])

    for g in guesses:
        if g in NOT_PLACE or g in COUNT or g in WEIGHT or g in NOT_QTY or len(g) < 4:
            continue
        if any(re.search(p, g) for _, p in CATEGORIES):
            continue
        # fix doubled letters like "nagpurr"
        for c in CITIES:
            if re.sub(r"(.)\1+", r"\1", g) == re.sub(r"(.)\1+", r"\1", c):
                return c.title()
        return g.title()
    return None


def parse_rfq(text):
    t = text.lower()
    t = re.sub(r"(?<=\d),(?=\d)", "", t)                    # 1,50,000 -> 150000
    t = re.sub(r"\b(lacs?|lakhs|laks?)\b", "lakh", t)
    t = re.sub(r"\b(hazar|hajar|hazaar+)\b", "hazaar", t)

    category = get_category(t)
    quantity, unit = get_quantity(t, category)
    gsm = re.search(r"(\d+)\s*gsm", t)
    micron = re.search(r"(\d+)\s*(?:micron|mic)", t)

    return {
        "category": category,
        "quantity": quantity,
        "unit": unit,
        "gsm": int(gsm.group(1)) if gsm else None,
        "micron": int(micron.group(1)) if micron else None,
        "location": get_location(text, t),
    }
