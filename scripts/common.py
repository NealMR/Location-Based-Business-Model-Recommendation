"""
common.py
---------
Shared constants and paths for the pipeline scripts and apps.
Single source of truth — do not redefine BUSINESS_TYPES elsewhere.
"""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_RAW = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

BUSINESS_TYPES = [
    "restaurant", "cafe", "gym", "pharmacy", "beauty_salon",
    "store", "school", "lodging", "bar", "night_club"
]


# Raw features used for locality similarity (k-NN). Deliberately excludes
# derived footfall scores (redundant with these) and business counts (which
# are what the gap analysis predicts).
SIMILARITY_FEATURES = [
    "railway_stations", "metro_stations", "bus_stops", "colleges", "schools",
    "offices", "malls", "hospitals", "parking_lots", "tourist_spots",
    "est_rent_sqft",
]

N_NEIGHBORS = 8  # peer group size for gap analysis


def model_path(business_type):
    """Canonical path of the trained model for a business type."""
    return os.path.join(MODELS_DIR, f"model_{business_type}.joblib")


# Footfall formulas (weights shared between 06_footfall.py and the
# dashboard's what-if simulator so simulated infra changes propagate).
# Each entry: score_name -> list of (weight, component) where component is a
# tuple of raw feature columns summed before min-max normalization.
FOOTFALL_FORMULAS = {
    "overall_footfall": [
        (0.30, ("railway_stations", "metro_stations")),
        (0.25, ("offices",)),
        (0.20, ("colleges", "schools")),
        (0.15, ("malls",)),
        (0.10, ("tourist_spots",)),
    ],
    "morning_footfall": [
        (0.4, ("offices",)),
        (0.3, ("railway_stations", "metro_stations")),
        (0.2, ("colleges",)),
        (0.1, ("bus_stops",)),
    ],
    "afternoon_footfall": [
        (0.4, ("malls",)),
        (0.3, ("offices",)),
        (0.2, ("tourist_spots",)),
        (0.1, ("colleges",)),
    ],
    "evening_footfall": [
        (0.4, ("malls",)),
        (0.3, ("tourist_spots",)),
        (0.2, ("offices",)),
        (0.1, ("railway_stations", "metro_stations")),
    ],
    "office_hr_footfall": [
        (0.5, ("offices",)),
        (0.3, ("railway_stations", "metro_stations")),
        (0.2, ("bus_stops",)),
    ],
    "weekend_footfall": [
        (0.5, ("malls",)),
        (0.3, ("tourist_spots",)),
        (0.2, ("colleges",)),
    ],
}


def compute_footfall_scores(row_values, df):
    """
    Recompute all footfall scores for one hypothetical locality.

    row_values: dict-like of raw feature values (e.g. a simulated row)
    df: full dataset DataFrame used for min-max normalization bounds
    Returns dict of score_name -> value (0-100 scale).
    """
    scores = {}
    for score_name, terms in FOOTFALL_FORMULAS.items():
        total = 0.0
        for weight, cols in terms:
            raw = sum(float(row_values.get(c, 0) or 0) for c in cols)
            series = sum(df[c].fillna(0) for c in cols if c in df.columns)
            lo, hi = float(series.min()), float(series.max())
            norm = ((raw - lo) / (hi - lo)) * 100.0 if hi > lo else 0.0
            total += weight * max(0.0, min(100.0, norm))
        scores[score_name] = round(total, 1)
    return scores
