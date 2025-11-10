import urllib.parse
import requests
import wikipedia
from wikipedia.exceptions import DisambiguationError,PageError
from bs4 import BeautifulSoup
import re

def summarize_text_for_search(text, llm):
    prompt = f"""
    You are a research assistant. Convert the following text into a short and clear Wikipedia search phrase.
    Only return the search phrase, no explanations.

    Text:
    {text}
    """

    response = llm.invoke(prompt)

    if hasattr(response, "content"):
        response_text = response.content
    elif isinstance(response, dict) and "content" in response:
        response_text = response["content"]
    else:
        response_text = str(response)

    return response_text.strip()

def clean_search_query(raw_text: str) -> str:
    if not raw_text:
        return ""
    
    text = re.sub(r"^(Sure, here is the search phrase:|Search phrase:|Here(?:'s| is) the (?:search )?phrase:)\s*", "", raw_text, flags=re.IGNORECASE)
    
    text = re.sub(r"[*_`]+", "", text)
    
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    if not lines:
        return ""
    
    return lines[0].strip()


def fetch_wikipedia_summary(raw_query: str, sentences: int = 10) -> str:
    query = clean_search_query(raw_query)
    if not query:
        print(f"⚠️ Empty query after cleaning: '{raw_query}'")
        return ""

    print(f"[Debug] Cleaned query: '{query}'")

    safe_title = query.replace(" ", "_")
    direct_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(safe_title)}"
    
    print(f"[Debug] Checking direct URL: {direct_url}")
    
    try:
        r = requests.get(direct_url, timeout=10)
        print(f"[Debug] Direct URL status code: {r.status_code}")
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            disambiguation = soup.find("div", {"id": "disambig"})
            
            if not disambiguation:
                try:
                    page = wikipedia.page(safe_title, auto_suggest=False)
                    print(f"[Debug] Found direct page: {page.title}")
                    return wikipedia.summary(page.title, sentences=sentences)
                except (DisambiguationError, PageError) as e:
                    print(f"[Debug] Direct page error: {e}")
                    pass
            else:
                print(f"[Debug] Direct page is a disambiguation page")
    except Exception as e:
        print(f"⚠️ Direct URL check failed: {e}")

    try:
        search_results = wikipedia.search(query)
        print(f"[Debug] Search results: {search_results}")
        
        if not search_results:
            return ""

        for result in search_results[:1]:
            try:
                page = wikipedia.page(result, auto_suggest=False)
                print(f"[Debug] Using search result: {page.title}")
                return wikipedia.summary(page.title, sentences=sentences)
            except (DisambiguationError, PageError) as e:
                print(f"[Debug] Search result error for '{result}': {e}")
                continue

        return ""
    except Exception as e:
        print(f"⚠️ Wikipedia search error: {e}")
        return ""

def fetch_wikipedia_full_text(query: str) -> str | None:

    safe_title = urllib.parse.quote(query.replace(" ", "_"))
    url = f"https://en.wikipedia.org/wiki/{safe_title}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        paragraphs = soup.select("div.mw-parser-output > p")
        text = "\n".join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
        return text.strip() if text else None
    except Exception as e:
        print(f"⚠️ fetch_wikipedia_full_text error: {e}")
        return None
    
