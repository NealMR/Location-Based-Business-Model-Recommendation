"""
04_rent_data.py
---------------
Estimates commercial rent using Maharashtra Ready Reckoner 2024 rates.
Formula: monthly_rent_per_sqft = property_rate_per_sqft * 0.005
Interpolates missing localities using zone averages.
Output: data/raw/rent_data.csv
"""

import os
import csv

# Base Ready Reckoner Commercial Rates (property_rate_per_sqft) for known localities
SPECIFIC_RATES = {
    "Colaba": 65000, "Cuffe Parade": 68000, "Navy Nagar": 58000, "Churchgate": 70000,
    "Fort": 62000, "Ballard Estate": 55000, "Mandvi": 40000, "Masjid Bunder": 38000,
    "Crawford Market": 45000, "Marine Lines": 60000, "Charni Road": 52000, "Grant Road": 48000,
    "Girgaon": 50000, "Malabar Hill": 75000, "Pedder Road": 72000, "Breach Candy": 74000,
    "Tardeo": 55000, "Bhendi Bazaar": 35000, "Nagpada": 32000, "Dongri": 30000,
    "Mazgaon": 38000, "Reay Road": 30000, "Byculla": 42000, "Jacob Circle": 45000,
    "Worli": 65000, "Nariman Point": 85000, "Apollo Bunder": 70000,
    "Dadar (East)": 45000, "Dadar (West)": 48000, "Mahim": 42000, "Matunga": 46000,
    "Parel": 40000, "Lower Parel": 55000, "Lalbaug": 38000, "Sewri": 32000,
    "Cotton Green": 30000, "Wadala": 35000, "Sion": 34000, "Dharavi": 20000,
    "Chunabhatti": 28000, "Antop Hill": 26000, "Chembur": 32000, "Govandi": 22000,
    "Mankhurd": 18000, "Trombay": 18000, "Kurla (West)": 28000, "Kurla (East)": 26000,
    "Ghatkopar (West)": 30000, "Ghatkopar (East)": 32000, "Elphinstone Road": 45000,
    "Prabhadevi": 52000,
    "Bandra (West)": 60000, "Bandra (East)": 45000, "Santacruz (West)": 48000,
    "Santacruz (East)": 40000, "Vile Parle (West)": 50000, "Vile Parle (East)": 42000,
    "Khar (West)": 55000, "Juhu": 65000, "Andheri (West)": 45000, "Andheri (East)": 38000,
    "Jogeshwari (West)": 32000, "Jogeshwari (East)": 30000, "Goregaon (West)": 36000,
    "Goregaon (East)": 35000, "Malad (West)": 34000, "Malad (East)": 32000,
    "Kandivali (West)": 30000, "Kandivali (East)": 28000, "Borivali (West)": 35000,
    "Borivali (East)": 32000, "Dahisar (West)": 26000, "Dahisar (East)": 25000,
    "Mira Road": 18000, "Bhayander": 16000, "Versova": 45000, "Lokhandwala": 50000,
    "Oshiwara": 42000, "Powai": 45000, "Chandivali": 38000, "Sakinaka": 30000,
    "DN Nagar": 40000, "Yari Road": 38000, "4 Bungalows": 38000,
    "Vikhroli (West)": 28000, "Vikhroli (East)": 26000, "Kanjurmarg": 28000,
    "Bhandup (West)": 24000, "Bhandup (East)": 22000, "Nahur": 24000,
    "Mulund (West)": 30000, "Mulund (East)": 28000, "Vidyavihar": 30000,
    "Tilaknagar": 28000, "Deonar": 26000,
    "Vashi": 25000, "Belapur": 22000, "Kharghar": 18000, "Panvel": 12000,
    "Nerul": 20000, "Airoli": 18000, "Seawoods": 22000,
    "Thane (West)": 25000, "Thane (East)": 20000, "Naupada": 26000,
    "Wagle Estate": 22000, "Majiwada": 24000, "Ghodbunder Road": 22000,
    "Kalyan (West)": 15000, "Dombivli (East)": 14000
}

# Zone Averages for Interpolation (Fallback)
ZONE_AVERAGES = {
    "South Mumbai": 50000,
    "Western Suburbs": 35000,
    "Central Mumbai": 32000,
    "Eastern Suburbs": 24000,
    "Thane": 20000,
    "Navi Mumbai": 18000,
    "MMR": 12000
}

def get_rent_tier(rent):
    if rent < 80:
        return "budget"
    elif rent <= 150:
        return "moderate"
    elif rent <= 280:
        return "premium"
    else:
        return "luxury"

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_path = os.path.join(project_root, "data", "raw", "localities.csv")
    output_path = os.path.join(project_root, "data", "raw", "rent_data.csv")

    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    # Read localities
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        localities = list(reader)

    print(f"Loaded {len(localities)} localities. Estimating commercial rent...")
    print("-" * 50)

    results = []
    for loc in localities:
        name = loc['name']
        zone = loc['zone']
        
        # Get property rate (Reckoner rate)
        reckoner_rate = SPECIFIC_RATES.get(name)
        if not reckoner_rate:
            reckoner_rate = ZONE_AVERAGES.get(zone, ZONE_AVERAGES["MMR"])
            
        est_rent_sqft = round(reckoner_rate * 0.005, 1)
        rent_tier = get_rent_tier(est_rent_sqft)
        
        results.append({
            "locality": name,
            "reckoner_rate": reckoner_rate,
            "est_rent_sqft": est_rent_sqft,
            "rent_tier": rent_tier
        })

    # Save to CSV
    fieldnames = ["locality", "reckoner_rate", "est_rent_sqft", "rent_tier"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Generated rent data for {len(results)} localities.")
    print("-" * 50)
    print(f"[OK] Step 4 complete - ready for Step 5")
    print(f"Data saved to: {output_path}")

if __name__ == "__main__":
    main()
