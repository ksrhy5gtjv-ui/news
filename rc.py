import requests
from bs4 import BeautifulSoup
import pandas as pd
import csv
from datetime import datetime
import time
import os
import re
import random
import json
import math

# Create directories to store scraped data
if not os.path.exists("scraped_data"):
    os.makedirs("scraped_data")
if not os.path.exists("scraped_data/chunks"):
    os.makedirs("scraped_data/chunks")

# Maximum size for each JSON chunk
MAX_CHUNK_SIZE_BYTES = 90000

# Radio-Canada sites to scrape
RADIO_CANADA_SITES = [
    {
        "name": "Radio-Canada",
        "url": "https://ici.radio-canada.ca/info",
        "max_articles": 15
    },
    {
        "name": "Radio-Canada Quebec",
        "url": "https://ici.radio-canada.ca/quebec",
        "max_articles": 15
    },
    {
        "name": "Radio-Canada Environnement",
        "url": "https://ici.radio-canada.ca/environnement",
        "max_articles": 15
    },
    {
        "name": "Radio-Canada Abitibi-Témiscamingue",
        "url": "https://ici.radio-canada.ca/abitibi-temiscamingue",
        "max_articles": 15
    },
    {
        "name": "Radio-Canada Gaspésie-Îles-de-la-Madeleine",
        "url": "https://ici.radio-canada.ca/gaspesie-iles-de-la-madeleine",
        "max_articles": 15
    },
    {
        "name": "Radio-Canada Estrie",
        "url": "https://ici.radio-canada.ca/estrie",
        "max_articles": 15
    },
    {
        "name": "Radio-Canada Grand Montréal",
        "url": "https://ici.radio-canada.ca/grandmontreal",
        "max_articles": 15
    },
    {
        "name": "Radio-Canada Mauricie",
        "url": "https://ici.radio-canada.ca/mauricie",
        "max_articles": 15
    },
    {
        "name": "Radio-Canada Ontario",
        "url": "https://ici.radio-canada.ca/ontario",
        "max_articles": 15
    },
    {
        "name": "Radio-Canada Saguenay-Lac-Saint-Jean",
        "url": "https://ici.radio-canada.ca/saguenay-lac-saint-jean",
        "max_articles": 15
    }
]

def clean_text(text):
    """Clean up text by removing extra whitespace and special characters"""
    if text:
        # Remove newlines and extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    return ""

def get_full_url(url, base_url="https://ici.radio-canada.ca"):
    """Convert relative URLs to absolute URLs"""
    if url.startswith('http'):
        return url
    elif url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        return base_url + url
    return base_url + '/' + url

