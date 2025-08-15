import os
import requests
import feedparser
import json
import random
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from datetime import datetime


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
PODCASTS = {
    'Philosophy Bites': {
        # A list of index pages to scrape from https://philosophybites.com/episodes/
        'index_url': [
            'https://philosophybites.com/episodes/',
            'https://philosophybites.com/episodes/?e-filter-6d27afa-podcast_category=ethics-of-health-and-medicine',
            'https://philosophybites.com/episodes/?e-filter-6d27afa-podcast_category=about-philosophy',
            'https://philosophybites.com/episodes/?e-filter-6d27afa-podcast_category=body-and-mind',
            'https://philosophybites.com/episodes/?e-filter-6d27afa-podcast_category=decision-making-and-responsibility',
            'https://philosophybites.com/episodes/?e-filter-6d27afa-podcast_category=existence-and-reality',
            'https://philosophybites.com/episodes/?e-filter-6d27afa-podcast_category=knowledge-thought-and-belief',
            'https://philosophybites.com/episodes/?e-filter-6d27afa-podcast_category=religion',
            'https://philosophybites.com/episodes/?e-filter-6d27afa-podcast_category=traditional-ethical-theories'
        ],
        'history_file': 'posted_philosophy_bites_links.txt',
        'scraper_type': 'philosophybites_web', # New dedicated type
        'category_fa': 'پادکست_گاز_فلسفی',
        'hashtag_en': '#PhilosophyBites'
    },
    'Philosophize This!': {
        # This is not a feed URL, but the main transcript index page
        'index_url': 'https://www.philosophizethis.org/transcripts',
        'history_file': 'posted_philosophize_this_links.txt',
        'scraper_type': 'philosophizethis_web', # New dedicated type
        'category_fa': 'پادکست_فلسفیش‌ـ‌کن',
        'hashtag_en': '#PhilosophizeThis'
    },    
    'Podcast Summaries': {
        # This source pulls from multiple feeds
        'feed_url': [
            'https://feeds.megaphone.fm/QCD6036500916',         # Philosophize This!
            'https://partiallyexaminedlife.libsyn.com/rss',     #The Partially Examined Life is a philosophy podcast
            'https://feeds.megaphone.fm/RSV1597324942',         #The Tucker Carlson Show
            'https://feeds.simplecast.com/C0fPpQ64'             #The Ben Shapiro Show
        ],
        'history_file': 'posted_podcastsummary_links.txt',  # A shared history file for the group
        'scraper_type': 'multi_rss_random',             # Our new type for this logic
        'category_fa': 'خلاصه‌پادکست',
        'hashtag_en': '#PodcastSummary'
    },    
    'Huberman Lab': {
        'feed_url': ['https://feeds.megaphone.fm/hubermanlab'],
        'history_file': 'posted_hubermanlab_links.txt',
        'scraper_type': 'podscribe_rss',
        'category_fa': 'پادکست_هابرمن',      # New
        'hashtag_en': '#HubermanLab'        # New
    },
    'The Jordan B. Peterson': {
        'feed_url': ['https://feeds.simplecast.com/vsy1m5LV'],
        'history_file': 'posted_JordanPeterson_links.txt',
        'scraper_type': 'podscribe_rss',
        'category_fa': 'پادکست_پیترسون',      # New
        'hashtag_en': '#JordanPeterson'        # New
    },    
    'Lex Fridman Podcast': {
        'feed_url': ['https://lexfridman.com/feed/podcast/'],
        'history_file': 'posted_lexfridman_links.txt',
        'scraper_type': 'lexfridman',
        'category_fa': 'پادکست_لکس_فریدمن', # New
        'hashtag_en': '#LexFridmanPodcast'   # New
    },
}
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

