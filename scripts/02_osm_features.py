import csv
import os
import time
import requests

FEATURES = {
    'railway_stations': (1000, ['["railway"="station"]', '["railway"="halt"]']),
    'metro_stations': (1000, ['["station"="subway"]', '["railway"="subway"]']),
    'bus_stops': (500, ['["highway"="bus_stop"]', '["public_transport"="platform"]']),
    'colleges': (1500, ['["amenity"="college"]', '["amenity"="university"]']),
    'schools': (1000, ['["amenity"="school"]']),
    'offices': (1000, ['["office"]']),
    'malls': (2000, ['["shop"="mall"]', '["shop"="department_store"]']),
    'hospitals': (1000, ['["amenity"="hospital"]', '["amenity"="clinic"]']),
    'parking_lots': (500, ['["amenity"="parking"]']),
    'tourist_spots': (2000, ['["tourism"]', '["historic"]']),
    'existing_cafes': (500, ['["amenity"="cafe"]']),
    'existing_restaurants': (500, ['["amenity"="restaurant"]']),
    'existing_gyms': (1000, ['["leisure"="fitness_centre"]'])
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def get_osm_counts_batch(lat, lon):
    """Fetches all feature counts for a location in a single Overpass query."""
    feature_names = list(FEATURES.keys())
    
    query = "[out:json][timeout:25];\n"
    for i, name in enumerate(feature_names):
        radius, tag_list = FEATURES[name]
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
        # Elements array has one element per 'out count'
        if 'elements' in data and len(data['elements']) == len(feature_names):
            for i, name in enumerate(feature_names):
                counts = data['elements'][i].get('tags', {})
                results[name] = sum(int(v) for v in counts.values() if v.isdigit() or isinstance(v, int))
            return results
        else:
            print(f"  WARNING: unexpected Overpass response shape; writing zeros for this locality")
            return {name: 0 for name in feature_names}
    except Exception as e:
        print(f"  WARNING: Overpass query failed ({e}); writing zeros for this locality")
        return {name: 0 for name in feature_names}

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_path = os.path.join(project_root, "data", "raw", "localities.csv")
    output_path = os.path.join(project_root, "data", "raw", "osm_features.csv")
    
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        localities = list(reader)

    print(f"Loaded {len(localities)} localities. Starting Fast OSM extraction...")
    print(f"This will take approximately {len(localities) * 2 / 60:.1f} minutes.")
    print("-" * 50)

    fieldnames = ['name', 'ward', 'lat', 'lng', 'zone'] + list(FEATURES.keys())
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, loc in enumerate(localities, 1):
            name = loc['name']
            lat = float(loc['lat'])
            lon = float(loc['lng'])
            
            print(f"[{i}/{len(localities)}] Processing {name}...")
            
            counts = get_osm_counts_batch(lat, lon)
            row = loc.copy()
            row.update(counts)
            
            writer.writerow(row)
            f.flush()
            
            time.sleep(2.0) # Rate limit protection

    print("-" * 50)
    print(f"[OK] Step 2 complete - ready for Step 3")
    print(f"Data saved to: {output_path}")

if __name__ == "__main__":
    main()
