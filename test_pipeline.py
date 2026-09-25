import sys
import os
import time

# Ensure we can import from the scripts folder
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
from maps_scraper import scrape_google_data
from llm_processor import generate_business_strategy_stream
from geopy.geocoders import Nominatim

def run_full_test():
    print("========================================")
    print("INITIATING END-TO-END PIPELINE TEST")
    print("========================================\n")

    # Step 1: Geopy Test
    print("[1/3] Testing Geopy Reverse Geocoding...")
    try:
        geolocator = Nominatim(user_agent="ai_location_app")
        loc = geolocator.reverse("19.0596, 72.8295") # Bandra West coordinates
        location_name = loc.address if loc else "Bandra West, Mumbai"
        print(f"[Success] Resolved Address: {location_name}\n")
    except Exception as e:
        print(f"[Failed] Geopy failed: {e}")
        location_name = "Bandra West, Mumbai"

    # Step 2: Playwright Scraper Test
    print(f"[2/3] Testing Playwright Scraper for: {location_name[:30]}...")
    try:
        scraped_data = scrape_google_data("Bandra West, Mumbai")
        infra = scraped_data.get('infrastructure', {})
        comps = scraped_data.get('competitors', [])
        
        print(f"[Success] Scraper returned data:")
        print(f"   - Infrastructure: Schools({infra.get('schools')}), Colleges({infra.get('colleges')})")
        print(f"   - Competitors Feed Extracted: {len(comps)} elements.\n")
    except Exception as e:
        print(f"[Failed] Scraper failed: {e}")
        sys.exit(1)

    # Step 3: Local LLM Test (Ollama)
    print("[3/3] Testing Local LLM (Streaming from Ollama 'phi3')...")
    infra_str = str(infra)
    comp_str = "\n".join(comps)
    rev_str = "Customer sentiment: Needs better ambiance and wifi."

    try:
        print("--- AI RESPONSE START ---")
        for chunk in generate_business_strategy_stream(location_name, infra_str, comp_str, rev_str, model_name='phi3'):
            print(chunk, end='', flush=True)
            time.sleep(0.02) # Slight delay to visualize the stream in terminal
        print("\n--- AI RESPONSE END ---\n")
        print("[Success] LLM generated the strategy.\n")
    except Exception as e:
        print(f"\n[Failed] Local LLM Connection Failed: {e}")
        print("CRITICAL FIX: Please ensure the 'Ollama' application is running on your computer.")
        print("If Ollama is running, ensure you have pulled the model by typing: ollama run phi3")
        sys.exit(1)

    print("========================================")
    print("ALL TESTS PASSED SUCCESSFULLY.")
    print("========================================")

if __name__ == "__main__":
    run_full_test()
