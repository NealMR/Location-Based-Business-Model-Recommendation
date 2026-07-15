"""
09_enrich.py
------------
Post-model enrichment layer that adds portfolio-grade analytics:

  1. Competitive Saturation Index - identifies oversaturated vs. blue-ocean markets
  2. Revenue Estimation - rough monthly revenue/cost/ROI estimates per business type
  3. Market Gap Tagging - classifies each (locality, business) pair as opportunity/saturated

Reads from:  data/processed/final_dataset.csv
Writes to:   data/processed/enriched_dataset.csv
"""

import os
import pandas as pd
import numpy as np

from common import BUSINESS_TYPES

# -- Industry Benchmarks --------------------------------------------------
# Average monthly revenue per business type (Rs. lakhs) - sourced from
# IHRSA (gyms), NRA India (restaurants), CRISIL reports, industry surveys.
# These are ballpark urban-India averages for a small-medium outlet.
AVG_MONTHLY_REVENUE_LAKHS = {
    "restaurant":   6.0,
    "cafe":         3.5,
    "gym":          2.5,
    "pharmacy":     4.0,
    "beauty_salon": 2.0,
    "store":        5.5,
    "school":       8.0,   # tuition centres / coaching
    "lodging":      7.0,
    "bar":          5.0,
    "night_club":   6.5,
}

# Average floor area in sq ft per business type
AVG_SQFT = {
    "restaurant":   800,
    "cafe":         500,
    "gym":          1500,
    "pharmacy":     300,
    "beauty_salon": 400,
    "store":        600,
    "school":       2000,
    "lodging":      3000,
    "bar":          700,
    "night_club":   1200,
}


def compute_saturation(df):
    """
    For each business type, compute:
      saturation_index = existing_count / (overall_footfall + 1)

    High saturation -> many competitors for limited foot traffic.
    Low saturation  -> underserved market (opportunity).
    """
    for bt in BUSINESS_TYPES:
        count_col = f"{bt}_count"
        if count_col in df.columns:
            df[f"{bt}_saturation"] = (
                df[count_col].fillna(0) /
                (df['overall_footfall'].fillna(0) + 1)
            ).round(3)
        else:
            df[f"{bt}_saturation"] = 0.0

    return df


def compute_revenue_estimates(df):
    """
    Estimates monthly revenue, cost, and ROI for each business type per locality.

    Revenue = viability_score/100 * avg_revenue * footfall_multiplier
    Cost    = est_rent_sqft * avg_sqft_for_type
    ROI     = (Revenue - Cost) / Cost * 100
    """
    # Footfall multiplier: normalise overall_footfall to a 0.5-1.5 range
    ff_min = df['overall_footfall'].min()
    ff_max = df['overall_footfall'].max()
    if ff_max > ff_min:
        df['footfall_multiplier'] = 0.5 + (
            (df['overall_footfall'] - ff_min) / (ff_max - ff_min)
        )
    else:
        df['footfall_multiplier'] = 1.0

    for bt in BUSINESS_TYPES:
        viability_col = f"{bt}_viability_norm"
        if viability_col not in df.columns:
            continue

        viability = df[viability_col].fillna(0) / 100.0
        avg_rev = AVG_MONTHLY_REVENUE_LAKHS[bt]
        avg_area = AVG_SQFT[bt]

        # Monthly revenue estimate (Rs. lakhs)
        df[f"{bt}_est_revenue_lakhs"] = (
            viability * avg_rev * df['footfall_multiplier']
        ).round(2)

        # Monthly rent cost (Rs. lakhs)
        df[f"{bt}_est_rent_cost_lakhs"] = (
            df['est_rent_sqft'].fillna(0) * avg_area / 100000
        ).round(2)

        # ROI percentage
        cost = df[f"{bt}_est_rent_cost_lakhs"]
        revenue = df[f"{bt}_est_revenue_lakhs"]
        df[f"{bt}_est_roi_pct"] = np.where(
            cost > 0,
            ((revenue - cost) / cost * 100).round(1),
            0.0
        )

    return df


