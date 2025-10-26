import os, re, json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

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

# Maximum size for each JSON chunk (about 90K tokens or roughly 70% of Claude's context window)
MAX_CHUNK_SIZE_BYTES = 90000

# Fixed capitalization - ensure this matches the reference in the main() function
def clean_text(text):
    """Clean up text by removing extra whitespace and special characters"""
    if text:
        # Remove newlines and extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    return ""

def get_full_url(url, base_url):
    """Convert relative URLs to absolute URLs"""
    if url.startswith('http'):
        return url
    elif url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        # Extract domain from base_url
        domain_match = re.match(r'(https?://[^/]+)', base_url)
        if domain_match:
            domain = domain_match.group(1)
            return domain + url
    return base_url + url

def extract_article_content(article_url, site):
    """Visit the article page and extract the full content"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": site['url'],
        "Connection": "keep-alive"
    }
    
    try:
        response = requests.get(article_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the content container
        content_container = soup.select_one(site['content_container'])
        if not content_container:
            print(f"No content container found for {article_url}")
            return ""
        
        # Remove excluded elements
        for exclude_selector in site['exclude_selectors']:
            for element in content_container.select(exclude_selector):
                element.decompose()
        
        # Extract all paragraphs
        paragraphs = content_container.select(site['content_selector'])
        
        # Combine paragraphs into full text
        full_text = "\n\n".join([clean_text(p.get_text()) for p in paragraphs if p.get_text().strip()])
        
        return full_text
    
    except Exception as e:
        print(f"Error extracting content from {article_url}: {e}")
        return ""

def find_article_links(soup, site, max_articles=15):
    """Find links to articles on the main page with deduplication"""
    article_links = []
    seen_urls = set()  # Track URLs we've already found
    article_elements = soup.select(site['article_selector'])
    
    for article in article_elements:
        try:
            # Find the link - could be the article element itself or a child element
            link = None
            if article.name == 'a' and 'href' in article.attrs:
                link = article['href']
            else:
                # Try to find the first link in the article element
                link_element = article.find('a')
                if link_element and 'href' in link_element.attrs:
                    link = link_element['href']
            
            if link:
                # Convert to absolute URL if needed
                full_url = get_full_url(link, site['base_url'])
                
                # Skip if we've already seen this URL
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                
                # Extract title if available at this stage
                title_element = article.select_one(site['title_selector'])
                title = clean_text(title_element.text) if title_element else ""
                
                article_links.append({
                    'url': full_url,
                    'title': title
                })
                
                if len(article_links) >= max_articles:
                    break
        except Exception as e:
            print(f"Error finding article link: {e}")
            continue
    
    return article_links

def scrape_website(site):
    """Scrape a single website for news articles including full content"""
    print(f"Scraping {site['name']}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,fr;q=0.8"
    }
    
    try:
        response = requests.get(site['url'], headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []
        
        # Find article links from the main page
        article_links = find_article_links(soup, site, site['max_articles'])
        
        print(f"Found {len(article_links)} articles on {site['name']}")
        
        for i, article_data in enumerate(article_links):
            try:
                article_url = article_data['url']
                preliminary_title = article_data['title']
                
                print(f"Processing article {i+1}/{len(article_links)}: {article_url}")
                
                # Extract the full content from the article page
                full_content = extract_article_content(article_url, site)
                
                # If we couldn't extract the title from the main page, try from the article page
                title = preliminary_title
                if not title:
                    # Try to revisit the article page to get the title if we don't have it
                    article_response = requests.get(article_url, headers=headers, timeout=10)
                    article_soup = BeautifulSoup(article_response.text, 'html.parser')
                    title_element = article_soup.select_one(site['title_selector'] + ", h1.title, h1")
                    if title_element:
                        title = clean_text(title_element.text)
                
                # Only add articles with content
                if title and full_content:
                    articles.append({
                        "source": site['name'],
                        "title": title,
                        "url": article_url,
                        "content": full_content,
                        "date_scraped": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                # Add random delay between article requests (1-3 seconds)
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"Error processing article: {e}")
                continue
                
        return articles
        
    except Exception as e:
        print(f"Error scraping {site['name']}: {e}")
        return []

def main():
    """Main function to scrape all websites and save data in manageable chunks"""
    all_articles = []
    
    # Global URL tracking to avoid duplicates across sites
    global_seen_urls = set()
    
    for site in NEWS_SITES:
        site_articles = scrape_website(site)
        
        # Additional global deduplication
        unique_articles = []
        for article in site_articles:
            if article['url'] not in global_seen_urls:
                global_seen_urls.add(article['url'])
                unique_articles.append(article)
        
        all_articles.extend(unique_articles)
        print(f"Scraped {len(unique_articles)} unique articles from {site['name']}")
        
        # Pause between sites to avoid overloading servers (5-10 seconds)
        pause_time = random.uniform(5, 10)
        print(f"Pausing for {pause_time:.2f} seconds before next site...")
        time.sleep(pause_time)
    
    # Create timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save all articles to a single CSV (for reference)
    csv_filename = f"scraped_data/news_articles_{timestamp}.csv"
    
    if all_articles:
        df = pd.DataFrame(all_articles)
        df.to_csv(csv_filename, index=False, encoding='utf-8')
        print(f"Scraped {len(all_articles)} articles and saved to {csv_filename}")
        
        # Save a single JSON file (may be large)
        json_filename = f"scraped_data/news_articles_{timestamp}.json"
        df.to_json(json_filename, orient='records', force_ascii=False, indent=2)
        print(f"Also saved data to {json_filename}")
        
        # Split into smaller chunks for easier upload to Claude
        chunks = chunk_articles(all_articles)
        chunk_base_filename = f"scraped_data/chunks/news_articles_{timestamp}"
        save_chunks(chunks, chunk_base_filename)
        print(f"Split data into {len(chunks)} chunks for easier uploading")
        
        # Create a summary file with minimal content
        summary_articles = []
        for article in all_articles:
            # Copy the article but truncate content
            summary = article.copy()
            if 'content' in summary:
                # Keep just the first 200 characters of content for the summary
                summary['content'] = summary['content'][:200] + "..." if len(summary['content']) > 200 else summary['content']
            summary_articles.append(summary)
            
        summary_filename = f"scraped_data/news_articles_summary_{timestamp}.json"
        with open(summary_filename, 'w', encoding='utf-8') as f:
            json.dump(summary_articles, f, ensure_ascii=False, indent=2)
        print(f"Created summary file at {summary_filename}")
    else:
        print("No articles were scraped.")

NEWS_SITES_BASE = [
    {
        "name": "CBC News Canada",
        "url": "https://www.cbc.ca/news/canada",
        "article_selector": ".card, .contentListCard, .story",
        "title_selector": "h3.headline, .headline, h3",
        "summary_selector": ".description, .deck, p",
        "content_container": ".story, article, main",
        "content_selector": "p",
        "exclude_selectors": [".media-caption", ".metadata", ".social-media"],
        "base_url": "https://www.cbc.ca",
        "max_articles": 18
    },
 
    {
        "name": "Quebec Chronicle-Telegraph",
        "url": "https://www.qctonline.com",
        "article_selector": ".article, .post",
        "title_selector": ".entry-title, h1, h2",
        "summary_selector": ".excerpt, .entry-summary",
        "content_container": ".entry-content, .article-content",
        "content_selector": "p",
        "exclude_selectors": [".widget", ".ad"],
        "base_url": "https://www.qctonline.com",
        "max_articles": 18
    }
]
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

def merged_sites(include_rc=True):
    sites = list(NEWS_SITES_BASE)
    if include_rc and RADIO_CANADA_SITES:
        sites.extend(RADIO_CANADA_SITES)
    return sites

def scrape_all_sites(include_rc=True, max_sites=None):
    all_articles = []
    successful_sites = 0
    for site in merged_sites(include_rc):
        if max_sites and successful_sites >= max_sites: break
        try:
            site_articles = scrape_website(site)
            if site_articles:
                all_articles.extend(site_articles)
                successful_sites += 1
        except Exception as e:
            print(f"Error scraping {site.get('name')}: {e}")
    # Deduplicate by URL
    seen = set(); unique = []
    for a in all_articles:
        url = a.get("url")
        if url and url not in seen:
            seen.add(url); unique.append(a)
    return unique

def save_single_json(articles, out_dir='scraped_data'):
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d')
    out_path = os.path.join(out_dir, f'news_articles_{ts}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f'Wrote {len(articles)} articles to {out_path}')
    return out_path

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--exclude-rc', action='store_true', help='Exclude Radio-Canada sources')
    ap.add_argument('--max-sites', type=int, default=None, help='Cap number of sites to scrape')
    args = ap.parse_args()
    arts = scrape_all_sites(include_rc=not args.exclude_rc, max_sites=args.max_sites)
    save_single_json(arts)

if __name__ == '__main__':
    main()
