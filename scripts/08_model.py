"""
08_model.py
-----------
Trains Random Forest Regressors to predict business viability (success %).
Trains one model per business type, and one Multi-Output RF for comparison.
Saves models to models/ folder.
Output: Feature importance heatmap, model metrics.
"""

import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
import joblib
import matplotlib.pyplot as plt

try:
    import seaborn as sns
except ImportError:
    sns = None

BUSINESS_TYPES = [
    "restaurant", "cafe", "gym", "pharmacy", "beauty_salon", 
    "store", "school", "lodging", "bar", "night_club"
]

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_path = os.path.join(project_root, "data", "processed", "final_dataset.csv")
    models_dir = os.path.join(project_root, "models")
    
    os.makedirs(models_dir, exist_ok=True)

    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        print("Please ensure Step 6 is completed.")
        return

    print("Loading final dataset...")
    df = pd.read_csv(input_path)

    # Prepare features (X)
    # Exclude non-numeric or leak columns
    exclude_cols = ['name', 'ward', 'zone', 'rent_tier', 'cluster_label', 'cluster_id', 'lat', 'lng']
    viability_cols = [c for c in df.columns if 'viability' in c]
    count_cols = [c for c in df.columns if '_count' in c]
    rating_cols = [c for c in df.columns if '_rating' in c]
    
    drop_cols = exclude_cols + viability_cols + count_cols + rating_cols
    feature_cols = [c for c in df.columns if c not in drop_cols]
    
    X = df[feature_cols].fillna(0)
    
    print(f"Using {len(feature_cols)} features for training.")
    
    # Store feature importance
    importance_dict = {}
    
    print("\n--- Training Individual Random Forest Models ---")
    for bt in BUSINESS_TYPES:
        target_col = f"{bt}_viability_norm"
        if target_col not in df.columns:
            print(f"Skipping {bt}: target column not found.")
            continue
            
        y = df[target_col].fillna(0)
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X_train, y_train)
        
        preds = rf.predict(X_test)
        
        mae = mean_absolute_error(y_test, preds)
        rmse = root_mean_squared_error(y_test, preds)
        r2 = r2_score(y_test, preds)
        
        print(f"{bt.upper():<15} | MAE: {mae:.2f} | RMSE: {rmse:.2f} | R2: {r2:.2f}")
        
        # Save model
        joblib.dump(rf, os.path.join(models_dir, f"rf_{bt}.joblib"))
        
        # Feature importance
        importances = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
        importance_dict[bt] = importances
        
        top5 = importances.head(5).index.tolist()
        # print(f"  Top 5 features: {', '.join(top5)}")

    # Train Multi-Output model for comparison
    print("\n--- Training Multi-Output Random Forest ---")
    y_multi = df[[f"{bt}_viability_norm" for bt in BUSINESS_TYPES if f"{bt}_viability_norm" in df.columns]].fillna(0)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y_multi, test_size=0.2, random_state=42)
    
    rf_multi = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_multi.fit(X_train, y_train)
    
    preds_multi = rf_multi.predict(X_test)
    r2_multi = r2_score(y_test, preds_multi)
    print(f"Multi-Output RF | Overall R2 Score: {r2_multi:.2f}")
    
    joblib.dump(rf_multi, os.path.join(models_dir, "rf_multi_output.joblib"))
    
    # Also save the feature columns order so predictor app knows what to use
    joblib.dump(feature_cols, os.path.join(models_dir, "feature_cols.joblib"))

    # Plot feature importance heatmap
    if sns is not None:
        try:
            print("\nGenerating feature importance heatmap...")
            imp_df = pd.DataFrame(importance_dict).T
            plt.figure(figsize=(12, 8))
            sns.heatmap(imp_df, cmap="YlGnBu", xticklabels=True, yticklabels=True)
            plt.title("Feature Importance by Business Type")
            plt.tight_layout()
            heatmap_path = os.path.join(project_root, "models", "feature_importance.png")
            plt.savefig(heatmap_path)
            print(f"Heatmap saved to: {heatmap_path}")
        except Exception as e:
            print(f"Could not generate heatmap: {e}")
    else:
        print("\nNotice: 'seaborn' not installed. Skipping heatmap.")

    print("-" * 50)
     - ready for Step 9")

if __name__ == "__main__":
    main()
