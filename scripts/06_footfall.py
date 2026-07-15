"""
06_footfall.py
--------------
Calculates various footfall scores (overall, morning, afternoon, evening, office_hr, weekend)
based on infrastructure features. Normalizes everything to a 0-100 scale.
Output: data/processed/final_dataset.csv
"""

import os
import pandas as pd

from common import FOOTFALL_FORMULAS

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
    
    print("Computing normalized scores...")
    # Formulas live in common.py so the dashboard simulator uses the same math
    for score_name, terms in FOOTFALL_FORMULAS.items():
        total = 0.0
        for weight, cols in terms:
            component = sum(df.get(c, pd.Series(0, index=df.index)).fillna(0) for c in cols)
            total = total + weight * normalize_series(component)
        df[score_name] = total.round(1)

    # Save final dataset
    df.to_csv(output_path, index=False)
    print("-" * 50)
    print(f"[OK] Step 6 complete - ready for Step 7")
    print(f"Dataset generated with {len(df)} localities and {len(df.columns)} features.")
    print(f"Data saved to: {output_path}")

if __name__ == "__main__":
    main()
