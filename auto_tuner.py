import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
from maps_scraper import scrape_google_data
from llm_processor import generate_business_strategy_stream

# We will test 3 distinct locations to find and fix edge cases
locations = [
    "Connaught Place, New Delhi", # Highly dense urban area
    "Powai, Mumbai", # Suburban/Tech hub
    "Sangli Gymkhana" # Remote/Zero competitor test
]

for loc in locations:
    print(f"\n{'='*60}\nRunning test for: {loc}\n{'='*60}")
    
    # Scrape
    print("1. Scraping data...")
    data = scrape_google_data(loc)
    infra = data.get('infrastructure', {})
    comps = data.get('competitors', [])
    print(f"Found Infra: Schools({infra.get('schools')}), Colleges({infra.get('colleges')})")
    
    # Synthesize strings
    infra_str = f"Schools: {infra.get('schools', 0)}, Colleges: {infra.get('colleges', 0)}"
    comp_str = "\n".join(comps)
    rev_str = "\n".join(data.get('reviews', []))
    
    print("2. Generating AI Strategy...\n")
    print("--- REPORT START ---")
    try:
        for chunk in generate_business_strategy_stream(loc, infra_str, comp_str, rev_str, model_name='phi3'):
            print(chunk, end='', flush=True)
    except Exception as e:
        print(f"\n[ERROR] LLM Failed: {e}")
    print("\n--- REPORT END ---")
