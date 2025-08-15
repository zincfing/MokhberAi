import os
import requests
import feedparser
import json
import random
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

# ==============================================================================
# --- 1. SCRIPT CONFIGURATION ---
# ==============================================================================

# --- AI PROVIDER SELECTION ---
# Choose your AI provider here. Options: 'gemini' or 'groq'
AI_PROVIDER = 'gemini' 

# --- GITHUB SECRETS & API KEYS ---
# Make sure to set these in your environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_API_KEY = os.getenv('GROQ_API_KEY') # Renamed from OPENROUTER_API_KEY for clarity
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- GROQ CONFIGURATION ---
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-70b-8192" # A powerful and common model on Groq
YOUR_SITE_URL = "https://github.com/SangeRooYakh/MokhberAi" # For Groq/OpenRouter headers
YOUR_APP_NAME = "Farsi Science News by AI"             # For Groq/OpenRouter headers

# --- GEMINI CONFIGURATION ---
# Note: Gemini 2.5 Pro does not exist. Use 'gemini-1.5-pro-latest' or 'gemini-1.5-flash-latest'
GEMINI_MODEL = "gemini-2.5-flash"

# 4. SOURCE LIST
# In your SOURCES dictionary...
SOURCES = {
    'Popular Science': {
        # --- MODIFIED: 'url' is now a list of feeds ---
        'url': [
            'https://www.popsci.com/category/science/feed/',
            'https://www.popsci.com/category/environment/feed/',
            'https://www.popsci.com/category/diy/feed/',
            'https://www.popsci.com/category/technology/feed/',
            'https://www.popsci.com/category/ai/feed',
            'https://www.popsci.com/category/space/feed',
            'https://www.popsci.com/category/ask-us-anything/feed',
            'https://www.popsci.com/category/biology/',
            'https://www.popsci.com/category/dinosaurs/',
            'https://www.popsci.com/category/evolution/'
        ],
        'category_fa': 'علوم_محبوب',
        'hashtag_en': '#PopularScience',
        'type': 'popsci',
        'post_format': 'scientific_news'
    },
    'NVIDIA News': {
        'url': ['https://nvidianews.nvidia.com/releases.xml',
                'http://feeds.feedburner.com/nvidiablog',
                'https://nvidianews.nvidia.com/cats/press_release.xml'
        ],
        'category_fa': 'اخبار_انویدیا',
        'hashtag_en': '#NVIDIANews',
        'type': 'nvidia_news',  # A unique type name for our new scraper
        'post_format': 'scientific_news' # Use the news format for posting
    }
  
}

POSTED_LINKS_FILE = 'posted_links5.txt'

# ==============================================================================
# --- Utility & Fetching Functions (Unchanged) ---
# ==============================================================================
def load_posted_links():
    try:
        with open(POSTED_LINKS_FILE, 'r', encoding='utf-8') as f: return set(line.strip() for line in f)
    except FileNotFoundError: return set()

def save_posted_links(links):
    with open(POSTED_LINKS_FILE, 'w', encoding='utf-8') as f:
        for link in sorted(links): f.write(link + '\n')
          
def scrape_popsci_article(url):
    """
    Fetches text and an image from a Popular Science article page by trying
    multiple selectors and prioritizing the 'srcset' attribute for the best image URL.
    """
    print(f"  Scraping Popular Science article: {url}")
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Scrape the main text content (no changes here) ---
        article_body = soup.select_one('div.content-wrapper')
        if not article_body:
            # ... (rest of the text scraping logic is the same)
            print("  Could not find article body with class 'content-wrapper'.")
            return {'text': None, 'image_url': None, 'doi_link': None}
        full_text = ' '.join(p.get_text(strip=True) for p in article_body.find_all('p'))

        # --- FINAL, MOST ROBUST IMAGE SCRAPING LOGIC ---
        image_url = None
        image_selectors = [
            'figure.featured-image img',
            'img.article-featured-image',
            'figure.wp-block-image img'
        ]

        for selector in image_selectors:
            image_tag = soup.select_one(selector)
            if image_tag:
                # --- NEW: Prioritize srcset ---
                if image_tag.has_attr('srcset'):
                    print(f"  Image tag found with srcset using selector: '{selector}'")
                    # srcset is a comma-separated list of "url width", e.g., "img.jpg 500w, img-large.jpg 1000w"
                    # We'll take the last one, which is usually the highest resolution.
                    # 1. Split by comma to get individual sources
                    # 2. Take the last one in the list
                    # 3. Strip whitespace
                    # 4. Split by space and take the first part (the URL)
                    highest_res_source = image_tag['srcset'].split(',')[-1].strip()
                    image_url = highest_res_source.split(' ')[0]
                    break # Found a good URL, exit the loop
                # --- Fallback to src ---
                elif image_tag.has_attr('src'):
                    print(f"  Image tag found with src (no srcset) using selector: '{selector}'")
                    image_url = image_tag['src']
                    break # Found a URL, exit the loop
        
        # --- No DOI link ---
        doi_link = None

        print(f"  Scraped: {len(full_text)} chars, Image: {'Yes' if image_url else 'No'}, DOI: No")
        return {'text': full_text, 'image_url': image_url, 'doi_link': doi_link}
    except Exception as e:
        print(f"  Error scraping Popular Science: {e}")
        return {'text': None, 'image_url': None, 'doi_link': None}
      
