import os, re, json, random, hashlib, glob, datetime, difflib
import requests

# ---------- SETTINGS (yahan badlo) ----------
PER_RUN = 3                      # ek run mein kitni shayari
LANGUAGE = "Hinglish (Roman script mein Hindi, jaise: 'tum yaad aaye')"
# Hindi ke liye: "Hindi (Devanagari script)" | Urdu ke liye: "Urdu (Nastaliq script)"
MODELS = [os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
          "openai/gpt-oss-20b", "llama-3.1-8b-instant"]   # pehla fail ho to agla try hoga
SIMILARITY_LIMIT = 0.75          # isse zyada match ho to reject
OUT_DIR = "content/shayari"
# --------------------------------------------

CATEGORIES = ["love", "dosti", "sad", "motivation", "zindagi", "intezaar", "yaadein"]
MOODS = ["udaas", "romantic", "josh wala", "sukoon wala", "shikayat bhara"]
KEYWORDS = ["chand", "baarish", "chai", "safar", "raat", "aaina", "khamoshi",
            "subah", "dil", "manzil", "hawa", "tanhai", "khwab", "diya"]

API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
if not API_KEY:
    raise SystemExit("GROQ_API_KEY secret nahi mila. Settings > Secrets and variables > Actions mein add karo.")

URL = "https://api.groq.com/openai/v1/chat/completions"


def normalize(t):
    return " ".join(re.sub(r"[^\w\s]", "", t.lower()).split())


def load_existing():
    items = []
    for f in glob.glob(f"{OUT_DIR}/*.md"):
        raw = open(f, encoding="utf-8").read()
        items.append(raw.split("---", 2)[-1].strip())
    return items


def is_duplicate(text, existing):
    n = normalize(text)
    for e in existing:
        ne = normalize(e)
        if n == ne or difflib.SequenceMatcher(None, n, ne).ratio() >= SIMILARITY_LIMIT:
            return True
    return False


def call_llm(prompt):
    last_err = None
    for model in MODELS:
        r = requests.post(
            URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Tum ek shayar ho. Hamesha sirf valid JSON object return karo."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 1.0,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        last_err = f"[{model}] HTTP {r.status_code}: {r.text[:300]}"
        print("API ERROR:", last_err)
    raise RuntimeError(last_err)


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
    raw = call_llm(prompt)
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    data = json.loads(raw)
    if isinstance(data, list):
        data = data[0]
    if not data.get("text") or not data.get("title"):
        raise ValueError("title/text missing in response")
    return data


def save(item, category, mood, keyword):
    os.makedirs(OUT_DIR, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc)
    h = hashlib.md5(item["text"].encode()).hexdigest()[:6]
    name = f"{now:%Y-%m-%d}-{h}.md"
    title = item["title"].replace('"', "'")
    front = (f'---\ntitle: "{title}"\ndate: {now:%Y-%m-%dT%H:%M:%SZ}\n'
             f'category: "{category}"\nmood: "{mood}"\nkeyword: "{keyword}"\n---\n\n')
    with open(f"{OUT_DIR}/{name}", "w", encoding="utf-8") as f:
        f.write(front + item["text"].strip() + "\n")
    print("Saved:", name)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    existing = load_existing()
    made, attempts = 0, 0
    while made < PER_RUN and attempts < PER_RUN * 3:
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
        raise SystemExit("Koi shayari nahi bani, upar ke API ERROR lines dekho")


if __name__ == "__main__":
    main()