# ==============================================================================
# --- NEW: Podcast Scraping & Analysis Functions ---
# ==============================================================================
def scrape_philosophybites_index_page(url):
    """
    Scrapes a Philosophy Bites index/category page to find all episode links.
    Returns a list of dictionaries, each with 'url' and 'title'.
    """
    print(f"  Scraping Philosophy Bites index page: {url}")
    headers = { 'User-Agent': 'Mozilla/5.0' }
    episodes = []
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Each episode is in a 'div' with class 'e-loop-item'
        episode_blocks = soup.select('div.e-loop-item')
        
        for block in episode_blocks:
            link_tag = block.find('a')
            title_tag = block.select_one('h3.elementor-heading-title')
            
            if link_tag and link_tag.has_attr('href') and title_tag:
                episodes.append({
                    'url': link_tag['href'],
                    'title': title_tag.get_text(strip=True)
                })
        
        print(f"  Found {len(episodes)} episodes on this page.")
        return episodes

    except Exception as e:
        print(f"  Error scraping Philosophy Bites index page: {e}")
        return []

def scrape_philosophybites_episode_page(url):
    """
    Scrapes a Philosophy Bites episode page for the transcript and MP3 URL.
    Returns a dictionary: {'transcript': '...', 'mp3_url': '...'}.
    """
    print(f"  Scraping episode page: {url}")
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Initialize return values ---
        full_text = None
        mp3_url = None

        # --- Find the Transcript ---
        transcript_heading = soup.find('h3', string=re.compile(r'^\s*TRANSCRIPT\s*$', re.IGNORECASE))
        if transcript_heading:
            heading_widget = transcript_heading.find_parent('div', class_='elementor-widget')
            if heading_widget:
                transcript_container = heading_widget.find_next_sibling('div', class_='elementor-widget')
                if transcript_container:
                    paragraphs = transcript_container.find_all('p')
                    if paragraphs:
                        full_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
                        print(f"  Successfully scraped {len(full_text)} characters from transcript.")
        
        if not full_text:
            print("  Could not find transcript content.")

        # --- Find the MP3 URL ---
        audio_tag = soup.find('audio')
        if audio_tag and audio_tag.find('source') and audio_tag.source.has_attr('src'):
            mp3_url = audio_tag.source['src']
            print(f"  Successfully found MP3 URL.")
        else:
            print("  Could not find MP3 URL.")
            
        # Return whatever was found
        return {'transcript': full_text, 'mp3_url': mp3_url}
        
    except requests.exceptions.RequestException as e:
        print(f"  Network error scraping episode page {url}: {e}")
        return {'transcript': None, 'mp3_url': None}
    except Exception as e:
        print(f"  An unexpected error occurred while scraping {url}: {e}")
        return {'transcript': None, 'mp3_url': None}

def scrape_philosophizethis_index_page(url):
    """
    Scrapes the main transcripts page to find the URL of the most recent episode.
    """
    print(f"  Scraping Philosophize This index page: {url}")
    headers = { 'User-Agent': 'Mozilla/5.0' }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the first item in the archive list, which is the latest one
        latest_item = soup.select_one('li.archive-item a.archive-item-link')
        
        if not latest_item or not latest_item.has_attr('href'):
            print("  Could not find the link for the latest transcript.")
            return None
        
        # The href is a relative path, so we need to join it with the base URL
        transcript_path = latest_item['href']
        transcript_url = urljoin(url, transcript_path)
        
        print(f"  Found latest transcript URL: {transcript_url}")
        return transcript_url

    except Exception as e:
        print(f"  Error scraping Philosophize This index page: {e}")
        return None

def scrape_philosophizethis_transcript_page(url):
    """
    Scrapes the full text content from a Philosophize This! transcript page.
    """
    print(f"  Scraping transcript page: {url}")
    headers = { 'User-Agent': 'Mozilla/5.0' }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # The main content area that holds the paragraphs
        content_area = soup.select_one('div.sqs-block-content')
        
        if not content_area:
            print("  Could not find transcript content in div.sqs-block-content.")
            return None
        
        # Find all <p> tags within that content area
        paragraphs = content_area.find_all('p')
        if not paragraphs:
            print("  Found content area, but no <p> tags inside. Aborting.")
            return None

        # Join the text from all found paragraphs
        full_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
        
        print(f"  Successfully scraped {len(full_text)} characters from transcript.")
        return full_text
    except Exception as e:
        print(f"  Error scraping transcript page {url}: {e}")
        return None