def scrape_nvidia_news_article(url):
    """Fetches text and an image from an NVIDIA News release page."""
    print(f"  Scraping NVIDIA News article: {url}")
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Scrape the main text content ---
        article_body = soup.select_one('div.entry-content')
        if not article_body:
            print("  Could not find article body with class 'entry-content'.")
            return {'text': None, 'image_url': None, 'doi_link': None}
        
        # Join all paragraph text within the main content area
        full_text = ' '.join(p.get_text(strip=True) for p in article_body.find_all('p'))

        # --- Scrape the main image ---
        image_url = None
        # The image is an <img> tag inside the <div class="entry-title ...">
        image_tag = soup.select_one('div.entry-title img')
        if image_tag and image_tag.has_attr('src'):
            image_url = image_tag['src']

        # --- No DOI link for news releases ---
        # We set this to None to maintain a consistent return format
        doi_link = None

        print(f"  Scraped: {len(full_text)} chars, Image: {'Yes' if image_url else 'No'}, DOI: No")
        return {'text': full_text, 'image_url': image_url, 'doi_link': doi_link}
    except Exception as e:
        print(f"  Error scraping NVIDIA News: {e}")
        return {'text': None, 'image_url': None, 'doi_link': None}
      
def scrape_sciencedaily_article(url):
    print(f"  Scraping ScienceDaily article: {url}")
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' }
    try:
        response = requests.get(url, headers=headers, timeout=20); response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        article_body = soup.select_one('div#story_text')
        if not article_body: return {'text': None, 'image_url': None, 'doi_link': None}

        full_text = ' '.join(p.get_text(strip=True) for p in article_body.find_all('p'))
        image_url = None
        image_tag = soup.select_one('figure.mainimg img')
        if image_tag and image_tag.has_attr('src'): image_url = urljoin(url, image_tag['src'])

        doi_link = None
        journal_ref_div = soup.select_one('div#journal_references')
        if journal_ref_div:
            doi_tag = journal_ref_div.find('a', href=re.compile(r'dx\.doi\.org'))
            if doi_tag and doi_tag.has_attr('href'): doi_link = doi_tag['href']

        print(f"  Scraped: {len(full_text)} chars, Image: {'Yes' if image_url else 'No'}, DOI: {'Yes' if doi_link else 'No'}")
        return {'text': full_text, 'image_url': image_url, 'doi_link': doi_link}
    except Exception as e:
        print(f"  Error scraping ScienceDaily: {e}"); return {'text': None, 'image_url': None, 'doi_link': None}

def scrape_phys_org_article(url):
    """Fetches text, an image, and a DOI link from a Phys.org article page."""
    print(f"  Scraping Phys.org article: {url}")
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' }
    try:
        response = requests.get(url, headers=headers, timeout=20); response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        article_body = soup.select_one('div.article-main')
        if not article_body: return {'text': None, 'image_url': None, 'doi_link': None}

        full_text = ' '.join(p.get_text(strip=True) for p in article_body.find_all('p'))

        image_url = None
        image_tag = article_body.select_one('figure.article-img img')
        if image_tag and image_tag.has_attr('src'):
            image_url = image_tag['src']

        doi_link = None
        doi_container = soup.select_one('div.article-main__more')
        if doi_container:
            doi_tag = doi_container.select_one('a[data-doi="1"]')
            if doi_tag and doi_tag.has_attr('href'):
                doi_link = doi_tag['href']

        print(f"  Scraped: {len(full_text)} chars, Image: {'Yes' if image_url else 'No'}, DOI: {'Yes' if doi_link else 'No'}")
        return {'text': full_text, 'image_url': image_url, 'doi_link': doi_link}
    except Exception as e:
        print(f"  Error scraping Phys.org: {e}"); return {'text': None, 'image_url': None, 'doi_link': None}

