"""
03_ground_truth.py
------------------
Uses Google Places API to count business types and compute a viability score.
If GOOGLE_MAPS_API_KEY environment variable is missing or fails, falls back 
to realistic dummy data.

Output: data/raw/ground_truth.csv
"""

import os
import csv
import math
import time
import random

try:
    import googlemaps
except ImportError:
    googlemaps = None

# Business types for Google Places API
BUSINESS_TYPES = [
    "restaurant", "cafe", "gym", "pharmacy", "beauty_salon", 
    "store", "school", "lodging", "bar", "night_club"
]

def compute_viability(count, avg_rating):
    if count == 0:
        return 0.0
    # viability = (count × avg_rating × log(count + 1)) / 1.0
    return (count * avg_rating * math.log(count + 1)) / 1.0

def normalize_labels(data_rows, business_types):
    """
    Normalizes viability scores to a 0-100 scale per business type
    across all localities.
    """
    # Find max viability for each business type
    max_viability = {bt: 0.0 for bt in business_types}
    
    for row in data_rows:
        for bt in business_types:
            val = float(row.get(f"{bt}_viability", 0.0))
            if val > max_viability[bt]:
                max_viability[bt] = val
                
    # Normalize
    for row in data_rows:
        for bt in business_types:
            val = float(row.get(f"{bt}_viability", 0.0))
            if max_viability[bt] > 0:
                normalized = (val / max_viability[bt]) * 100.0
            else:
                normalized = 0.0
            row[f"{bt}_viability_norm"] = round(normalized, 1)
            
    return data_rows

def get_dummy_data(zone, bt):
    """Generates realistic dummy data if API key is missing."""
    # Base multiplier depending on zone
    multiplier = 1.0
    if zone in ["South Mumbai", "Western Suburbs"]:
        multiplier = 1.5
    elif zone in ["Navi Mumbai", "Thane"]:
        multiplier = 0.7
        
    # Base count ranges per business type
    ranges = {
        "restaurant": (5, 40),
        "cafe": (2, 20),
        "gym": (1, 10),
        "pharmacy": (5, 25),
        "beauty_salon": (3, 15),
        "store": (10, 60),
        "school": (1, 8),
        "lodging": (0, 10),
        "bar": (0, 8),
        "night_club": (0, 3)
    }
    
    min_c, max_c = ranges.get(bt, (1, 10))
    count = int(random.randint(min_c, max_c) * multiplier)
    
    avg_rating = round(random.uniform(3.5, 4.8), 1) if count > 0 else 0.0
    return count, avg_rating

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_path = os.path.join(project_root, "data", "raw", "localities.csv")
    output_path = os.path.join(project_root, "data", "raw", "ground_truth.csv")
    
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    # Read input localities
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        localities = list(reader)

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    use_dummy = False
    gmaps = None
    
    if not api_key:
        print("WARNING: GOOGLE_MAPS_API_KEY environment variable not set.")
        print("Falling back to dummy data generation to ensure pipeline continuity.")
        use_dummy = True
    elif googlemaps is None:
        print("WARNING: 'googlemaps' library not installed.")
        print("Falling back to dummy data generation.")
        use_dummy = True
    else:
        try:
            gmaps = googlemaps.Client(key=api_key)
            print("Google Maps API Key detected. Fetching live ground truth data...")
        except Exception as e:
            print(f"Error initializing Google Maps Client: {e}")
            print("Falling back to dummy data generation.")
            use_dummy = True

    print("-" * 50)
    
    processed_data = []

    for i, loc in enumerate(localities, 1):
        name = loc['name']
        lat = float(loc['lat'])
        lng = float(loc['lng'])
        zone = loc['zone']
        
        print(f"[{i}/{len(localities)}] Processing ground truth for {name}...")
        
        row_data = loc.copy()
        
        for bt in BUSINESS_TYPES:
            count = 0
            avg_rating = 0.0
            
            if use_dummy:
                count, avg_rating = get_dummy_data(zone, bt)
            else:
                total_rating = 0.0
                rated_places = 0
                
                try:
                    # Fetch up to 60 results via pagination
                    result = gmaps.places_nearby(location=(lat, lng), radius=800, type=bt)
                    places = result.get('results', [])
                    count += len(places)
                    
                    for p in places:
                        if 'rating' in p:
                            total_rating += p['rating']
                            rated_places += 1
                            
                    while 'next_page_token' in result:
                        time.sleep(2) # Required sleep for next_page_token to become valid
                        result = gmaps.places_nearby(page_token=result['next_page_token'])
                        places = result.get('results', [])
                        count += len(places)
                        for p in places:
                            if 'rating' in p:
                                total_rating += p['rating']
                                rated_places += 1
                                
                    if rated_places > 0:
                        avg_rating = total_rating / rated_places
                    else:
                        # Fallback sensible default if places exist but none have ratings
                        avg_rating = 3.5 if count > 0 else 0.0
                        
                except Exception as e:
                    print(f"  Error fetching {bt} for {name}: {e}")
                    # Keep count=0 on error
            
            viability = compute_viability(count, avg_rating)
            row_data[f"{bt}_count"] = count
            row_data[f"{bt}_rating"] = round(avg_rating, 2)
            row_data[f"{bt}_viability"] = round(viability, 2)
            
        processed_data.append(row_data)
        
        # Avoid hitting API rate limits too hard
        if not use_dummy:
            time.sleep(0.5)

    # Normalize labels across the dataset
    print("\nNormalizing viability scores (0-100)...")
    final_data = normalize_labels(processed_data, BUSINESS_TYPES)

    # Determine fieldnames
    fieldnames = ['name', 'ward', 'lat', 'lng', 'zone']
    for bt in BUSINESS_TYPES:
        fieldnames.extend([f"{bt}_count", f"{bt}_rating", f"{bt}_viability", f"{bt}_viability_norm"])

    # Save to CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_data)

    print("-" * 50)
     - ready for Step 4")
    print(f"Data saved to: {output_path}")

if __name__ == "__main__":
    main()
