"""
10_similarity.py
----------------
Similarity-based gap analysis — the honest alternative to regression at n=137.

For each locality, find its k most similar peers (k-NN on standardized raw
infrastructure + rent), then for each business type:

    expected_count = mean count among peers
    gap            = expected_count - actual_count

gap > 0  -> similar localities support more of this business than exist here
            (underserved market, potential opportunity)
gap < 0  -> more businesses than peers support (crowded relative to profile)

Self-evaluation: leave-one-out MAE of expected_count vs actual count,
compared against a global-mean baseline, saved to models/gap_report.json.

Reads:   data/processed/enriched_dataset.csv
Writes:  data/processed/enriched_dataset.csv (adds columns),
         models/neighbors.json, models/gap_report.json
"""

import json
import os

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from common import (BUSINESS_TYPES, DATA_PROCESSED, MODELS_DIR,
                    N_NEIGHBORS, SIMILARITY_FEATURES)


def main():
    input_path = os.path.join(DATA_PROCESSED, "enriched_dataset.csv")
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found. Run steps 1-9 first.")
        return

    df = pd.read_csv(input_path)
    features = [c for c in SIMILARITY_FEATURES if c in df.columns]
    print(f"Similarity space: {len(features)} features, {len(df)} localities, k={N_NEIGHBORS}")

    X = StandardScaler().fit_transform(df[features].fillna(0))

    # +1 to leave room for self; self is NOT always at position 0 when
    # feature vectors tie at distance 0, so filter by index explicitly.
    nn = NearestNeighbors(n_neighbors=N_NEIGHBORS + 1).fit(X)
    dist_all, idx_all = nn.kneighbors(X)
    idx = np.empty((len(df), N_NEIGHBORS), dtype=int)
    dist = np.empty((len(df), N_NEIGHBORS))
    for i in range(len(df)):
        keep = [k for k in range(idx_all.shape[1]) if idx_all[i, k] != i][:N_NEIGHBORS]
        idx[i] = idx_all[i, keep]
        dist[i] = dist_all[i, keep]

    # Save peer lists for the dashboard
    neighbors = {
        df.iloc[i]["name"]: [
            {"name": df.iloc[j]["name"], "zone": df.iloc[j]["zone"],
             "distance": round(float(d), 2)}
            for j, d in zip(idx[i], dist[i])
        ]
        for i in range(len(df))
    }
    with open(os.path.join(MODELS_DIR, "neighbors.json"), "w") as f:
        json.dump(neighbors, f, indent=1)

    # Expected counts + gaps, and leave-one-out evaluation.
    # Note: expected_count already excludes self (neighbors drop self),
    # so the expected value IS the LOO prediction.
    gap_report = {}
    for bt in BUSINESS_TYPES:
        count_col = f"{bt}_count"
        if count_col not in df.columns:
            continue
        counts = df[count_col].fillna(0).to_numpy(dtype=float)

        expected = counts[idx].mean(axis=1)
        df[f"{bt}_expected_count"] = expected.round(1)
        df[f"{bt}_gap"] = (expected - counts).round(1)

        knn_mae = float(np.abs(expected - counts).mean())
        baseline_mae = float(np.abs(counts.mean() - counts).mean())
        gap_report[bt] = {
            "loo_mae": round(knn_mae, 2),
            "baseline_mae": round(baseline_mae, 2),
            "beats_baseline": bool(knn_mae < baseline_mae),
        }
        status = "OK" if knn_mae < baseline_mae else "!! baseline wins"
        print(f"  {bt:<14} LOO MAE: {knn_mae:6.2f} | mean-baseline: {baseline_mae:6.2f}  [{status}]")

    with open(os.path.join(MODELS_DIR, "gap_report.json"), "w") as f:
        json.dump(gap_report, f, indent=2)

    df.to_csv(input_path, index=False)

    n_better = sum(1 for r in gap_report.values() if r["beats_baseline"])
    print("-" * 50)
    print(f"[OK] Step 10 complete - gap analysis beats mean baseline for "
          f"{n_better}/{len(gap_report)} business types")
    print(f"Neighbors saved to: {os.path.join(MODELS_DIR, 'neighbors.json')}")


if __name__ == "__main__":
    main()
