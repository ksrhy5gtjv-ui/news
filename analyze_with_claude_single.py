
import os, json, math
from glob import glob
from datetime import datetime
import anthropic

API_KEY = os.getenv("CLAUDE_API_KEY")
if not API_KEY:
    raise RuntimeError("Set CLAUDE_API_KEY")

client = anthropic.Anthropic(api_key=API_KEY)

files = sorted(glob("scraped_data/news_articles_*.json"), reverse=True)
if not files:
    raise RuntimeError("No news_articles_*.json found")
input_file = files[0]

with open(input_file, "r", encoding="utf-8") as f:
    articles = json.load(f)

def compact(article, max_chars=1200):
    a = dict(article)
    # keep essential fields and trim content to avoid token blowups
    keep = {k: a.get(k) for k in ["site", "title", "url", "summary", "published_at"] if k in a}
    body = a.get("content") or a.get("full_text") or ""
    if body and len(body) > max_chars:
        body = body[:max_chars] + "…"
    keep["content"] = body
    return keep

compact_arts = [compact(a) for a in articles][:250]

system_prompt = "You are a literary and journalism expert at CBC Radio. Be concise and decisive."
user_prompt = (
    "Evaluate the following scraped news items for documentary potential in the style of CBC Radio's Storylines. "
    "For each promising story, provide: 1) title, 2) why it works as narrative audio (characters, arc, stakes, tension), "
    "3) broader significance, 4) initial reporting plan (sources to call), and 5) confidence 1–5. "
    "Then give a 10-item ranked shortlist. If an item is weak, say why briefly.\n"
    f"Dataset date: {datetime.now().date()}.\n"
    "JSON array below:"
)

content = json.dumps(compact_arts, ensure_ascii=False)

msg = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=3000,
    temperature=0.2,
    system=system_prompt,
    messages=[{"role": "user", "content": f"{user_prompt}\n\n{content}"}],
)

out_dir = "analysis"
os.makedirs(out_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
out_path = os.path.join(out_dir, f"claude_analysis_{ts}.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(msg.content[0].text if hasattr(msg.content[0], "text") else str(msg.content))

print(f"Wrote analysis to {out_path}")
print((msg.content[0].text if hasattr(msg.content[0], "text") else str(msg.content))[:800])
