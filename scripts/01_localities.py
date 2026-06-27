"""
01_localities.py
----------------
Creates a CSV of 150 Mumbai localities with:
  name, ward, lat, lng, zone

Zones covered:
  - South Mumbai
  - Central Mumbai
  - Western Suburbs
  - Eastern Suburbs
  - Navi Mumbai
  - Thane

Output: data/raw/localities.csv
"""

import csv
import os

# Locality data: (name, ward, lat, lng, zone)
# Coordinates are approximate centres of each locality.
# Ward codes follow BMC ward boundaries (A-T for BMC; NMC/TMC for Navi/Thane)
LOCALITIES = [
    # -- SOUTH MUMBAI (Ward A, B, C, D, E, F/S, F/N) ------------------------
    ("Colaba",            "A",   18.9067, 72.8147, "South Mumbai"),
    ("Cuffe Parade",      "A",   18.9138, 72.8194, "South Mumbai"),
    ("Navy Nagar",        "A",   18.9000, 72.8136, "South Mumbai"),
    ("Churchgate",        "A",   18.9322, 72.8264, "South Mumbai"),
    ("Fort",              "B",   18.9340, 72.8354, "South Mumbai"),
    ("Ballard Estate",    "B",   18.9387, 72.8406, "South Mumbai"),
    ("Mandvi",            "B",   18.9490, 72.8376, "South Mumbai"),
    ("Masjid Bunder",     "B",   18.9512, 72.8381, "South Mumbai"),
    ("Crawford Market",   "B",   18.9469, 72.8332, "South Mumbai"),
    ("Marine Lines",      "C",   18.9447, 72.8231, "South Mumbai"),
    ("Charni Road",       "C",   18.9511, 72.8190, "South Mumbai"),
    ("Grant Road",        "C",   18.9640, 72.8179, "South Mumbai"),
    ("Girgaon",           "C",   18.9582, 72.8178, "South Mumbai"),
    ("Malabar Hill",      "D",   18.9630, 72.8026, "South Mumbai"),
    ("Pedder Road",       "D",   18.9714, 72.8089, "South Mumbai"),
    ("Breach Candy",      "D",   18.9697, 72.8067, "South Mumbai"),
    ("Tardeo",            "D",   18.9745, 72.8136, "South Mumbai"),
    ("Bhendi Bazaar",     "E",   18.9527, 72.8352, "South Mumbai"),
    ("Nagpada",           "E",   18.9578, 72.8305, "South Mumbai"),
    ("Dongri",            "E",   18.9553, 72.8399, "South Mumbai"),
    ("Mazgaon",           "F/N", 18.9607, 72.8474, "South Mumbai"),
    ("Reay Road",         "F/N", 18.9683, 72.8514, "South Mumbai"),
    ("Byculla",           "F/S", 18.9716, 72.8374, "South Mumbai"),
    ("Jacob Circle",      "F/S", 18.9757, 72.8399, "South Mumbai"),
    ("Worli",             "G/S", 19.0074, 72.8175, "South Mumbai"),

    # -- CENTRAL MUMBAI (Ward G, H, K/E, K/W) --------------------------------
    ("Dadar (East)",      "G/N", 19.0176, 72.8472, "Central Mumbai"),
    ("Dadar (West)",      "G/N", 19.0190, 72.8421, "Central Mumbai"),
    ("Mahim",             "G/N", 19.0365, 72.8395, "Central Mumbai"),
    ("Matunga",           "G/S", 19.0234, 72.8596, "Central Mumbai"),
    ("Parel",             "G/S", 18.9944, 72.8416, "Central Mumbai"),
    ("Lower Parel",       "G/S", 18.9934, 72.8285, "Central Mumbai"),
    ("Lalbaug",           "G/S", 19.0017, 72.8391, "Central Mumbai"),
    ("Sewri",             "F/N", 19.0001, 72.8593, "Central Mumbai"),
    ("Cotton Green",      "F/N", 18.9845, 72.8562, "Central Mumbai"),
    ("Wadala",            "F/S", 19.0178, 72.8608, "Central Mumbai"),
    ("Sion",              "H",   19.0404, 72.8619, "Central Mumbai"),
    ("Dharavi",           "H",   19.0370, 72.8530, "Central Mumbai"),
    ("Chunabhatti",       "H",   19.0448, 72.8710, "Central Mumbai"),
    ("Antop Hill",        "H",   19.0270, 72.8663, "Central Mumbai"),
    ("Chembur",           "M/E", 19.0623, 72.9004, "Central Mumbai"),
    ("Govandi",           "M/E", 19.0602, 72.9157, "Central Mumbai"),
    ("Mankhurd",          "M/E", 19.0518, 72.9277, "Central Mumbai"),
    ("Trombay",           "M/E", 19.0416, 72.9346, "Central Mumbai"),
    ("Kurla (West)",      "L",   19.0698, 72.8798, "Central Mumbai"),
    ("Kurla (East)",      "L",   19.0716, 72.8884, "Central Mumbai"),
    ("Ghatkopar (West)",  "N",   19.0858, 72.9063, "Central Mumbai"),
    ("Ghatkopar (East)",  "N",   19.0862, 72.9128, "Central Mumbai"),

    # -- WESTERN SUBURBS (Ward H, K/W, P/N, P/S, R/N, R/C, R/S) -------------
    ("Bandra (West)",     "H",   19.0596, 72.8295, "Western Suburbs"),
    ("Bandra (East)",     "H",   19.0607, 72.8386, "Western Suburbs"),
    ("Santacruz (West)",  "K/W", 19.0826, 72.8351, "Western Suburbs"),
    ("Santacruz (East)",  "K/W", 19.0820, 72.8448, "Western Suburbs"),
    ("Vile Parle (West)", "K/W", 19.0990, 72.8363, "Western Suburbs"),
    ("Vile Parle (East)", "K/W", 19.1004, 72.8481, "Western Suburbs"),
    ("Khar (West)",       "H",   19.0721, 72.8329, "Western Suburbs"),
    ("Juhu",              "K/W", 19.1075, 72.8263, "Western Suburbs"),
    ("Andheri (West)",    "K/W", 19.1197, 72.8465, "Western Suburbs"),
    ("Andheri (East)",    "K/E", 19.1136, 72.8697, "Western Suburbs"),
    ("Jogeshwari (West)", "K/W", 19.1374, 72.8468, "Western Suburbs"),
    ("Jogeshwari (East)", "K/E", 19.1370, 72.8596, "Western Suburbs"),
    ("Goregaon (West)",   "P/N", 19.1538, 72.8491, "Western Suburbs"),
    ("Goregaon (East)",   "P/S", 19.1597, 72.8706, "Western Suburbs"),
    ("Malad (West)",      "P/N", 19.1876, 72.8489, "Western Suburbs"),
    ("Malad (East)",      "P/S", 19.1949, 72.8689, "Western Suburbs"),
    ("Kandivali (West)",  "R/N", 19.2073, 72.8393, "Western Suburbs"),
    ("Kandivali (East)",  "R/S", 19.2047, 72.8649, "Western Suburbs"),
    ("Borivali (West)",   "R/N", 19.2307, 72.8567, "Western Suburbs"),
    ("Borivali (East)",   "R/S", 19.2281, 72.8687, "Western Suburbs"),
    ("Dahisar (West)",    "R/N", 19.2523, 72.8438, "Western Suburbs"),
    ("Dahisar (East)",    "R/S", 19.2530, 72.8683, "Western Suburbs"),
    ("Mira Road",         "R/C", 19.2812, 72.8682, "Western Suburbs"),
    ("Bhayander",         "R/C", 19.3003, 72.8510, "Western Suburbs"),
    ("Versova",           "K/W", 19.1315, 72.8193, "Western Suburbs"),
    ("Lokhandwala",       "K/W", 19.1390, 72.8286, "Western Suburbs"),
    ("Oshiwara",          "K/W", 19.1464, 72.8290, "Western Suburbs"),
    ("Powai",             "L",   19.1176, 72.9060, "Western Suburbs"),
    ("Chandivali",        "L",   19.1062, 72.9073, "Western Suburbs"),
    ("Sakinaka",          "L",   19.0967, 72.8905, "Western Suburbs"),

    # -- EASTERN SUBURBS (Ward L, M/E, N, S, T) ------------------------------
    ("Vikhroli (West)",   "L",   19.1063, 72.9245, "Eastern Suburbs"),
    ("Vikhroli (East)",   "L",   19.1091, 72.9352, "Eastern Suburbs"),
    ("Kanjurmarg",        "L",   19.1210, 72.9415, "Eastern Suburbs"),
    ("Bhandup (West)",    "N",   19.1453, 72.9416, "Eastern Suburbs"),
    ("Bhandup (East)",    "N",   19.1474, 72.9488, "Eastern Suburbs"),
    ("Nahur",             "N",   19.1325, 72.9343, "Eastern Suburbs"),
    ("Mulund (West)",     "T",   19.1735, 72.9484, "Eastern Suburbs"),
    ("Mulund (East)",     "T",   19.1756, 72.9633, "Eastern Suburbs"),
    ("Nahur West",        "N",   19.1420, 72.9289, "Eastern Suburbs"),
    ("Tagore Nagar",      "M/E", 19.0784, 72.9207, "Eastern Suburbs"),
    ("Asalpha",           "L",   19.0869, 72.8984, "Eastern Suburbs"),
    ("Vidyavihar",        "L",   19.0817, 72.8966, "Eastern Suburbs"),
    ("Garodia Nagar",     "N",   19.0937, 72.9095, "Eastern Suburbs"),
    ("Pant Nagar",        "N",   19.0898, 72.9047, "Eastern Suburbs"),
    ("Tilaknagar",        "M/E", 19.0596, 72.9098, "Eastern Suburbs"),
    ("Chembur Colony",    "M/E", 19.0537, 72.8942, "Eastern Suburbs"),
    ("Deonar",            "M/E", 19.0457, 72.9186, "Eastern Suburbs"),
    ("Shivaji Nagar (E)", "M/E", 19.0355, 72.9281, "Eastern Suburbs"),
    ("Vashi Naka",        "M/E", 19.0643, 72.9248, "Eastern Suburbs"),
    ("Kurla North",       "L",   19.0762, 72.8843, "Eastern Suburbs"),

    # -- NAVI MUMBAI (NMC Wards) ----------------------------------------------
    ("Vashi",             "NMC-A", 19.0771, 73.0072, "Navi Mumbai"),
    ("Belapur",           "NMC-B", 19.0229, 73.0346, "Navi Mumbai"),
    ("Kharghar",          "NMC-C", 19.0474, 73.0661, "Navi Mumbai"),
    ("Panvel",            "NMC-D", 18.9894, 73.1175, "Navi Mumbai"),
    ("Nerul",             "NMC-E", 19.0398, 73.0175, "Navi Mumbai"),
    ("Airoli",            "NMC-F", 19.1557, 72.9990, "Navi Mumbai"),
    ("Ghansoli",          "NMC-G", 19.1178, 73.0025, "Navi Mumbai"),
    ("Kopar Khairane",    "NMC-H", 19.1045, 73.0065, "Navi Mumbai"),
    ("Sanpada",           "NMC-I", 19.0606, 73.0098, "Navi Mumbai"),
    ("Turbhe",            "NMC-J", 19.0866, 73.0174, "Navi Mumbai"),
    ("Juinagar",          "NMC-K", 19.0271, 73.0187, "Navi Mumbai"),
    ("Seawoods",          "NMC-L", 19.0181, 73.0153, "Navi Mumbai"),
    ("Ulwe",              "NMC-M", 18.9734, 73.0247, "Navi Mumbai"),
    ("Dronagiri",         "NMC-N", 18.9376, 72.9831, "Navi Mumbai"),
    ("Kamothe",           "NMC-O", 19.0126, 73.0889, "Navi Mumbai"),
    ("Roadpali",          "NMC-P", 19.0289, 73.0997, "Navi Mumbai"),
    ("New Panvel",        "NMC-Q", 18.9960, 73.1092, "Navi Mumbai"),
    ("Taloja",            "NMC-R", 19.0658, 73.1238, "Navi Mumbai"),
    ("Kalamboli",         "NMC-S", 19.0346, 73.0804, "Navi Mumbai"),
    ("Pushpak Nagar",     "NMC-T", 19.0200, 73.1018, "Navi Mumbai"),

    # -- THANE (TMC Wards) ---------------------------------------------------
    ("Thane (West)",      "TMC-A", 19.2183, 72.9781, "Thane"),
    ("Thane (East)",      "TMC-B", 19.2143, 72.9960, "Thane"),
    ("Kopri",             "TMC-C", 19.2071, 72.9990, "Thane"),
    ("Naupada",           "TMC-D", 19.1998, 72.9818, "Thane"),
    ("Vartak Nagar",      "TMC-E", 19.2293, 72.9690, "Thane"),
    ("Wagle Estate",      "TMC-F", 19.1987, 72.9627, "Thane"),
    ("Manpada",           "TMC-G", 19.1908, 73.0182, "Thane"),
    ("Ghodbunder Road",   "TMC-H", 19.2550, 72.9680, "Thane"),
    ("Majiwada",          "TMC-I", 19.2352, 72.9793, "Thane"),
    ("Balkum",            "TMC-J", 19.2452, 72.9893, "Thane"),
    ("Pokhran Road",      "TMC-K", 19.2100, 73.0065, "Thane"),
    ("Dombivli (East)",   "KDMC-A",19.2157, 73.0852, "Thane"),
    ("Dombivli (West)",   "KDMC-B",19.2118, 73.0785, "Thane"),
    ("Kalyan (East)",     "KDMC-C",19.2437, 73.1308, "Thane"),
    ("Kalyan (West)",     "KDMC-D",19.2355, 73.1249, "Thane"),
    ("Ulhasnagar",        "UMC-A", 19.2183, 73.1544, "Thane"),
    ("Bhiwandi",          "BCC-A", 19.2967, 73.0585, "Thane"),
    ("Murbad",            "TMC-L", 19.2574, 73.3912, "Thane"),
    ("Ambernath",         "AMC-A", 19.1979, 73.1874, "Thane"),
    ("Badlapur",          "TMC-M", 19.1550, 73.2547, "Thane"),
]

# Main logic
def main():
    # Build output path relative to this script location
    script_dir = os.path.dirname(os.path.abspath(__file__))   # scripts/
    project_root = os.path.dirname(script_dir)                 # project root
    output_path = os.path.join(project_root, "data", "raw", "localities.csv")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)   # ensure folder exists

    print("Writing localities to:", output_path)
    print("-" * 50)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "ward", "lat", "lng", "zone"])  # header row

        for row in LOCALITIES:
            writer.writerow(row)
            print(f"  Wrote: {row[0]:30s}  ({row[4]})")

    print("-" * 50)
    print(f"\nTotal localities written: {len(LOCALITIES)}")

    # Zone breakdown summary
    zone_counts = {}
    for row in LOCALITIES:
        zone_counts[row[4]] = zone_counts.get(row[4], 0) + 1

    print("\nZone breakdown:")
    for zone, count in zone_counts.items():
        print(f"   {zone:<22s}: {count} localities")

    print("\n Step 1 complete - ready for Step 2")


if __name__ == "__main__":
    main()
