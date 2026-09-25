import time
import sys
from playwright.sync_api import sync_playwright

def scrape_google_data(location_address, radius="3"):
    """
    Scrapes infrastructure and competitor data from Google Maps based on a location string and search radius.
    """
    infrastructure = {"schools": 0, "colleges": 0, "transit": 0}
    competitors = []
    
    print(f"Starting Playwright scrape for: {location_address} (Radius: {radius}km)")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            )
            context.set_default_timeout(15000) # 15s timeout to prevent freezing
            page = context.new_page()
            
            # 1. Scrape Infrastructure for Locality Profiling (Quantitative + Qualitative)
            infrastructure_details = {}
            for infra in ["Schools", "Colleges", "Hospitals", "Corporate Offices", "Apartment Complexes"]:
                print(f"Searching for {infra} within {radius}km...")
                infra_key = infra.lower().replace(" ", "_")
                try:
                    page.goto(f"https://www.google.com/maps/search/{infra}+within+{radius}km+of+{location_address}")
                    # PERFORMANCE FIX: Wait for actual DOM element instead of hardcoded 3-second sleep
                    try:
                        page.wait_for_selector('div[role="article"]', timeout=3000)
                    except:
                        page.wait_for_timeout(1000) # fallback
                    
                    accept_btn = page.query_selector('button:has-text("Accept all")')
                    if accept_btn: accept_btn.click()
                    
                    elements = page.query_selector_all('div[role="article"]')
                    infrastructure[infra_key] = len(elements)
                    
                    # Extract qualitative context (e.g. "Medical College" vs "Arts College")
                    details = []
                    for el in elements[:5]:
                        text_lines = el.inner_text().strip().split('\n')
                        if text_lines:
                            # Join the first 2 lines (usually Name + Category/Rating)
                            clean_text = " - ".join([line for line in text_lines[:2] if line.strip()])
                            details.append(clean_text)
                    infrastructure_details[infra_key] = details
                    
                except Exception as e:
                    print(f"Timeout/Error on {infra}: {e}")
                    infrastructure[infra_key] = 0
                    infrastructure_details[infra_key] = []
                
            # 2. Scrape Competitors & Ratings
            print(f"Searching for local businesses and reviews within {radius}km...")
            comp_count = 0
            try:
                page.goto(f"https://www.google.com/maps/search/local+businesses+and+popular+places+within+{radius}km+of+{location_address}")
                try:
                    page.wait_for_selector('div[role="feed"]', timeout=6000)
                except:
                    page.wait_for_timeout(2000)
                
                # Scroll down aggressively to load deep market results
                for _ in range(8):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(800)
                    
                # Accurately count individual businesses in DOM before text extraction
                # ROBUST FIX: Use multiple fallback selectors to survive Google A/B testing
                HEADLINE_SELECTORS = ['.fontHeadlineSmall', '[data-attrid="title"]', 'h3.section-result-title', '[aria-level="3"]']
                headlines = []
                for sel in HEADLINE_SELECTORS:
                    headlines = page.query_selector_all(sel)
                    if headlines: break
                    
                comp_count = len(headlines) if headlines else 0
                
                # Target the main sidebar that holds results
                feed_element = page.query_selector('div[role="feed"]') or page.query_selector('div[aria-label*="Results"]')
                if feed_element:
                    raw_text = feed_element.inner_text()
                    
                    # FINE-TUNING: Clean up huge empty spaces and useless UI buttons
                    ignore_phrases = ["Reserve a table", "Order online", "Share", "Send to your phone", "Directions", "Website", "Save", "You're seeing a limited view", "Results"]
                    cleaned_lines = []
                    for line in raw_text.split('\n'):
                        line = line.strip()
                        if line and line not in ignore_phrases and len(line) > 2:
                            cleaned_lines.append(line)
                            
                    cleaned_text = " | ".join(cleaned_lines)
                    competitors.append(cleaned_text[:8000]) # Increased to 8000 for deep context
                else:
                    # Fallback to grab any business-looking elements
                    for el in headlines:
                        competitors.append(el.inner_text())
                        
                # QUALITY FIX: Extract actual star ratings and review counts from the DOM
                star_elements = page.query_selector_all('span[aria-label*="stars"]')
                real_reviews = []
                for s in star_elements[:30]:
                    label = s.get_attribute('aria-label')
                    if label: real_reviews.append(label)
                    
            except Exception as e:
                print(f"Timeout/Error on Competitors: {e}")
                
            browser.close()
            
    except Exception as e:
        print(f"Extraction error: {e}")
        
    # Anti-Hallucination Fallback
    if len(competitors) == 0:
        competitors = ["ZERO COMPETITORS FOUND IN IMMEDIATE RADIUS. This is an untapped market."]
    
    # Send actual extracted ratings to the LLM
    if 'real_reviews' in locals() and len(real_reviews) > 0:
        reviews = ["Customer Sentiment Data:"] + real_reviews
    else:
        reviews = ["Customer Sentiment Data: No visible ratings found on map surface."]
        
    return {
        "infrastructure": infrastructure,
        "infrastructure_details": locals().get('infrastructure_details', {}),
        "competitors": competitors,
        "reviews": reviews,
        "competitor_count": comp_count
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "Andheri West, Mumbai"
        
    res = scrape_google_data(query)
    print("Scrape Complete:")
    print(res)