def fetch_page(url):
    """Fetch a page with error handling and retry logic"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive"
    }
    
    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Fetching {url} (Attempt {attempt + 1}/{MAX_RETRIES})")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = random.uniform(2, 5) * (attempt + 1)
                print(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Failed to fetch {url} after {MAX_RETRIES} attempts.")
                return None

def extract_article_links(html, site_url):
    """Extract article links from a Radio-Canada page"""
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    article_links = []
    seen_urls = set()
    
    # Look for articles in various ways Radio-Canada might structure them
    # 1. Look for standard article cards
    article_elements = soup.select('article, .card, a[href*="/nouvelle/"], a[href*="/info/"]')
    
    # 2. Also look for div elements with certain classes that might be article containers
    article_elements.extend(soup.select('div.card, div.teaser, div.media'))
    
    print(f"Found {len(article_elements)} potential article elements")
    
    for article in article_elements:
        try:
            # Try to find the article link - either the element itself is a link or it contains a link
            link = None
            url = None
            
            # If the element itself is a link
            if article.name == 'a' and 'href' in article.attrs:
                url = article['href']
            else:
                # Look for links that might point to articles
                link_elements = article.select('a[href*="/nouvelle/"], a[href*="/info/"]')
                if link_elements:
                    url = link_elements[0]['href']
            
            if not url:
                continue
                
            # Ensure it's a full URL
            full_url = get_full_url(url)
            
            # Only include news article URLs (avoid videos, audio, etc.)
            if '/nouvelle/' not in full_url and '/info/' not in full_url:
                continue
                
            # Skip duplicates
            if full_url in seen_urls:
                continue
                
            seen_urls.add(full_url)
            
            # Extract the title
            title = None
            
            # Try various ways to find the title
            title_element = article.select_one('h1, h2, h3, .title, .headline')
            if title_element:
                title = clean_text(title_element.text)
            
            # If no title found but we have a link element, try to get title from link text or title attribute
            if not title and link and link.text.strip():
                title = clean_text(link.text)
            elif not title and 'title' in article.attrs:
                title = clean_text(article['title'])
            
            if not title:
                title = f"Article from {site_url}"
            
            article_links.append({
                'url': full_url,
                'title': title
            })
            
            print(f"Found article: {title} - {full_url}")
            
        except Exception as e:
            print(f"Error processing article element: {e}")
            continue
    
    return article_links

def extract_article_content(url):
    """Extract content from a Radio-Canada article"""
    html = fetch_page(url)
    if not html:
        return None, None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract title if not already found
    title = None
    title_element = soup.select_one('h1, .article-title, .title')
    if title_element:
        title = clean_text(title_element.text)
    
    # Extract content
    content = ""
    
    # Try different selectors for article content
    content_selectors = [
        'article p', 
        '.article-body-container p', 
        '.article-body p', 
        '.editorial-content p',
        'main p',
        '.content p'
    ]
    
    for selector in content_selectors:
        paragraphs = soup.select(selector)
        if paragraphs:
            content = "\n\n".join([clean_text(p.text) for p in paragraphs if p.text.strip()])
            break
    
    # If still no content, try a more generic approach
    if not content:
        # Try to find the main content container
        main_content = soup.select_one('article, .article, main, .article-content, .content')
        if main_content:
            # Get all paragraphs within the main content
            paragraphs = main_content.find_all('p')
            content = "\n\n".join([clean_text(p.text) for p in paragraphs if p.text.strip()])
    
    return title, content

def scrape_radio_canada_site(site):
    """Scrape a Radio-Canada site"""
    print(f"Scraping {site['name']}...")
    
    articles = []
    
    # Fetch the main page
    html = fetch_page(site['url'])
    if not html:
        print(f"Failed to fetch {site['name']} main page.")
        return []
    
    # Extract article links
    article_links = extract_article_links(html, site['url'])
    print(f"Found {len(article_links)} articles on {site['name']}")
    
    # Limit to maximum number of articles
    article_links = article_links[:site['max_articles']]
    
    # Process each article
    for i, article_data in enumerate(article_links):
        try:
            article_url = article_data['url']
            preliminary_title = article_data['title']
            
            print(f"Processing article {i+1}/{len(article_links)}: {article_url}")
            
            # Extract article content
            title, content = extract_article_content(article_url)
            
            # Use preliminary title if no title was found
            if not title:
                title = preliminary_title
            
            # Only add articles with content
            if title and content and len(content) > 100:  # Ensure we have substantial content
                articles.append({
                    "source": site['name'],
                    "title": title,
                    "url": article_url,
                    "content": content,
                    "date_scraped": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                print(f"Added article: {title}")
            else:
                print(f"Skipping article: Missing title or sufficient content for {article_url}")
            
            # Add a delay between article requests
            delay = random.uniform(1, 3)
            print(f"Waiting {delay:.2f} seconds before next article...")
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error processing article: {e}")
            continue
    
    return articles

def chunk_articles(articles, max_size_bytes=MAX_CHUNK_SIZE_BYTES):
    """Split articles into chunks that fit within the maximum size limit"""
    chunks = []
    current_chunk = []
    current_size = 0
    
    for article in articles:
        # Estimate the size of the article in bytes (approximate)
        article_json = json.dumps(article, ensure_ascii=False)
        article_size = len(article_json.encode('utf-8'))
        
        # If adding this article would exceed the maximum size, start a new chunk
        if current_size + article_size > max_size_bytes and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_size = 0
        
        # Add the article to the current chunk
        current_chunk.append(article)
        current_size += article_size
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def save_chunks(chunks, base_filename):
    """Save chunks to separate JSON files"""
    for i, chunk in enumerate(chunks):
        chunk_filename = f"{base_filename}_chunk_{i+1}_of_{len(chunks)}.json"
        with open(chunk_filename, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
        print(f"Saved chunk {i+1}/{len(chunks)} with {len(chunk)} articles to {chunk_filename}")
        
        # Calculate approximate size
        file_size = os.path.getsize(chunk_filename)
        print(f"Chunk size: {file_size / 1024:.2f} KB")

def main():
    """Main function to scrape Radio-Canada sites"""
    all_articles = []
    
    # Global URL tracking to avoid duplicates across sites
    global_seen_urls = set()
    
    # Track successful sites
    successful_sites = 0
    
    for site in RADIO_CANADA_SITES:
        try:
            site_articles = scrape_radio_canada_site(site)
            
            # Deduplicate articles
            unique_articles = []
            for article in site_articles:
                if article['url'] not in global_seen_urls:
                    global_seen_urls.add(article['url'])
                    unique_articles.append(article)
            
            all_articles.extend(unique_articles)
            print(f"Scraped {len(unique_articles)} unique articles from {site['name']}")
            
            if len(unique_articles) > 0:
                successful_sites += 1
            
            # Pause between sites
            pause_time = random.uniform(3, 7)
            print(f"Pausing for {pause_time:.2f} seconds before next site...")
            time.sleep(pause_time)
            
        except Exception as e:
            print(f"Error processing site {site['name']}: {e}")
            continue
    
    # Create timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save all articles to files
    if all_articles:
        print(f"Successfully scraped {successful_sites} out of {len(RADIO_CANADA_SITES)} sites")
        print(f"Total articles collected: {len(all_articles)}")
        
        # Save to CSV
        csv_filename = f"scraped_data/radio_canada_articles_{timestamp}.csv"
        df = pd.DataFrame(all_articles)
        df.to_csv(csv_filename, index=False, encoding='utf-8')
        print(f"Saved articles to {csv_filename}")
        
        # Save to JSON
        json_filename = f"scraped_data/radio_canada_articles_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        print(f"Also saved data to {json_filename}")
        
        # Split into chunks
        chunks = chunk_articles(all_articles)
        chunk_base_filename = f"scraped_data/chunks/radio_canada_articles_{timestamp}"
        save_chunks(chunks, chunk_base_filename)
        print(f"Split data into {len(chunks)} chunks for easier uploading")
        
        # Create summary file
        summary_articles = []
        for article in all_articles:
            summary = article.copy()
            if 'content' in summary:
                summary['content'] = summary['content'][:200] + "..." if len(summary['content']) > 200 else summary['content']
            summary_articles.append(summary)
        
        summary_filename = f"scraped_data/radio_canada_articles_summary_{timestamp}.json"
        with open(summary_filename, 'w', encoding='utf-8') as f:
            json.dump(summary_articles, f, ensure_ascii=False, indent=2)
        print(f"Created summary file at {summary_filename}")
    else:
        print("No articles were scraped.")

if __name__ == "__main__":
    main()