def scrape_full_article_page(url):
    print(f"  Scraping full article page: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=20); response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        article_body = soup.find('div', class_='c-article-body') or soup.find('div', class_='article__body')
        if not article_body: print("  Could not find main article body. Scraping failed."); return None
        full_text = ' '.join(p.get_text(strip=True) for p in article_body.find_all('p'))
        print(f"  Successfully scraped {len(full_text)} characters."); return full_text
    except Exception as e: print(f"  Error scraping article page: {e}"); return None

def scrape_pubmed_abstract(url):
    print(f"  Scraping PubMed abstract: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=20); response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        abstract_div = soup.find('div', class_='abstract-content')
        if not abstract_div: print("  Could not find abstract content. Scraping failed."); return None
        full_text = abstract_div.get_text(separator=' ', strip=True)
        print(f"  Successfully scraped {len(full_text)} characters from PubMed."); return full_text
    except Exception as e: print(f"  Error scraping PubMed abstract: {e}"); return None

def fetch_content_via_crossref(entry):
    print(f"  Attempting Crossref fetch for: {entry.title}")
    doi = None
    if hasattr(entry, 'dc_identifier'): doi = entry.dc_identifier.replace('doi:', '').strip()
    elif hasattr(entry, 'prism_doi'): doi = entry.prism_doi.strip()
    if not doi:
        match = re.search(r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', entry.link, re.IGNORECASE)
        if match: doi = match.group(0)
    if not doi: print("  Could not find or extract a DOI for this entry."); return None
    api_url = f"https://api.crossref.org/works/{doi}"; print(f"  Querying Crossref with DOI: {doi}")
    try:
        response = requests.get(api_url, timeout=15); response.raise_for_status()
        data = response.json()
        abstract_html = data.get('message', {}).get('abstract')
        if abstract_html:
            clean_abstract = BeautifulSoup(abstract_html, 'html.parser').get_text(separator=' ', strip=True)
            print(f"  Successfully fetched {len(clean_abstract)} characters from Crossref."); return clean_abstract
        else: print("  Crossref response did not contain an abstract."); return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404: print(f"  DOI not found in Crossref (404)."); return "NOT_FOUND_IN_API"
        else: print(f"  HTTP error contacting Crossref API: {e}"); return None
    except Exception as e: print(f"  General error contacting Crossref API: {e}"); return None

# ==============================================================================
# --- 3. AI ANALYSIS FUNCTIONS (REFACTORED) ---
# ==============================================================================

# --- Provider-Specific Implementations ---

def _get_analysis_from_groq(prompt, model):
    """Internal function to get a JSON response from the Groq API."""
    try:
        response = requests.post(
            url=GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "HTTP-Referer": YOUR_SITE_URL,
                "X-Title": YOUR_APP_NAME,
            },
            data=json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            })
        )
        response.raise_for_status()
        ai_response_json = response.json()['choices'][0]['message']['content']
        return json.loads(ai_response_json)
    except Exception as e:
        print(f"  Error communicating with Groq or parsing response: {e}")
        return None

def _get_analysis_from_gemini(prompt, model):
    """Internal function to get a JSON response from the Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=45)
        response.raise_for_status()
        ai_response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        return json.loads(ai_response_text)
    except requests.exceptions.RequestException as e:
        print(f"  Error communicating with Gemini API: {e}")
        return None
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"  Error parsing Gemini API response: {e}")
        return None
    except Exception as e:
        print(f"  An unexpected error occurred with Gemini: {e}")
        return None

# --- Unified Dispatcher Functions ---

def get_ai_paper_analysis(text_content):
    """
    Analyzes scientific text for a paper summary.
    This function dispatches the request to the provider set in AI_PROVIDER.
    """
    if not text_content or len(text_content) < 100:
        print("  Text too short, skipping AI paper analysis.")
        return None
        
    print(f"  Sending for DETAILED PAPER analysis via [{AI_PROVIDER.upper()}]...")
    prompt = f"""You are an expert science communicator. Analyze the following scientific text and provide a response ONLY in a valid JSON object format in modern Persian (Farsi). The JSON object must have these exact keys:
