import os
import anthropic
import json
from glob import glob

# Get your Claude API key from environment
claude_api_key = os.getenv("CLAUDE_API_KEY")
client = anthropic.Anthropic(api_key=claude_api_key)

# Find your latest news JSON file
files = sorted(glob("scraped_data/news_articles_*.json"), reverse=True)
if not files:
    raise Exception("No news articles JSON file found.")
input_file = files[0]

# Load articles
with open(input_file, "r", encoding="utf-8") as f:
    articles = json.load(f)

# Prompt: adjust as needed!
prompt = (
    "Analyze these news articles. Group them by topic (education, crime, politics, environment, etc). "
    "For each group, provide a short summary of the main events or controversies. "
    "Provide your answer as clear text."
)

# Prepare Claude message
message = client.messages.create(
    model="claude-3-sonnet-20240229",  # or latest available, check API docs
    max_tokens=2000,
    temperature=0.3,
    system="You are a helpful news analyst.",
    messages=[
        {"role": "user", "content": prompt + "\n\n" + json.dumps(articles)}
    ]
)

output_file = input_file.replace(".json", "_claude_analysis.txt")
with open(output_file, "w", encoding="utf-8") as f:
    f.write(message.content[0].text)

print(f"Analysis saved to {output_file}")
