"""
06_footfall.py
--------------
Calculates various footfall scores (overall, morning, afternoon, evening, office_hr, weekend)
based on infrastructure features. Normalizes everything to a 0-100 scale.
Output: data/processed/final_dataset.csv
"""

import os
import pandas as pd

def normalize_series(series):
    """Min-max scaling to 0-100 scale"""
    min_val = series.min()
    max_val = series.max()
    if max_val > min_val:
        return ((series - min_val) / (max_val - min_val)) * 100.0
    return pd.Series([0.0] * len(series), index=series.index)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_path = os.path.join(project_root, "data", "processed", "features.csv")
    output_path = os.path.join(project_root, "data", "processed", "final_dataset.csv")

    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        print("Please ensure Step 5 is completed.")
        return

    print("Loading merged features data...")
    df = pd.read_csv(input_path)
    
    # Extract features needed (handle missing by filling with 0 just in case)
    railway = df.get("railway_stations", 0).fillna(0)
    metro = df.get("metro_stations", 0).fillna(0)
    bus = df.get("bus_stops", 0).fillna(0)
    offices = df.get("offices", 0).fillna(0)
    colleges = df.get("colleges", 0).fillna(0)
    schools = df.get("schools", 0).fillna(0)
    malls = df.get("malls", 0).fillna(0)
    tourist = df.get("tourist_spots", 0).fillna(0)

    transit = railway + metro
    
    print("Computing normalized scores...")
    # Pre-calculate normalized base components
    norm_transit = normalize_series(transit)
    norm_office = normalize_series(offices)
    norm_education = normalize_series(colleges + schools)
    norm_mall = normalize_series(malls)
    norm_tourist = normalize_series(tourist)
    norm_college = normalize_series(colleges)
    norm_bus = normalize_series(bus)

    # Calculate overall footfall
    df['overall_footfall'] = (
        0.30 * norm_transit +
        0.25 * norm_office +
        0.20 * norm_education +
        0.15 * norm_mall +
        0.10 * norm_tourist
    ).round(1)

    # Calculate sub-scores
    df['morning_footfall'] = (
        0.4 * norm_office +
        0.3 * norm_transit +
        0.2 * norm_college +
        0.1 * norm_bus
    ).round(1)

    df['afternoon_footfall'] = (
        0.4 * norm_mall +
        0.3 * norm_office +
        0.2 * norm_tourist +
        0.1 * norm_college
    ).round(1)

    df['evening_footfall'] = (
        0.4 * norm_mall +
        0.3 * norm_tourist +
        0.2 * norm_office +
        0.1 * norm_transit
    ).round(1)

    df['office_hr_footfall'] = (
        0.5 * norm_office +
        0.3 * norm_transit +
        0.2 * norm_bus
    ).round(1)

    df['weekend_footfall'] = (
        0.5 * norm_mall +
        0.3 * norm_tourist +
        0.2 * norm_college
    ).round(1)

    # Save final dataset
    df.to_csv(output_path, index=False)
    print("-" * 50)
     - ready for Step 7")
    print(f"Dataset generated with {len(df)} localities and {len(df.columns)} features.")
    print(f"Data saved to: {output_path}")

if __name__ == "__main__":
    main()