def fetch_top_wikipedia_results(query: str, n: int = 3, sentences: int = 10):

    if not query or not isinstance(query, str) or query.strip().lower() in ['none', 'null', '']:
        print(f"[DEBUG] ⚠️ Invalid query: '{query}', using 'artillery' as fallback")
        query = "artillery"
    
    cleaned_query = query.strip()
    results = []
    
    print(f"[DEBUG] 🔍 Starting search for: '{cleaned_query}'")
    
    safe_title = cleaned_query.replace(" ", "_")
    direct_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(safe_title)}"
    print(f"[DEBUG] 🌐 Direct URL: {direct_url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        r = requests.get(direct_url, timeout=10, headers=headers)
        print(f"[DEBUG] 📊 Direct URL status: {r.status_code}")
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            
            disambig = (soup.find("table", {"id": "disambigbox"}) or 
                        soup.find("table", {"class": "metadata plainlinks ambox ambox-content ambox-disambiguation"}) or
                        "disambiguation" in soup.get_text().lower() or
                        "may refer to:" in soup.get_text())
            
            if disambig:
                print(f"[DEBUG] ✅ Direct page is a disambiguation page")
                disambig_content = extract_disambiguation_content(soup, cleaned_query, n)
                results.append({
                    "title": f"{cleaned_query} (Disambiguation)",
                    "content": disambig_content,
                    "source_url": direct_url,
                    "is_disambiguation": True
                })
                print(f"[DEBUG] ✅ Disambiguation page processed")
                return results
            else:
                try:
                    page = wikipedia.page(safe_title)
                    summary = wikipedia.summary(page.title, sentences=sentences)
                    results.append({
                        "title": page.title,
                        "content": summary,
                        "source_url": page.url,
                        "is_disambiguation": False
                    })
                    print(f"[DEBUG] ✅ Direct page added: {page.title}")
                    return results
                except (DisambiguationError, PageError) as e:
                    print(f"[DEBUG] Direct page error: {e}")
                    manual_content = extract_manual_content(soup, sentences)
                    results.append({
                        "title": cleaned_query,
                        "content": manual_content,
                        "source_url": direct_url,
                        "is_disambiguation": False
                    })
                    print(f"[DEBUG] ✅ Manual content extracted")
                    return results

    except Exception as e:
        print(f"[DEBUG] ❌ Direct URL check failed: {e}")

    try:
        print(f"[DEBUG] Falling back to search for: '{cleaned_query}'")
        search_results = wikipedia.search(cleaned_query, results=n*2)
        print(f"[DEBUG] Search results: {search_results}")
        
        if not search_results:
            print(f"[DEBUG] No search results, trying manual extraction from direct URL")
            manual_results = manual_extract_from_url(direct_url, cleaned_query, sentences)
            if manual_results:
                return manual_results
            else:
                return get_fallback_content(cleaned_query)
        
        valid_results = [res for res in search_results if '(disambiguation)' not in res.lower()]
        for res in valid_results[:n]:
            try:
                page = wikipedia.page(res, auto_suggest=False)
                summary = wikipedia.summary(page.title, sentences=sentences)
                results.append({
                    "title": page.title,
                    "content": summary,
                    "source_url": page.url,
                    "is_disambiguation": False
                })
                print(f"[DEBUG] Search result added: {page.title}")
            except DisambiguationError as e:
                disambig_content = create_simple_disambiguation_content(cleaned_query, e.options[:8])
                results.append({
                    "title": f"{res} (Disambiguation)",
                    "content": disambig_content,
                    "source_url": f"https://en.wikipedia.org/wiki/{res.replace(' ', '_')}",
                    "is_disambiguation": True
                })
                print(f"[DEBUG] Disambiguation result added: {res}")
            except Exception as e:
                print(f"[DEBUG] Error with result {res}: {e}")
                continue
                
        print(f"[DEBUG] 📦 Final results count: {len(results)}")
        return results
        
    except Exception as e:
        print(f"[DEBUG] Wikipedia fetch error: {e}")
    
    print(f"[DEBUG] All methods failed, returning fallback content")
    return get_fallback_content(cleaned_query)

def extract_manual_content(soup: BeautifulSoup, sentences: int = 10) -> str:
    content_lines = []
    
    content_div = soup.find('div', {'class': 'mw-parser-output'})
    if content_div:
        paragraphs = content_div.find_all(['p', 'h1', 'h2', 'h3'], limit=sentences*2)
        
        for element in paragraphs:
            if element.name == 'p':
                text = element.get_text().strip()
                if text and len(text) > 50:
                    content_lines.append(text)
            elif element.name.startswith('h'):
                text = element.get_text().strip()
                if text:
                    content_lines.append(f"\n{text}\n")
            
            if len(content_lines) >= sentences:
                break
    
    if not content_lines:
        first_p = content_div.find('p') if content_div else None
        if first_p:
            content_lines.append(first_p.get_text().strip())
    
    if not content_lines:
        body_text = soup.get_text()
        lines = [line.strip() for line in body_text.split('\n') if line.strip()]
        content_lines = lines[:sentences]
    
    return '\n'.join(content_lines[:sentences])

def manual_extract_from_url(url: str, query: str, sentences: int = 10):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        r = requests.get(url, timeout=10, headers=headers)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            content = extract_manual_content(soup, sentences)
            return [{
                "title": query,
                "content": content,
                "source_url": url,
                "is_disambiguation": False
            }]
    except Exception as e:
        print(f"[DEBUG] ❌ Manual extraction failed: {e}")
    
    return None

def get_fallback_content(query: str):
    fallback_content = f"""Wikipedia content for '{query}' is currently unavailable. 

This may be due to:
• Network connectivity issues
• Wikipedia API limitations  
• The page not existing

Please try:
1. Checking your internet connection
2. Using a different search term
3. Trying again later

In the meantime, you can visit Wikipedia directly: https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"""

    return [{
        "title": query,
        "content": fallback_content,
        "source_url": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
        "is_disambiguation": False
    }]

def extract_disambiguation_content(soup, query, n=8):
    content_lines = []
    
    options = []
    
    selectors = [
        "div.mw-parser-output > ul > li > a",
        "div.mw-parser-output > ul > li",
        "div.mw-parser-output > p > a",
        "div.mw-parser-output > p + ul li a"
    ]
    
    for selector in selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text().strip()
            href = element.get('href', '')
            title = element.get('title', '')
            
            if (text and len(text) > 2 and 
                not text.lower().endswith('(disambiguation)') and
                not 'disambiguation' in text.lower() and
                href.startswith('/wiki/') and
                'disambiguation' not in href.lower()):
                
                options.append(text)
                if len(options) >= n * 2:
                    break
        if options:
            break
    
    seen = set()
    unique_options = []
    for opt in options:
        if opt not in seen and len(unique_options) < n:
            seen.add(opt)
            unique_options.append(opt)
    
    if unique_options:
        content_lines.append(f"'{query}' may refer to:")
        for option in unique_options:
            content_lines.append(f"• {option}")
        content_lines.append("")
        content_lines.append("Please specify your query for more precise results.")
    else:
        first_para = soup.find('div', {'class': 'mw-parser-output'})
        if first_para:
            first_p = first_para.find('p')
            if first_p:
                text = first_p.get_text()[:500]
                if len(first_p.get_text()) > 500:
                    text += "..."
                content_lines.append(text)
        else:
            content_lines.append("This is a disambiguation page listing articles associated with the same title.")
    
    return "\n".join(content_lines)

def create_simple_disambiguation_content(query, options):
    content_lines = [f"'{query}' may refer to:"]
    
    for option in options[:8]:
        content_lines.append(f"• {option}")
    
    content_lines.append("")
    content_lines.append("Please specify your query for more precise results.")
    
    return "\n".join(content_lines)