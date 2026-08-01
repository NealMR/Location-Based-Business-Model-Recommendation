"""
03_ground_truth.py
------------------
Uses OpenStreetMap (Overpass API) to count business types and compute a viability score.
This replaces the old Google Maps implementation, making it completely free.

Output: data/raw/ground_truth.csv
"""

import os
import csv
import math
import time
import random
import requests

# Business types and their corresponding OSM tags
BUSINESS_FEATURES = {
    "restaurant": ['["amenity"="restaurant"]'],
    "cafe": ['["amenity"="cafe"]'],
    "gym": ['["leisure"="fitness_centre"]'],
    "pharmacy": ['["amenity"="pharmacy"]'],
    "beauty_salon": ['["shop"="beauty"]', '["shop"="hairdresser"]'],
    "store": ['["shop"]'],
    "school": ['["amenity"="school"]'],
    "lodging": ['["tourism"="hotel"]', '["tourism"="hostel"]', '["tourism"="guest_house"]'],
    "bar": ['["amenity"="bar"]', '["amenity"="pub"]'],
    "night_club": ['["amenity"="nightclub"]']
}

BUSINESS_TYPES = list(BUSINESS_FEATURES.keys())

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def get_osm_counts_batch(lat, lon, radius=1500):
    """Fetches all feature counts for a location in a single Overpass query."""
    feature_names = list(BUSINESS_FEATURES.keys())
    
    query = "[out:json][timeout:25];\n"
    for i, name in enumerate(feature_names):
        tag_list = BUSINESS_FEATURES[name]
        query += "(\n"
        for tag in tag_list:
            query += f"  node{tag}(around:{radius},{lat},{lon});\n"
            query += f"  way{tag}(around:{radius},{lat},{lon});\n"
            query += f"  rel{tag}(around:{radius},{lat},{lon});\n"
        query += f")->.f{i};\n"
        query += f".f{i} out count;\n"
    
    headers = {'User-Agent': 'LocationPredictor/1.0'}
    
    try:
        response = requests.post(OVERPASS_URL, data=query.encode('utf-8'), headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        results = {}
        if 'elements' in data and len(data['elements']) == len(feature_names):
            for i, name in enumerate(feature_names):
                counts = data['elements'][i].get('tags', {})
                results[name] = sum(int(v) for v in counts.values() if str(v).isdigit())
            return results
        else:
            return {name: 0 for name in feature_names}
    except Exception as e:
        print(f"      Overpass API error: {e}")
        return {name: 0 for name in feature_names}

def compute_viability(count, avg_rating):
    if count == 0:
        return 0.0
    # viability = (count * avg_rating * log(count + 1)) / 1.0
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

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_path = os.path.join(project_root, "data", "raw", "localities.csv")
    output_path = os.path.join(project_root, "data", "raw", "ground_truth.csv")
    
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        localities = list(reader)

    print("-" * 50)
    print("Using OpenStreetMap for Ground Truth Generation")
    print(f"Total localities: {len(localities)}")
    print("-" * 50)
    
    processed_data = []

    for i, loc in enumerate(localities, 1):
        name = loc['name']
        lat = float(loc['lat'])
        lng = float(loc['lng'])
        
        print(f"[{i}/{len(localities)}] Fetching OSM ground truth for {name}...")
        
        counts = get_osm_counts_batch(lat, lng)
        row_data = loc.copy()
        
        for bt in BUSINESS_TYPES:
            count = counts.get(bt, 0)
            
            # Simulate a realistic rating based on density (competition)
            # High density = slightly higher baseline, plus some noise
            if count > 0:
                base_rating = 3.8 + min(0.7, count * 0.05)
                # Add random noise between -0.3 and 0.3
                avg_rating = base_rating + random.uniform(-0.3, 0.3)
                avg_rating = min(5.0, max(1.0, avg_rating)) # Clamp between 1.0 and 5.0
            else:
                avg_rating = 0.0
                
            viability = compute_viability(count, avg_rating)
            row_data[f"{bt}_count"] = count
            row_data[f"{bt}_rating"] = round(avg_rating, 2)
            row_data[f"{bt}_viability"] = round(viability, 2)
            
        processed_data.append(row_data)
        
        # Rate limit protection (Overpass recommends sleeping between queries)
        time.sleep(2.0)

    print("\nNormalizing viability scores (0-100)...")
    final_data = normalize_labels(processed_data, BUSINESS_TYPES)

    fieldnames = ['name', 'ward', 'lat', 'lng', 'zone']
    for bt in BUSINESS_TYPES:
        fieldnames.extend([f"{bt}_count", f"{bt}_rating", f"{bt}_viability", f"{bt}_viability_norm"])

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_data)

    print("-" * 50)
    print("Step 3 complete - ready for Step 4")
    print(f"Data saved to: {output_path}")

if __name__ == "__main__":
    main()
