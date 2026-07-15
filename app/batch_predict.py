"""
batch_predict.py
----------------
Runs the trained models to generate predictions for EVERY locality.
Saves the top recommendations to a CSV report.
"""

import os
import sys
import pandas as pd
import joblib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from common import BUSINESS_TYPES, model_path as canonical_model_path

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_path = os.path.join(project_root, "data", "processed", "final_dataset.csv")
    models_dir = os.path.join(project_root, "models")
    output_path = os.path.join(project_root, "data", "processed", "all_recommendations.csv")
    
    if not os.path.exists(input_path):
        print("Data not found.")
        return
        
    df = pd.read_csv(input_path)
    feature_cols = joblib.load(os.path.join(models_dir, "feature_cols.joblib"))
    
    # Prepare X
    X = df[feature_cols].fillna(0)
    
    # Load all models
    models = {}
    for bt in BUSINESS_TYPES:
        path = canonical_model_path(bt)
        if os.path.exists(path):
            # Safe: models are trained and written locally by scripts/08_model.py
            models[bt] = joblib.load(path)
            
    if not models:
        print("Models not found!")
        return

    print(f"Generating predictions for all {len(df)} localities...")
    
    results_list = []
    
    for idx, row in df.iterrows():
        loc_name = row['name']
        x_pred = pd.DataFrame([X.iloc[idx]])
        
        preds = []
        for bt, model in models.items():
            score = min(model.predict(x_pred)[0], 99.0)
            preds.append((bt.replace('_', ' ').title(), score))
            
        preds.sort(key=lambda x: x[1], reverse=True)
        
        results_list.append({
            "Locality": loc_name,
            "Cluster": row.get('cluster_label', 'Unknown'),
            "Footfall_Score": round(row.get('overall_footfall', 0), 1),
            "Top_1_Business": preds[0][0],
            "Top_1_Score": round(preds[0][1], 1),
            "Top_2_Business": preds[1][0],
            "Top_2_Score": round(preds[1][1], 1),
            "Top_3_Business": preds[2][0],
            "Top_3_Score": round(preds[2][1], 1)
        })

    out_df = pd.DataFrame(results_list)
    out_df.to_csv(output_path, index=False)
    print(f"Saved recommendations for every locality to: {output_path}")

if __name__ == "__main__":
    main()
