"""
05_merge.py
-----------
Merges localities, OSM features, ground truth, and rent data.
Handles fuzzy matching, missing values imputation using zone-level medians,
and drops localities missing >40% of features.

Output: data/processed/features.csv
"""

import os
import pandas as pd
import numpy as np

try:
    from fuzzywuzzy import process
except ImportError:
    # Fallback to simple matching if fuzzywuzzy not installed
    process = None

def get_fuzzy_match(name, choices, threshold=90):
    if process is None:
        return name if name in choices else None
        
    match = process.extractOne(name, choices)
    if match and match[1] >= threshold:
        return match[0]
    return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_raw = os.path.join(project_root, "data", "raw")
    output_path = os.path.join(project_root, "data", "processed", "features.csv")
    
    # Paths
    f_loc = os.path.join(data_raw, "localities.csv")
    f_osm = os.path.join(data_raw, "osm_features.csv")
    f_gt = os.path.join(data_raw, "ground_truth.csv")
    f_rent = os.path.join(data_raw, "rent_data.csv")

    # Ensure files exist
    for f in [f_loc, f_osm, f_gt, f_rent]:
        if not os.path.exists(f):
            print(f"Error: Required file missing -> {f}")
            print("Please ensure Steps 1-4 are completed.")
            return

    print("Loading data files...")
    df_loc = pd.read_csv(f_loc)
    df_osm = pd.read_csv(f_osm)
    df_gt = pd.read_csv(f_gt)
    df_rent = pd.read_csv(f_rent)
    
    print("Merging datasets...")
    # Base merge on localities
    df_merged = df_loc.copy()
    
    # Clean df_osm: drop duplicated columns (like ward, lat, lng, zone)
    cols_to_drop_osm = [c for c in ['ward', 'lat', 'lng', 'zone'] if c in df_osm.columns]
    df_osm = df_osm.drop(columns=cols_to_drop_osm)
    
    # Merge OSM
    df_merged = df_merged.merge(df_osm, on='name', how='left')
    
    # Merge GT
    cols_to_drop_gt = [c for c in ['ward', 'lat', 'lng', 'zone'] if c in df_gt.columns]
    df_gt = df_gt.drop(columns=cols_to_drop_gt)
    df_merged = df_merged.merge(df_gt, on='name', how='left')
    
    # Merge Rent
    if 'locality' in df_rent.columns:
        df_rent = df_rent.rename(columns={'locality': 'name'})
    df_merged = df_merged.merge(df_rent, on='name', how='left')

    # Drop localities missing > 40% of features
    initial_len = len(df_merged)
    feature_cols = [c for c in df_merged.columns if c not in ['name', 'ward', 'zone', 'lat', 'lng', 'rent_tier']]
    
    # Calculate missing percentage per row
    missing_pct = df_merged[feature_cols].isnull().mean(axis=1)
    
    dropped_localities = df_merged[missing_pct > 0.40]['name'].tolist()
    df_merged = df_merged[missing_pct <= 0.40].copy()
    
    print(f"\nDropped {len(dropped_localities)} localities missing >40% of features:")
    if dropped_localities:
        print(", ".join(dropped_localities))
    else:
        print("None")

    # Impute missing numeric values using zone-level median
    numeric_cols = df_merged.select_dtypes(include=[np.number]).columns
    numeric_cols = [c for c in numeric_cols if c not in ['lat', 'lng']]
    
    for col in numeric_cols:
        if df_merged[col].isnull().any():
            # Group by zone and transform to get median
            df_merged[col] = df_merged.groupby('zone')[col].transform(lambda x: x.fillna(x.median()))
            
            # If a zone is completely empty for a feature, fill with global median
            if df_merged[col].isnull().any():
                df_merged[col] = df_merged[col].fillna(df_merged[col].median())

    print("\n--- Merge Report ---")
    print(f"Total rows remaining: {len(df_merged)} (from initial {initial_len})")
    
    missing_after = df_merged.isnull().sum()
    print("Missing values per column (after imputation):")
    missing_after_gt0 = missing_after[missing_after > 0]
    if len(missing_after_gt0) > 0:
        print(missing_after_gt0)
    else:
        print("All missing values successfully imputed.")
    
    # Save processed features
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_merged.to_csv(output_path, index=False)
    
    print("-" * 50)
     - ready for Step 6")
    print(f"Data saved to: {output_path}")

if __name__ == "__main__":
    main()
