"""
predictor.py
------------
Command line app to predict business success for Mumbai Localities.
"""

import os
import sys
import pandas as pd
import joblib

BUSINESS_TYPES = [
    "restaurant", "cafe", "gym", "pharmacy", "beauty_salon", 
    "store", "school", "lodging", "bar", "night_club"
]

def load_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_path = os.path.join(project_root, "data", "processed", "final_dataset.csv")
    if not os.path.exists(input_path):
        return None
    return pd.read_csv(input_path)

def build_progress_bar(percentage):
    # 10 blocks total
    filled = int(percentage / 10)
    empty = 10 - filled
    return "█" * filled + "░" * empty

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    models_dir = os.path.join(project_root, "models")
    
    print("\nLoading system...")
    df = load_data()
    
    if df is None:
        print("Error: final_dataset.csv not found. Please run the pipeline first.")
        return
        
    try:
        feature_cols = joblib.load(os.path.join(models_dir, "feature_cols.joblib"))
    except FileNotFoundError:
        print("Error: Models not found. Please run Step 8 (08_model.py) first.")
        return

    print("="*60)
    print("Welcome to Business Success Predictor - Mumbai")
    print("="*60)
    
    loc_input = input("\nEnter locality name (or press Enter to input manually): ").strip()
    
    locality_name = "Custom Location"
    cluster_label = "Mixed-Use Locality"
    overall_footfall = 50.0
    
    input_features = {}
    
    if loc_input:
        match = df[df['name'].str.lower() == loc_input.lower()]
        if not match.empty:
            row = match.iloc[0]
            locality_name = row['name']
            cluster_label = row.get('cluster_label', 'Unknown')
            overall_footfall = row.get('overall_footfall', 0.0)
            
            for col in feature_cols:
                input_features[col] = [row.get(col, 0.0)]
        else:
            print(f"Locality '{loc_input}' not found in database. Switching to manual input.")
            loc_input = ""
            
    if not loc_input:
        print("\n--- Manual Feature Input ---")
        for col in feature_cols:
            val = input(f"Enter {col} (default 0): ").strip()
            input_features[col] = [float(val) if val else 0.0]
            
        # Very basic dummy values for display if manual
        overall_footfall = input_features.get('overall_footfall', [50.0])[0]
        cluster_label = "Custom Profile"
        
    X_pred = pd.DataFrame(input_features)
    
    # Load models and predict
    results = []
    for bt in BUSINESS_TYPES:
        model_path = os.path.join(models_dir, f"rf_{bt}.joblib")
        if os.path.exists(model_path):
            rf = joblib.load(model_path)
            score = rf.predict(X_pred)[0]
            # Cap at 99% for realism
            score = min(score, 99.0)
            results.append((bt.replace('_', ' ').title(), score))
            
    # Sort best to worst
    results.sort(key=lambda x: x[1], reverse=True)
    
    print("\n  ╔" + "═"*42 + "╗")
    print("  ║   Business Success Predictor — Mumbai    ║")
    print("  ╠" + "═"*42 + "╣")
    print(f"  ║  Location  : {locality_name[:28]:<28}║")
    print(f"  ║  Cluster   : {cluster_label[:28]:<28}║")
    print(f"  ║  Footfall  : {int(overall_footfall):>2} / 100                     ║")
    print("  ╠" + "═"*42 + "╣")
    print("  ║  RECOMMENDED BUSINESSES                  ║")
    
    for i, (bt, score) in enumerate(results[:5], 1):
        bar = build_progress_bar(score)
        print(f"  ║  {i}. {bt:<17} {bar}  {int(score):>2}%   ║")
        
    print("  ╠" + "═"*42 + "╣")
    
    # Simple insight based on top business
    top_bt = results[0][0].lower() if results else ""
    if "kitchen" in top_bt or "restaurant" in top_bt or "cafe" in top_bt:
        insight = "High food demand. Great for F&B businesses."
    elif "store" in top_bt or "pharmacy" in top_bt:
        insight = "Strong retail footfall. Ideal for commerce."
    elif "gym" in top_bt or "salon" in top_bt:
        insight = "Good residential base for personal services."
    else:
        insight = "Balanced demographic profile."
        
    print(f"  ║  Key insight: {insight:<26} ║")
    print("  ╚" + "═"*42 + "╝\n")

if __name__ == "__main__":
    main()