def format_rfc2822_date(date_string):
    """Parses an RFC 2822 date string and returns it as 'Month Day, Year'."""
    try:
        # The format string for RFC 2822 (+0000 timezone)
        dt_object = datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %z')
        return dt_object.strftime('%B %d, %Y') # e.g., "July 24, 2025"
    except (ValueError, TypeError):
        # Fallback for unexpected formats or if date_string is None
        return None
    
def scrape_lexfridman_episode_page(url):
    """
    From the main episode page, scrapes the transcript URL and the YouTube embed URL.
    This version uses more robust selectors.
    """
    print(f"  Scraping Lex Fridman episode page: {url}")
    headers = { 'User-Agent': 'Mozilla/5.0' }
    try:
        # Remove tracking parameters from the URL to get the canonical page
        clean_url = url.split('?')[0]
        print(f"  Using cleaned URL: {clean_url}")
        
        response = requests.get(clean_url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        transcript_url = None
        youtube_url = None

        # --- Find the transcript link (no changes needed here) ---
        transcript_header = soup.find('b', string=re.compile(r'Transcript:'))
        if transcript_header and transcript_header.find_next_sibling('a'):
            transcript_url = transcript_header.find_next_sibling('a')['href']

        # --- NEW ROBUST YOUTUBE FINDER ---
        # Try to find any iframe with a youtube embed source. This is the most reliable method.
        youtube_iframe = soup.select_one('iframe[src*="youtube.com/embed/"]')
        if youtube_iframe:
            youtube_url = youtube_iframe['src']
        else:
            # Fallback to the original method just in case
            player_div = soup.select_one('div.episode-player iframe')
            if player_div and player_div.has_attr('src'):
                youtube_url = player_div['src']
        
        print(f"  - Transcript URL: {'Found' if transcript_url else 'Not Found'}")
        print(f"  - YouTube URL: {'Found' if youtube_url else 'Not Found'}")
        return {'transcript_url': transcript_url, 'youtube_url': youtube_url}

    except Exception as e:
        print(f"  Error scraping episode page {url}: {e}")
        return {'transcript_url': None, 'youtube_url': None}

def scrape_lexfridman_transcript_page(url):
    """
    Scrapes the full text content from a Lex Fridman transcript page.
    This version correctly targets the <span class="ts-text"> tags that hold the transcript.
    """
    print(f"  Scraping transcript page: {url}")
    headers = { 'User-Agent': 'Mozilla/5.0' }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        main_content = soup.select_one('div.entry-content')
        if not main_content:
            print("  Could not find transcript container div.entry-content.")
            return None
        
        # --- CORRECTED SCRAPING LOGIC ---
        # Find all <span> tags with the class "ts-text" inside the main content.
        transcript_spans = main_content.select('span.ts-text')
        
        if not transcript_spans:
            print("  Found entry-content, but no 'ts-text' spans inside. Aborting.")
            return None
        
        # Join the text from all found spans into a single string.
        full_text = ' '.join(span.get_text(strip=True) for span in transcript_spans)
        
        print(f"  Successfully scraped {len(full_text)} characters from transcript.")
        return full_text
    except Exception as e:
        print(f"  Error scraping transcript page {url}: {e}")
        return None

def get_ai_podcast_analysis(transcript_text):
    """
    Analyzes a podcast transcript and extracts key information.
    v2: Asks for hashtags.
    """
    if not transcript_text or len(transcript_text) < 500:
        print("  Transcript too short, skipping AI podcast analysis.")
        return None

    print(f"  Sending transcript for PODCAST analysis via [{AI_PROVIDER.upper()}]...")
    prompt = f"""You are a podcast analyst. Your task is to analyze the following podcast transcript and summarize it for a general audience. Provide a response ONLY in a valid JSON object format in modern Persian (Farsi).

The JSON object must have these exact keys:
- "guest_name": The full name of the guest being interviewed. if not, mention "بدون مهمان"
- "summary": A concise, engaging 2-3 paragraph summary of the entire conversation.
- "key_topics": A list of 4-5 main topics or ideas discussed, as short strings.
- "notable_questions": A list of 2-3 interesting questions Lex asked his guest.
- "memorable_quote": One impactful or thought-provoking quote from the guest (or Lex if solo).
- "hashtags": A list of 4-5 relevant Persian hashtags (without the # symbol).

Podcast Transcript to Analyze:
---
{transcript_text[:25000]} 
---"""

    # Reuses existing AI provider logic
    if AI_PROVIDER == 'gemini':
        return _get_analysis_from_gemini(prompt, GEMINI_MODEL)
    elif AI_PROVIDER == 'groq':
        return _get_analysis_from_groq(prompt, GROQ_MODEL)
    else:
        print(f"  ERROR: Invalid AI_PROVIDER configured: {AI_PROVIDER}")
        return None
    
def get_ai_rss_podcast_analysis(title, description):
    """
    Analyzes podcast data taken directly from an RSS feed description.
    v2: Asks for hashtags.
    """
    if not description or len(description) < 100:
        print("  RSS description is too short, skipping AI analysis.")
        return None

    print(f"  Sending RSS content for PODCAST analysis via [{AI_PROVIDER.upper()}]...")
    prompt = f"""You are a podcast summarizer. Your task is to refine and structure the following podcast description into a more engaging format for a social media post. The original podcast title is "{title}". Provide a response ONLY in a valid JSON object format in modern Persian (Farsi).

The JSON object must have these exact keys:
- "catchy_title": Create a new, engaging title for the social media post based on the episode's content.
- "summary": Rewrite the provided description into a clean, easy-to-read paragraph.
- "key_takeaways": From the description, extract a list of 3-4 key takeaways or topics as short, bullet-point-style strings.
- "guest_info": Identify the guest if mentioned, otherwise state it's a solo episode.
- "hashtags": A list of 4-5 relevant Persian hashtags (without the # symbol).

Podcast Description to Analyze:
---
{description[:15000]} 
---"""

    # This reuses your existing AI provider logic
    if AI_PROVIDER == 'gemini':
        return _get_analysis_from_gemini(prompt, GEMINI_MODEL)
    elif AI_PROVIDER == 'groq':
        return _get_analysis_from_groq(prompt, GROQ_MODEL)
    else:
        print(f"  ERROR: Invalid AI_PROVIDER configured: {AI_PROVIDER}")
        return None
def format_rss_podcast_telegram_message(ai_data, original_title, pub_date, mp3_url, podcaster_config):
    """
    Formats the AI analysis of an RSS-based podcast into an engaging post.
    v3: Uses the new standard format with header, date, and full tags.
    """
    # Extract data from AI and config
    catchy_title = ai_data.get('catchy_title', original_title)
    summary = ai_data.get('summary', 'خلاصه‌ای موجود نیست.')
    takeaways = ai_data.get('key_takeaways', [])
    guest = ai_data.get('guest_info', 'نامشخص')
    ai_hashtags = ai_data.get('hashtags', [])
    
    podcaster_name = podcaster_config['name']
    hardcoded_hashtag_en = podcaster_config['hashtag_en']
    hardcoded_category_fa = podcaster_config['category_fa']

    # Format the header
    header = f"🎙️ <b>{catchy_title}</b> 🎙️"
    
    # Format metadata line
    date_formatted = format_rfc2822_date(pub_date)
    metadata_line = f"<i>از پادکست {podcaster_name}"
    if date_formatted:
        metadata_line += f" | {date_formatted}</i>\n\n"
    else:
        metadata_line += "</i>\n\n"
        
    # Format main sections
    guest_section = f"👤 <b>مهمان یا موضوع:</b> {guest}\n\n"
    summary_section = f"📝 <b>چکیده گفتگو:</b>\n{summary}\n\n"
    takeaways_section = "📌 <b>نکات کلیدی این قسمت:</b>\n" + "\n".join([f"▪️ {item}" for item in takeaways]) + "\n\n" if takeaways else ""
    
    # Format links and tags
    listen_section = f"🎧 <a href='{mp3_url}'>برای شنیدن کامل این قسمت کلیک کنید</a>"
    
    ai_hashtag_line = " ".join([f"#{tag.replace(' ', '_')}" for tag in ai_hashtags])
    full_hashtag_line = f"{hardcoded_hashtag_en} #{hardcoded_category_fa}\n{ai_hashtag_line}"

    return f"{header}\n{metadata_line}{guest_section}{summary_section}{takeaways_section}{listen_section}\n\n{full_hashtag_line}"


def send_simple_podcast_to_telegram(message_text):
    """Sends a single text-based message for a podcast."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("ERROR: TELEGRAM_TOKEN and TELEGRAM_CHANNEL_ID must be set.")
        return False
    
    try:
        print("  Sending simple text message to Telegram...")
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHANNEL_ID,
            'text': message_text[:4096],
            'parse_mode': 'HTML',
            'disable_web_page_preview': False # Keep preview for the MP3 link
        }
        response = requests.post(url, data=payload, timeout=30)
        response.raise_for_status()
        print("  ✅ Successfully sent podcast post.")
        return True
    except Exception as e:
        print(f"  ❌ Error sending simple podcast post to Telegram: {e}")
        if 'response' in locals(): print(f"  -> Response: {response.text}")
        return False

def format_podcast_telegram_message(ai_data, original_title, pub_date, podcaster_config, mp3_url=None):
    """
    Formats the AI analysis of a transcript-based podcast into an engaging post.
    v3: Now includes an optional MP3 link.
    """
    # Extract data from AI and config
    guest = ai_data.get('guest_name', 'نامشخص')
    summary = ai_data.get('summary', 'خلاصه‌ای موجود نیست.')
    topics = ai_data.get('key_topics', [])
    questions = ai_data.get('notable_questions', [])
    quote = ai_data.get('memorable_quote', '')
    ai_hashtags = ai_data.get('hashtags', [])
    
    podcaster_name = podcaster_config['name']
    hardcoded_hashtag_en = podcaster_config['hashtag_en']
    hardcoded_category_fa = podcaster_config['category_fa']

    # Format the header
    header = f"🎙️ <b>پادکست: {original_title}</b> 🎙️"

    # Format metadata line
    date_formatted = format_rfc2822_date(pub_date)
    metadata_line = f"<i>از پادکست {podcaster_name}"
    if date_formatted:
        metadata_line += f" | {date_formatted}</i>\n\n"
    else:
        metadata_line += "</i>\n\n"
        
    # Format the main sections
    guest_section = f"👤 <b>مهمان این قسمت:</b> {guest}\n\n"
    summary_section = f"📝 <b>چکیده گفتگو:</b>\n{summary}\n\n"
    topics_section = "🧠 **موضوعات کلیدی:**\n" + "\n".join([f"▪️ {item}" for item in topics]) + "\n\n" if topics else ""
    questions_section = "❓ **پرسش‌های جالب:**\n" + "\n".join([f"▪️ {item}" for item in questions]) + "\n\n" if questions else ""
    quote_section = f"💬 **نقل‌قول به یاد ماندنی:**\n*«{quote}»*\n\n" if quote else ""

    # --- NEW: Conditionally add the listen link ---
    listen_section = f"🎧 <a href='{mp3_url}'>برای شنیدن کامل این قسمت کلیک کنید</a>\n\n" if mp3_url else ""
    
    # Format all tags
    ai_hashtag_line = " ".join([f"#{tag.replace(' ', '_')}" for tag in ai_hashtags])
    full_hashtag_line = f"{hardcoded_hashtag_en} #{hardcoded_category_fa}\n{ai_hashtag_line}"

    # Note: The YouTube link is sent separately, so we don't include it here.
    return f"{header}\n{metadata_line}{guest_section}{summary_section}{topics_section}{questions_section}{quote_section}{listen_section}{full_hashtag_line}"


def send_podcast_to_telegram(youtube_url, analysis_text, episode_title):
    """
    Sends a two-part message for the podcast: video first, then analysis as a reply.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("ERROR: TELEGRAM_TOKEN and TELEGRAM_CHANNEL_ID must be set.")
        return False
    
    try:
        # --- Part 1: Send the video link for embedding ---
        print("  Sending podcast video link to Telegram...")
        video_message_text = f"🎙️ **پادکست روز: {episode_title}**\n\n{youtube_url}"
        video_url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        video_payload = {
            'chat_id': TELEGRAM_CHANNEL_ID,
            'text': video_message_text,
            'disable_web_page_preview': False # IMPORTANT: Ensure preview is ON
        }
        video_response = requests.post(video_url_api, data=video_payload, timeout=30)
        video_response.raise_for_status()
        video_message_id = video_response.json()['result']['message_id']
        print("  ✅ Successfully sent video link.")

        # --- Part 2: Send the analysis as a reply to the video message ---
        print("  Sending podcast analysis as a reply...")
        analysis_url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        analysis_payload = {
            'chat_id': TELEGRAM_CHANNEL_ID,
            'text': analysis_text[:4096],
            'parse_mode': 'HTML',
            'reply_to_message_id': video_message_id
        }
        analysis_response = requests.post(analysis_url_api, data=analysis_payload, timeout=30)
        analysis_response.raise_for_status()
        print("  ✅ Successfully sent analysis.")
        return True

    except Exception as e:
        print(f"  ❌ Error sending podcast post to Telegram: {e}")
        if 'video_response' in locals(): print(f"  -> Response: {video_response.text}")
        return False

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

# ==============================================================================
# --- 4. TELEGRAM & FORMATTING FUNCTIONS ---
# ==============================================================================
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
# --- NEW: Main Podcast Execution Logic ---
# ==============================================================================
def process_all_podcasts():
    podcast_names = list(PODCASTS.keys())
    random.shuffle(podcast_names)

    for name in podcast_names:
        podcaster_config = PODCASTS[name]
        podcaster_config['name'] = name 
        
        print(f"\n--- Checking Podcast Group: {name} ---")

        history_file = podcaster_config['history_file']
        posted_links = set()
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                posted_links = set(line.strip() for line in f)
        except FileNotFoundError:
            print(f"  History file '{history_file}' not found. Will create it.")

        try:
            scraper_type = podcaster_config['scraper_type']
            success = False
            unique_id = None 
            if scraper_type == 'philosophybites_web':
                all_new_episodes = []
                # 1. Aggregate all new episodes from all index pages
                for index_url in podcaster_config['index_url']:
                    episodes_on_page = scrape_philosophybites_index_page(index_url)
                    for episode in episodes_on_page:
                        # Use the episode URL as the unique ID
                        if episode['url'] not in posted_links:
                            all_new_episodes.append(episode)
                
                # De-duplicate the list
                unique_episodes = {ep['url']: ep for ep in all_new_episodes}.values()
                
                if not unique_episodes:
                    print("  No new episodes found across all index pages.")
                    continue

                # 2. Pick one randomly to process
                print(f"  Found {len(unique_episodes)} unique new episodes. Picking one randomly.")
                selected_episode = random.choice(list(unique_episodes))
                unique_id = selected_episode['url']
                episode_title = selected_episode['title']

                print(f"  Selected to process: '{episode_title}'")

                # --- REVISED LOGIC ---
                # 3. Scrape the content from the selected episode's page
                page_data = scrape_philosophybites_episode_page(unique_id)
                transcript_text = page_data.get('transcript')
                mp3_url = page_data.get('mp3_url')

                if not transcript_text:
                    print("  Failed to scrape transcript content. Aborting.")
                    continue
                
                # 4. Analyze and post
                ai_data = get_ai_podcast_analysis(transcript_text)
                if not ai_data:
                    print("  Failed to get AI analysis. Aborting.")
                    continue

                # Pass the mp3_url to the formatter
                message = format_podcast_telegram_message(ai_data, episode_title, None, podcaster_config, mp3_url=mp3_url)
                success = send_simple_podcast_to_telegram(message)
            # --- NEW LOGIC FOR PHILOSOPHIZE THIS! WEB SCRAPING ---
            elif scraper_type == 'philosophizethis_web':
                # 1. Scrape the index page to get the URL of the latest transcript
                latest_transcript_url = scrape_philosophizethis_index_page(podcaster_config['index_url'])
                
                if not latest_transcript_url:
                    print("  Could not find latest transcript URL. Skipping.")
                    continue
                
                unique_id = latest_transcript_url
                if unique_id in posted_links:
                    print(f"  Latest transcript '{unique_id}' has already been posted.")
                    continue
                
                print(f"  Found new transcript to process: {unique_id}")

                # 2. Scrape the transcript page for its content
                transcript_text = scrape_philosophizethis_transcript_page(unique_id)
                if not transcript_text:
                    print("  Failed to scrape transcript content. Aborting.")
                    continue

                # 3. Get AI analysis (reusing the Lex Fridman prompt is a good start)
                # We need a title, so we can try to extract it from the URL or text
                episode_title = "Philosophize This! - " + unique_id.split('/')[-1].replace('-transcript', '').replace('-', ' ').title()
                ai_data = get_ai_podcast_analysis(transcript_text)
                if not ai_data:
                    print("  Failed to get AI analysis. Aborting.")
                    continue

                # 4. Format and send the message (reusing the Lex formatter is suitable)
                # This podcast is solo, so we don't need pub_date from RSS
                message = format_podcast_telegram_message(ai_data, episode_title, None, podcaster_config)
                # Since there's no audio/video link, we send it as a simple text post.
                success = send_simple_podcast_to_telegram(message)

            # --- NEW LOGIC PATH FOR MULTI-FEED RANDOM CHOICE ---
            elif scraper_type == 'multi_rss_random':
                all_new_episodes = []
                # 1. Aggregate all new episodes from all feeds in the group
                for feed_url in podcaster_config['feed_url']:
                    print(f"  Fetching feed: {feed_url}")
                    feed = feedparser.parse(feed_url)
                    for episode in feed.entries:
                        unique_id = episode.get('link')
                        if episode.get('enclosures'):
                            unique_id = episode.enclosures[0].get('href', unique_id)
                        
                        if unique_id not in posted_links:
                            all_new_episodes.append(episode)
                
                # 2. If new episodes exist, pick one randomly and process it
                if not all_new_episodes:
                    print("  No new episodes found across all feeds in this group.")
                    continue
                
                print(f"  Found {len(all_new_episodes)} new episodes. Picking one randomly.")
                selected_episode = random.choice(all_new_episodes)
                episode_title = selected_episode.title
                pub_date = selected_episode.get('published')
                
                print(f"  Selected to process: '{episode_title}'")

                # 3. Process the selected episode using the same logic as podscribe_rss
                description = selected_episode.get('itunes_summary', selected_episode.get('description', ''))
                clean_description = BeautifulSoup(description, 'html.parser').get_text(separator=' ', strip=True)
                mp3_url = selected_episode.enclosures[0].get('href') if selected_episode.get('enclosures') else None

                if not clean_description or not mp3_url:
                    print("  Selected episode is missing description or MP3 URL. Aborting.")
                    continue
                
                ai_data = get_ai_rss_podcast_analysis(episode_title, clean_description)
                if not ai_data:
                    print("  Failed to get AI analysis. Aborting.")
                    continue

                message = format_rss_podcast_telegram_message(ai_data, episode_title, pub_date, mp3_url, podcaster_config)
                success = send_simple_podcast_to_telegram(message)
                # If successful, we need to update the unique_id to the one we just posted
                unique_id = selected_episode.get('link')
                if selected_episode.get('enclosures'):
                    unique_id = selected_episode.enclosures[0].get('href', unique_id)

            # --- LOGIC FOR SINGLE-LATEST RSS (Huberman) ---
            elif scraper_type == 'podscribe_rss':
                feed = feedparser.parse(podcaster_config['feed_url'][0]) # Get the first (and only) url
                if not feed.entries:
                    print("  Podcast feed is empty. Skipping.")
                    continue
                latest_episode = feed.entries[0]
                unique_id = latest_episode.get('link')
                if latest_episode.get('enclosures'):
                    unique_id = latest_episode.enclosures[0].get('href', unique_id)
                if unique_id in posted_links:
                    print(f"  Latest episode '{latest_episode.title}' already posted.")
                    continue
                # (The rest of the processing logic is the same as the random one, so we just call that)
                print(f"  Found new episode to process: {latest_episode.title}")
                description = latest_episode.get('itunes_summary', latest_episode.get('description', ''))
                clean_description = BeautifulSoup(description, 'html.parser').get_text(separator=' ', strip=True)
                mp3_url = latest_episode.enclosures[0].get('href') if latest_episode.get('enclosures') else None
                pub_date = latest_episode.get('published')
                ai_data = get_ai_rss_podcast_analysis(latest_episode.title, clean_description)
                if ai_data and mp3_url:
                    message = format_rss_podcast_telegram_message(ai_data, latest_episode.title, pub_date, mp3_url, podcaster_config)
                    success = send_simple_podcast_to_telegram(message)

            # --- LOGIC FOR WEB SCRAPING (Lex Fridman) ---
            elif scraper_type == 'lexfridman':
                feed = feedparser.parse(podcaster_config['feed_url'][0])
                if not feed.entries:
                    print("  Podcast feed is empty. Skipping.")
                    continue
                latest_episode = feed.entries[0]
                unique_id = latest_episode.link
                if unique_id in posted_links:
                    print(f"  Latest episode '{latest_episode.title}' already posted.")
                    continue
                # (Lex Fridman's custom scraping logic)
                print(f"  Found new episode to process: {latest_episode.title}")
                page_data = scrape_lexfridman_episode_page(latest_episode.link)
                if page_data and page_data.get('transcript_url'):
                    transcript_text = scrape_lexfridman_transcript_page(page_data['transcript_url'])
                    if not page_data.get('youtube_url') or not transcript_text:
                        print("  Failed to get essential data. Aborting.")
                        continue
                    ai_data = get_ai_podcast_analysis(transcript_text)
                    if not ai_data:
                        print("  Failed to get AI analysis. Aborting.")
                        continue
                    pub_date = latest_episode.get('published')
                    analysis_message = format_podcast_telegram_message(ai_data, latest_episode.title, pub_date, podcaster_config)
                    youtube_url = page_data['youtube_url']
                    success = send_podcast_to_telegram(youtube_url, analysis_message, latest_episode.title)
                else:
                    print("  Lex Fridman scraper failed to find page data.")
            else:
                print(f"  ERROR: Unknown scraper_type '{scraper_type}'.")

            # --- Unified history saving for any successful post ---
            if success:
                posted_links.add(unique_id)
                with open(history_file, 'w', encoding='utf-8') as f:
                    for link in sorted(posted_links):
                        f.write(link + '\n')
                print(f"  Updated history file: {history_file}")

        except Exception as e:
            print(f"!! FATAL ERROR processing podcast group '{name}': {e}")

if __name__ == "__main__":
    # Final check for API keys before running
    if AI_PROVIDER == 'gemini' and not GEMINI_API_KEY:
        print("FATAL ERROR: AI_PROVIDER is 'gemini' but GEMINI_API_KEY is not set.")
    elif AI_PROVIDER == 'groq' and not GROQ_API_KEY:
         print("FATAL ERROR: AI_PROVIDER is 'groq' but GROQ_API_KEY is not set.")
    else:
        # Run the new generalized podcast processor
        process_all_podcasts()