- "summary": A 3-4 sentence summary.
- "highlights": A list of 3 key finding strings.
- "keywords": A list of 4-5 keyword strings.
- "eli5": A single sentence explanation.
- "big_so_what": A 1-2 sentence explanation of why this matters.
- "analogy": A single sentence analogy.
- "next_steps": A list of 2-3 short strings about future research.

Scientific Text to Analyze:
---
{text_content[:15000]}
---"""

    if AI_PROVIDER == 'gemini':
        return _get_analysis_from_gemini(prompt, GEMINI_MODEL)
    elif AI_PROVIDER == 'groq':
        return _get_analysis_from_groq(prompt, GROQ_MODEL)
    else:
        print(f"  ERROR: Invalid AI_PROVIDER configured: {AI_PROVIDER}")
        return None

def get_ai_news_analysis(text_content):
    """
    Analyzes article text for a news summary.
    This function dispatches the request to the provider set in AI_PROVIDER.
    """
    if not text_content or len(text_content) < 50:
        print("  Text too short, skipping AI news analysis.")
        return None

    print(f"  Sending for GENERAL NEWS analysis via [{AI_PROVIDER.upper()}]...")
    prompt = f"""You are a science news editor. Summarize the following article for a general Persian-speaking audience. Provide a response ONLY in a valid JSON object format in modern Persian (Farsi).
The JSON object must have these exact keys:
- "catchy_title": An engaging, human-like title for the news piece.
- "summary": A simple paragraph, clear summary of the main points.
- "keywords": A list of 3-4 relevant keyword strings.
- "eli5": A single paragraph, ultra-simple explaining the core idea as if to a 5-year-old.