def tag_market_gaps(df):
    """
    Classifies each (locality, business_type) pair into:
      - 'Blue Ocean'    -> high viability + low saturation (< 25th percentile)
      - 'Saturated'     -> high existing count + low viability
      - 'Growing'       -> moderate viability + moderate saturation
      - 'Low Demand'    -> low viability + low count
    """
    for bt in BUSINESS_TYPES:
        viability_col = f"{bt}_viability_norm"
        saturation_col = f"{bt}_saturation"

        if viability_col not in df.columns or saturation_col not in df.columns:
            df[f"{bt}_market_tag"] = "Unknown"
            continue

        viability = df[viability_col].fillna(0)
        saturation = df[saturation_col].fillna(0)

        sat_25 = saturation.quantile(0.25)
        sat_75 = saturation.quantile(0.75)
        via_median = viability.median()

        conditions = [
            (viability >= via_median) & (saturation <= sat_25),    # Blue Ocean
            (viability < via_median) & (saturation >= sat_75),     # Saturated
            (viability >= via_median) & (saturation > sat_25),     # Growing
        ]
        choices = ['Blue Ocean', 'Saturated', 'Growing']

        df[f"{bt}_market_tag"] = np.select(conditions, choices, default='Low Demand')

    return df


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_path = os.path.join(project_root, "data", "processed", "final_dataset.csv")
    output_path = os.path.join(project_root, "data", "processed", "enriched_dataset.csv")

    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    print("Loading final dataset...")
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} localities with {len(df.columns)} columns.")

    # -- Step 1: Saturation Analysis --------------------------------------
    print("\n[1/3] Computing competitive saturation indices...")
    df = compute_saturation(df)

    # Show top saturated & blue-ocean localities
    for bt in ['restaurant', 'cafe', 'gym']:
        sat_col = f"{bt}_saturation"
        if sat_col in df.columns:
            top_sat = df.nlargest(3, sat_col)[['name', sat_col]]
            low_sat = df.nsmallest(3, sat_col)[['name', sat_col]]
            print(f"\n  {bt.title()} - Most saturated: {', '.join(top_sat['name'].tolist())}")
            print(f"  {bt.title()} - Least saturated: {', '.join(low_sat['name'].tolist())}")

    # -- Step 2: Revenue Estimation ---------------------------------------
    print("\n[2/3] Estimating revenue, cost, and ROI...")
    df = compute_revenue_estimates(df)

    # Show best ROI opportunities
    for bt in ['restaurant', 'cafe', 'gym']:
        roi_col = f"{bt}_est_roi_pct"
        if roi_col in df.columns:
            top_roi = df.nlargest(3, roi_col)[['name', roi_col]]
            print(f"\n  {bt.title()} - Top ROI: {', '.join(f'{r.name}: {r[roi_col]:.0f}%' for _, r in top_roi.iterrows())}")

    # -- Step 3: Market Gap Tags ------------------------------------------
    print("\n[3/3] Tagging market gaps (Blue Ocean / Saturated / Growing / Low Demand)...")
    df = tag_market_gaps(df)

    # Summary
    for bt in ['restaurant', 'cafe']:
        tag_col = f"{bt}_market_tag"
        if tag_col in df.columns:
            counts = df[tag_col].value_counts()
            print(f"\n  {bt.title()} market tags:")
            for tag, cnt in counts.items():
                print(f"    {tag}: {cnt} localities")

    # -- Save -------------------------------------------------------------
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    print("\n" + "-" * 50)
    print(f"[OK] Step 9 complete - enriched dataset ready")
    print(f"  Columns: {len(df.columns)} (was {len(pd.read_csv(input_path).columns)})")
    print(f"  Data saved to: {output_path}")


if __name__ == "__main__":
    main()
