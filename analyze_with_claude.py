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

# Storylines documentary evaluation prompt
storylines_prompt = """**Storylines** features character-driven documentary narratives – "stories you can't stop thinking about" – that illuminate broader issues. Each episode follows one compelling story with these key ingredients:

- **Central characters and a narrative arc:** Is there a clear story with protagonists or key people and a beginning-middle-end progression?
- **Human interest and emotional impact:** Does the story have a strong human angle that evokes emotion or empathy? Are the stakes personal and relatable?
- **Conflict or tension:** What is the central conflict, challenge, or question driving the story? Is there drama, tension, or a mystery that needs resolution?
- **Broader significance:** Does the story connect to larger themes or issues (social, cultural, political, historical) that would give listeners a deeper insight into "what's going on and why" beyond just this one case?
- **Novelty or surprise:** Is the story unusual or memorable in some way? Does it have an element that would intrigue listeners or make them want to share it (e.g. an unexpected twist, a unique situation, or a new perspective)?
- **Rich storytelling potential:** Are there vivid scenes, settings, or dialogues in the article that you can imagine being portrayed in audio? Would this story "sound good" with interviews or scene-setting (as if "mixed like a movie")?

**Task:** Read the news article provided below. Then, **write a brief analysis** evaluating if it has the ingredients listed above to be developed into a Storylines-style documentary.

Your response should include:
1. A **verdict** – start with **"Yes"** if it is a good candidate or **"No"** if it is not. *(If it's borderline, use your best judgment to pick yes or no.)*
2. A **short explanation** referencing the criteria. Point out which key elements are present in the story and which might be missing. For example, note the central characters and conflict, the emotional angle, the larger issue it reflects, and anything particularly compelling or lacking.

Be concise and specific.

Now, **evaluate the article** below for Storylines documentary potential:"""

# Process each article
yes_candidates = []
print(f"Evaluating {len(articles)} articles for Storylines potential...\n")

for i, article in enumerate(articles, 1):
    print(f"Processing article {i}/{len(articles)}...", end=" ")
    
    # Format article text (adjust keys based on your JSON structure)
    # If your articles have specific fields, format them nicely:
    if isinstance(article, dict):
        article_text = f"""
Title: {article.get('title', 'N/A')}
Source: {article.get('source', 'N/A')}
URL: {article.get('url', 'N/A')}
Date: {article.get('date', 'N/A')}

Content:
{article.get('content', article.get('text', json.dumps(article)))}
"""
    else:
        article_text = str(article)
    
    # Call Claude API
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1000,
        temperature=0.3,
        system="You are an experienced documentary producer evaluating story potential for Storylines.",
        messages=[
            {"role": "user", "content": f"{storylines_prompt}\n\n{article_text}"}
        ]
    )
    
    evaluation = message.content[0].text
    
    # Only keep "Yes" candidates
    if evaluation.strip().startswith("Yes"):
        yes_candidates.append({
            "article": article,
            "evaluation": evaluation
        })
        print("✓ YES - Story potential found!")
    else:
        print("✗ No")

print(f"\n{'='*80}")
print(f"Found {len(yes_candidates)} strong candidates out of {len(articles)} articles")
print(f"{'='*80}\n")

# Create email-ready output with only YES candidates
if yes_candidates:
    output_file = input_file.replace(".json", "_storylines_ideas.txt")
    
    with open(output_file, "w", encoding="utf-8") as f:
        # Email header
        f.write("STORYLINES EPISODE IDEAS\n")
        f.write(f"Generated: {input_file}\n")
        f.write(f"Total candidates found: {len(yes_candidates)}\n")
        f.write(f"\n{'='*80}\n\n")
        
        # Each candidate
        for i, result in enumerate(yes_candidates, 1):
            article = result["article"]
            
            f.write(f"STORY IDEA #{i}\n")
            f.write(f"{'-'*80}\n\n")
            
            # Article details
            if isinstance(article, dict):
                title = article.get('title', 'Untitled Story')
                f.write(f"📰 {title}\n\n")
                
                if article.get('source'):
                    f.write(f"Source: {article['source']}\n")
                if article.get('date'):
                    f.write(f"Date: {article['date']}\n")
                if article.get('url'):
                    f.write(f"Link: {article['url']}\n")
                f.write("\n")
            
            # Evaluation (remove the "Yes" prefix for cleaner reading)
            evaluation_text = result["evaluation"]
            if evaluation_text.strip().startswith("Yes"):
                # Remove "Yes" and any following punctuation/whitespace
                evaluation_text = evaluation_text.strip()[3:].lstrip(".,;: -")
            
            f.write("DOCUMENTARY POTENTIAL:\n")
            f.write(evaluation_text)
            f.write(f"\n\n{'='*80}\n\n")
    
    print(f"✅ Email-ready story ideas saved to: {output_file}")
else:
    print("❌ No strong candidates found in this batch.")
    # Still create a file noting this
    output_file = input_file.replace(".json", "_storylines_ideas.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("STORYLINES EPISODE IDEAS\n")
        f.write(f"Generated: {input_file}\n")
        f.write(f"\nNo strong documentary candidates found in this batch.\n")
    print(f"Report saved to: {output_file}")