Article Text to Analyze:
---
{text_content[:15000]}
---"""
    if AI_PROVIDER == 'gemini':
        return _get_analysis_from_gemini(prompt, GEMINI_MODEL)
    elif AI_PROVIDER == 'groq':
        return _get_analysis_from_groq(prompt, GROQ_MODEL)
    else:
        print(f"  ERROR: Invalid AI_PROVIDER configured: {AI_PROVIDER}")
        return None

# ==============================================================================
# --- 4. TELEGRAM & FORMATTING FUNCTIONS ---
# ==============================================================================
def format_paper_telegram_message(original_title, source_name, source_info, ai_data, link):
    header = "🔬 <b>تحلیل مقاله علمی</b> 🔬\n\n"
    title_section = f"<b>{original_title}</b>\n\n"
    summary_section = f"📝 <b>خلاصه خودمونی</b>\n{ai_data.get('summary', '')}\n\n"
    highlights = ai_data.get('highlights', [])
    highlights_section = "✨ <b>نکات کلیدی</b>\n" + "\n".join([f"▪️ {item}" for item in highlights]) + "\n\n" if highlights else ""
    eli5_section = f"🧒 <b>به زبان ساده (ELI5)</b>\n{ai_data.get('eli5', '')}\n\n"
    big_so_what_section = f"🌍 <b>چرا این مهمه؟</b>\n{ai_data.get('big_so_what', '')}\n\n" if ai_data.get('big_so_what') else ""
    analogy_section = f"💡 <b>مثال برای درک بهتر</b>\n{ai_data.get('analogy', '')}\n\n" if ai_data.get('analogy') else ""
    next_steps = ai_data.get('next_steps', [])
    next_steps_section = "🚀 <b>قدم بعدی چیه؟</b>\n" + "\n".join([f"▪️ {item}" for item in next_steps]) + "\n\n" if next_steps else ""
    keywords = ai_data.get('keywords', [])
    keyword_tags = " ".join([f"#{kw.replace(' ', '_').replace('-', '_')}" for kw in keywords])
    tags_section = f"{source_info['hashtag_en']} #{source_info['category_fa'].replace(' ', '_')}\n{keyword_tags}"
    link_section = f"🔗 <a href='{link}'>مطالعه مقاله کامل در {source_name}</a>"
    return f"{header}{title_section}{summary_section}{highlights_section}{eli5_section}{big_so_what_section}{analogy_section}{next_steps_section}{link_section}\n\n{tags_section}"

# --- MODIFIED: Added doi_link parameter and section ---
def format_news_telegram_message(original_title, source_name, source_info, ai_data, link, doi_link=None):
    header = "📰 <b>خبر علمی</b> 📰\n\n"
    catchy_title = ai_data.get('catchy_title', original_title)
    summary = ai_data.get('summary', '')
    eli5 = ai_data.get('eli5', '')
    keywords = ai_data.get('keywords', [])

    title_section = f"<b>{catchy_title}</b>\n\n"
    summary_section = f"{summary}\n\n"
    eli5_section = f"🧒 <b>به زبان ساده (ELI5)</b>\n{eli5}\n\n" if eli5 else ""
    
    # --- NEW: Section for the DOI link ---
    doi_section = ""
    if doi_link:
        doi_section = f"📖 <b>منبع اصلی (DOI):</b>\n<a href='{doi_link}'>مشاهده مقاله پژوهشی</a>\n\n"

    keyword_tags = " ".join([f"#{kw.replace(' ', '_').replace('-', '_')}" for kw in keywords])
    tags_section = f"{source_info['hashtag_en']} #{source_info['category_fa'].replace(' ', '_')}\n{keyword_tags}"
    link_section = f"🔗 <a href='{link}'>مطالعه مطلب کامل در {source_name}</a>"
    
    return f"{header}{title_section}{summary_section}{eli5_section}{doi_section}{link_section}\n\n{tags_section}"
    
def send_to_telegram(message_text, ai_data, image_url=None):
    """
    Sends a message to Telegram.
    If an image_url is provided, it sends the photo with a catchy_title caption first,
    then sends the full message_text in a separate message.
    Otherwise, it sends a single text-only message.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("ERROR: TELEGRAM_TOKEN and TELEGRAM_CHANNEL_ID must be set.")
        return

    # --- NEW LOGIC FOR POSTS WITH PHOTOS ---
    if image_url:
        print("  Sending multipart message (photo + text)...")
        
        # Extract the catchy title for the photo's caption. Fallback to a generic title.
        caption = ai_data.get('catchy_title', "خبر علمی")

        # --- Part 1: Send the Photo with the Caption ---
        photo_api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        photo_payload = {
            'chat_id': TELEGRAM_CHANNEL_ID,
            'photo': image_url,
            'caption': caption, # Caption is just the catchy title
            'parse_mode': 'HTML'
        }
        
        try:
            photo_response = requests.post(photo_api_url, data=photo_payload, timeout=30)
            photo_response.raise_for_status()
            print(f"  ✅ Successfully sent photo with caption: '{caption}'")

            # --- Part 2: Send the Full Text Message Afterward ---
            # The full message_text is sent here, without truncation.
            text_api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            text_payload = {
                'chat_id': TELEGRAM_CHANNEL_ID,
                'text': message_text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            text_response = requests.post(text_api_url, data=text_payload, timeout=30)
            text_response.raise_for_status()
            print("  ✅ Successfully sent accompanying full text.")

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error sending multipart post to Telegram: {e}")
            # Check which response exists to provide better error details
            if 'photo_response' in locals() and photo_response.text:
                print(f"  -> Photo Response: {photo_response.text}")
            if 'text_response' in locals() and text_response.text:
                 print(f"  -> Text Response: {text_response.text}")

    # --- ORIGINAL LOGIC FOR TEXT-ONLY POSTS ---
    else:
        print("  Sending text-only message to Telegram...")
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        # We still keep the 4096 slice here as a safeguard for very long text-only posts.
        payload = {
            'chat_id': TELEGRAM_CHANNEL_ID,
            'text': message_text[:4096],
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()
            print("  ✅ Successfully sent text-only post to Telegram.")
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error sending post to Telegram: {e}")
            if 'response' in locals() and response.text:
                print(f"  -> Telegram response: {response.text}")

# ==============================================================================
# --- 5. MAIN EXECUTION LOGIC (MODIFIED) ---
# ==============================================================================
def process_feeds():
    posted_links = load_posted_links()
    new_links_found = False
    source_names = list(SOURCES.keys())
    random.shuffle(source_names) # Keep shuffling sources for variety

    for source_name in source_names:
        source_info = SOURCES[source_name]
        print(f"--- Checking Source: {source_name} (Type: {source_info['type']}) ---")

        # --- NEW LOGIC: Step 1 - Aggregate all new entries from all feeds for this source ---
        all_new_entries_for_this_source = []
        # The 'url' is now a list, so we loop through it
        for feed_url in source_info['url']:
            print(f"  Fetching feed: {feed_url}")
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    # Always use the link as the unique ID
                    link_to_check = entry.link
                    if link_to_check not in posted_links:
                        all_new_entries_for_this_source.append(entry)
            except Exception as e:
                print(f"  !! ERROR fetching or parsing feed {feed_url}: {e}")
        
        # --- NEW LOGIC: Step 2 - If we found any new entries, pick one randomly to process ---
        if all_new_entries_for_this_source:
            print(f"  Found {len(all_new_entries_for_this_source)} new items for {source_name}. Picking one randomly.")
            entry_to_process = random.choice(all_new_entries_for_this_source)
            link_to_check = entry_to_process.link # Get the link of the chosen one

            print(f"  Selected to process: {entry_to_process.title}")

            # --- The rest of the processing logic is the same, but uses 'entry_to_process' ---
            content_data = None
            source_type = source_info.get('type')
            
            if source_type == 'phys_org':
                content_data = scrape_phys_org_article(entry_to_process.link)
            elif source_type == 'sciencedaily':
                content_data = scrape_sciencedaily_article(entry_to_process.link)
            # (Keep other scrapers, but ensure they return a compatible structure if needed)
            # For now, we'll manually create a simple dict for them.
            elif source_type == 'full_page_scrape':
                text = scrape_full_article_page(entry_to_process.link)
                content_data = {'text': text, 'image_url': None, 'doi_link': None}
            elif source_type == 'nvidia_news':
                content_data = scrape_nvidia_news_article(entry_to_process.link)
            elif source_type == 'popsci':
                content_data = scrape_popsci_article(entry_to_process.link)
            elif source_type == 'pubmed':
                text = scrape_pubmed_abstract(entry_to_process.link)
                content_data = {'text': text, 'image_url': None, 'doi_link': None}
            elif source_type == 'crossref_doi':
                text = fetch_content_via_crossref(entry_to_process)
                content_data = {'text': text, 'image_url': None, 'doi_link': None}
            elif source_type == 'rss_content_only':
                text = None
                if 'content' in entry and entry.content:
                    text = BeautifulSoup(entry.content[0].value, 'html.parser').get_text(separator=' ', strip=True)
                    print(f"  Extracted {len(text)} chars from RSS.")
                content_data = {'text': text, 'image_url': None, 'doi_link': None}
            
            full_text = content_data.get('text') if content_data else None

            if full_text:
                ai_data = None
                message = None
                post_format = source_info['post_format']
                
                # *** KEY CHANGE: CALLING THE NEW DISPATCHER FUNCTIONS ***
                if post_format == 'scientific_paper':
                    ai_data = get_ai_paper_analysis(full_text) # Replaced old call
                    if ai_data:
                        message = format_paper_telegram_message(entry_to_process.title, source_name, source_info, ai_data, entry_to_process.link)
                elif post_format == 'scientific_news':
                    ai_data = get_ai_news_analysis(full_text) # Replaced old call
                    if ai_data:
                        doi_link = content_data.get('doi_link')
                        message = format_news_telegram_message(entry_to_process.title, source_name, source_info, ai_data, entry_to_process.link, doi_link=doi_link)

                if message:
                    image_url = content_data.get('image_url')
                    send_to_telegram(message, ai_data, image_url=image_url)
                    posted_links.add(link_to_check)
                    new_links_found = True
                else:
                    print("  Skipping post due to AI/formatting failure.")
            else:
                print(f"  No content extracted for '{entry_to_process.title}'.")
        else:
            print(f"  No new, processable items found for {source_name}.")

    if new_links_found:
        save_posted_links(posted_links)
    else:
        print("\n--- No new posts were made in this run. ---")

if __name__ == "__main__":
    # Final check for API keys before running
    if AI_PROVIDER == 'gemini' and not GEMINI_API_KEY:
        print("FATAL ERROR: AI_PROVIDER is 'gemini' but GEMINI_API_KEY is not set.")
    elif AI_PROVIDER == 'groq' and not GROQ_API_KEY:
         print("FATAL ERROR: AI_PROVIDER is 'groq' but GROQ_API_KEY is not set.")
    else:
        process_feeds()
