import os
import glob
import json
from datetime import datetime


def latest_file(pattern: str):
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to read {path}: {e}")
        return []


def ensure_str(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def main():
    os.makedirs("output", exist_ok=True)

    news_json = latest_file("scraped_data/news_articles_*.json")
    rc_json = latest_file("scraped_data/radio_canada_articles_*.json")

    articles = []
    source_files = []

    if news_json:
        data = load_json(news_json)
        if isinstance(data, list):
            articles.extend(data)
            source_files.append(news_json)
        else:
            print(f"Unexpected JSON structure in {news_json}; expected a list of records.")

    if rc_json:
        data = load_json(rc_json)
        if isinstance(data, list):
            articles.extend(data)
            source_files.append(rc_json)
        else:
            print(f"Unexpected JSON structure in {rc_json}; expected a list of records.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"output/combined_news_{timestamp}.txt"

    if not articles:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("No articles found to combine.\n")
            f.write("Checked sources:\n")
            f.write(f"- {news_json or 'none'}\n")
            f.write(f"- {rc_json or 'none'}\n")
        print(f"Wrote empty combined file at {out_path}")
        return

    # Sort for a consistent order
    articles.sort(key=lambda a: (ensure_str(a.get("source")), ensure_str(a.get("title"))))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"Combined articles: {len(articles)}\n")
        f.write("Source files used:\n")
        for s in source_files:
            f.write(f"- {s}\n")
        f.write("\n" + "=" * 80 + "\n\n")

        for idx, a in enumerate(articles, 1):
            f.write(f"Article {idx}\n")
            f.write(f"Source: {ensure_str(a.get('source'))}\n")
            f.write(f"Title: {ensure_str(a.get('title'))}\n")
            f.write(f"URL: {ensure_str(a.get('url'))}\n")
            f.write(f"Date Scraped: {ensure_str(a.get('date_scraped'))}\n")
            f.write("Content:\n")
            f.write(ensure_str(a.get("content")).strip() + "\n")
            f.write("\n" + "-" * 80 + "\n\n")

    print(f"Wrote combined file at {out_path}")


if __name__ == "__main__":
    main()