"""
03_ground_truth.py
------------------
Uses Google Places API to count business types and compute a viability score.
Falls back to OpenStreetMap Overpass API if Google API key is unavailable.
Last resort: deterministic synthetic data (seed-locked).

Output: data/raw/ground_truth.csv
"""

import os
import csv
import math
import time
import random
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None

try:
    import googlemaps
except ImportError:
    googlemaps = None

# Deterministic seed for reproducibility
random.seed(42)

# Business types (shared) — names double as Google Places API types
from common import BUSINESS_TYPES

# OSM tag mapping for each business type (used for Overpass fallback)
OSM_BUSINESS_TAGS = {
    "restaurant":   ['["amenity"="restaurant"]'],
    "cafe":         ['["amenity"="cafe"]'],
    "gym":          ['["leisure"="fitness_centre"]', '["leisure"="sports_centre"]'],
    "pharmacy":     ['["amenity"="pharmacy"]'],
    "beauty_salon": ['["shop"="beauty"]', '["shop"="hairdresser"]'],
    "store":        ['["shop"="supermarket"]', '["shop"="convenience"]', '["shop"="department_store"]'],
    "school":       ['["amenity"="school"]'],
    "lodging":      ['["tourism"="hotel"]', '["tourism"="guest_house"]', '["tourism"="hostel"]'],
    "bar":          ['["amenity"="bar"]', '["amenity"="pub"]'],
    "night_club":   ['["amenity"="nightclub"]'],
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SEARCH_RADIUS = 800  # metres


def compute_viability(count, avg_rating):
    """Viability = count * avg_rating * log(count + 1)."""
    if count == 0:
        return 0.0
    return (count * avg_rating * math.log(count + 1)) / 1.0


def normalize_labels(data_rows, business_types):
    """
    Normalizes viability scores to a 0-100 scale per business type
    across all localities.
    """
    max_viability = {bt: 0.0 for bt in business_types}
    
    for row in data_rows:
        for bt in business_types:
            val = float(row.get(f"{bt}_viability", 0.0))
            if val > max_viability[bt]:
                max_viability[bt] = val
                
    for row in data_rows:
        for bt in business_types:
            val = float(row.get(f"{bt}_viability", 0.0))
            if max_viability[bt] > 0:
                normalized = (val / max_viability[bt]) * 100.0
            else:
                normalized = 0.0
            row[f"{bt}_viability_norm"] = round(normalized, 1)
            
    return data_rows


def get_osm_ground_truth(lat, lon, business_type):
    """
    Queries the Overpass API to count real businesses of a given type
    within SEARCH_RADIUS metres of (lat, lon).
    Returns (count, estimated_rating).
    """
    if requests is None:
        return 0, 0.0

    tags = OSM_BUSINESS_TAGS.get(business_type, [])
    if not tags:
        return 0, 0.0

    # Build a single union query for all tags of this business type
    query = f"[out:json][timeout:25];\n(\n"
    for tag in tags:
        query += f"  node{tag}(around:{SEARCH_RADIUS},{lat},{lon});\n"
        query += f"  way{tag}(around:{SEARCH_RADIUS},{lat},{lon});\n"
    query += ");\nout count;\n"

    headers = {'User-Agent': 'LocationPredictor/1.0'}

    try:
        response = requests.post(OVERPASS_URL, data=query.encode('utf-8'),
                                 headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        count = 0
        if 'elements' in data and len(data['elements']) > 0:
            counts_tag = data['elements'][0].get('tags', {})
            count = sum(int(v) for v in counts_tag.values()
                        if str(v).isdigit())

        # OSM doesn't have ratings; estimate from count density
        # Higher count -> likely more competitive -> slightly higher avg quality
        if count > 0:
            avg_rating = min(3.5 + 0.05 * count, 4.8)
        else:
            avg_rating = 0.0

        return count, round(avg_rating, 1)
    except Exception as e:
        logger.debug(f"OSM query failed for {business_type}: {e}")
        return 0, 0.0


def get_dummy_data(zone, bt):
    """Generates deterministic synthetic data (seed-locked) as last resort."""
    multiplier = 1.0
    if zone in ["South Mumbai", "Western Suburbs"]:
        multiplier = 1.5
    elif zone in ["Navi Mumbai", "Thane"]:
        multiplier = 0.7
        
    ranges = {
        "restaurant": (5, 40), "cafe": (2, 20), "gym": (1, 10),
        "pharmacy": (5, 25), "beauty_salon": (3, 15), "store": (10, 60),
        "school": (1, 8), "lodging": (0, 10), "bar": (0, 8), "night_club": (0, 3)
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
        logger.error(f"Input file not found at {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        localities = list(reader)

    # Determine data source: Google Maps > OSM Overpass > Synthetic
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    mode = "synthetic"
    gmaps = None
    
    if api_key and googlemaps is not None:
        try:
            gmaps = googlemaps.Client(key=api_key)
            mode = "google"
            logger.info("Google Maps API key detected. Fetching live ground truth data...")
        except Exception as e:
            logger.warning(f"Error initializing Google Maps Client: {e}")
    
    if mode != "google" and requests is not None:
        mode = "osm"
        logger.info("Using OpenStreetMap Overpass API for real ground truth data...")
    
    if mode == "synthetic":
        logger.warning("No API available. Using deterministic synthetic data (seed=42).")
    
    print("-" * 50)
    
    processed_data = []

    for i, loc in enumerate(localities, 1):
        name = loc['name']
        lat = float(loc['lat'])
        lng = float(loc['lng'])
        zone = loc['zone']
        
        print(f"[{i}/{len(localities)}] Processing ground truth for {name}... ({mode})")
        
        row_data = loc.copy()
        
        for bt in BUSINESS_TYPES:
            count = 0
            avg_rating = 0.0
            
            if mode == "synthetic":
                count, avg_rating = get_dummy_data(zone, bt)
            elif mode == "osm":
                count, avg_rating = get_osm_ground_truth(lat, lng, bt)
            else:
                # Google Maps mode
                total_rating = 0.0
                rated_places = 0
                
                try:
                    result = gmaps.places_nearby(location=(lat, lng), radius=SEARCH_RADIUS, type=bt)
                    places = result.get('results', [])
                    count += len(places)
                    
                    for p in places:
                        if 'rating' in p:
                            total_rating += p['rating']
                            rated_places += 1
                            
                    while 'next_page_token' in result:
                        time.sleep(2)
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
                        avg_rating = 3.5 if count > 0 else 0.0
                        
                except Exception as e:
                    logger.warning(f"  Error fetching {bt} for {name}: {e}")
            
            viability = compute_viability(count, avg_rating)
            row_data[f"{bt}_count"] = count
            row_data[f"{bt}_rating"] = round(avg_rating, 2)
            row_data[f"{bt}_viability"] = round(viability, 2)
            
        processed_data.append(row_data)
        
        # Rate-limit for API modes
        if mode == "google":
            time.sleep(0.5)
        elif mode == "osm":
            time.sleep(1.5)  # Be polite to Overpass

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
    print(f"[OK] Step 3 complete - ready for Step 4 (source: {mode})")
    print(f"Data saved to: {output_path}")

if __name__ == "__main__":
    main()

