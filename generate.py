import os, re, json, random, hashlib, glob, datetime, difflib
import requests

# ---------- SETTINGS (yahan badlo) ----------
PER_RUN = 3                      # ek run mein kitni shayari
LANGUAGE = "Hinglish (Roman script mein Hindi, jaise: 'tum yaad aaye')"
# Hindi ke liye: "Hindi (Devanagari script)" | Urdu ke liye: "Urdu (Nastaliq script)"
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
SIMILARITY_LIMIT = 0.75          # isse zyada match ho to reject
OUT_DIR = "content/shayari"
# --------------------------------------------

CATEGORIES = ["love", "dosti", "sad", "motivation", "zindagi", "intezaar", "yaadein"]
MOODS = ["udaas", "romantic", "josh wala", "sukoon wala", "shikayat bhara"]
KEYWORDS = ["chand", "baarish", "chai", "safar", "raat", "aaina", "khamoshi",
            "subah", "dil", "manzil", "hawa", "tanhai", "khwab", "diya"]

API_KEY = os.environ["GEMINI_API_KEY"]
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def normalize(t):
    return re.sub(r"[^\w\s]", "", t.lower()).split() and " ".join(re.sub(r"[^\w\s]", "", t.lower()).split())


def load_existing():
    items = []
    for f in glob.glob(f"{OUT_DIR}/*.md"):
        raw = open(f, encoding="utf-8").read()
        body = raw.split("---", 2)[-1].strip()
        items.append(body)
    return items


def is_duplicate(text, existing):
    n = normalize(text)
    h = hashlib.md5(n.encode()).hexdigest()
    for e in existing:
        ne = normalize(e)
        if hashlib.md5(ne.encode()).hexdigest() == h:
            return True
        if difflib.SequenceMatcher(None, n, ne).ratio() >= SIMILARITY_LIMIT:
            return True
    return False


def generate(category, mood, keyword, avoid):
    avoid_txt = "\n".join(f"- {a.splitlines()[0]}" for a in avoid[-40:]) or "koi nahi"
    prompt = f"""Ek bilkul original shayari likho.
Bhasha: {LANGUAGE}
Category: {category}
Mood: {mood}
Keyword: {keyword}
Format: 2 se 4 line. Kisi mashhoor shayar ki line copy mat karna.
Ye pehle se ban chuki hain, inse milti-julti mat likhna:
{avoid_txt}

Sirf JSON do: {{"title": "chhota title", "text": "shayari (lines \\n se alag)"}}"""
    r = requests.post(
        URL,
        headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 1.0, "responseMimeType": "application/json"},
        },
        timeout=60,
    )
    r.raise_for_status()
    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(raw)


def save(item, category, mood, keyword):
    os.makedirs(OUT_DIR, exist_ok=True)
    now = datetime.datetime.utcnow()
    h = hashlib.md5(item["text"].encode()).hexdigest()[:6]
    name = f"{now:%Y-%m-%d}-{h}.md"
    title = item["title"].replace('"', "'")
    front = (f'---\ntitle: "{title}"\ndate: {now:%Y-%m-%dT%H:%M:%SZ}\n'
             f'category: "{category}"\nmood: "{mood}"\nkeyword: "{keyword}"\n---\n\n')
    with open(f"{OUT_DIR}/{name}", "w", encoding="utf-8") as f:
        f.write(front + item["text"].strip() + "\n")
    print("Saved:", name)


def main():
    existing = load_existing()
    made, attempts = 0, 0
    while made < PER_RUN and attempts < PER_RUN * 5:
        attempts += 1
        cat, mood, kw = random.choice(CATEGORIES), random.choice(MOODS), random.choice(KEYWORDS)
        try:
            item = generate(cat, mood, kw, existing)
        except Exception as e:
            print("Error:", e)
            continue
        if is_duplicate(item["text"], existing):
            print("Duplicate/similar, skip")
            continue
        save(item, cat, mood, kw)
        existing.append(item["text"])
        made += 1
    print(f"Done: {made} new shayari")
             if made == 0:
        raise SystemExit("Koi shayari nahi bani, upar ke errors dekho")


if __name__ == "__main__":
    main()
