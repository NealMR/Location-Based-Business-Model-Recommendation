"""
07_clustering.py
----------------
Clusters localities based on footfall, infrastructure, and rent using KMeans.
Determines cluster profiles (Corporate Hub, Student Zone, etc.)
Plots an interactive Folium map.
Output: updates final_dataset.csv, clusters_map.html
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

try:
    import folium
except ImportError:
    folium = None

def assign_cluster_labels(centroids_df):
    """
    Heuristic to assign meaningful labels to clusters based on their centroids.
    """
    labels = {}
    
    # Simple logic based on relative ranking of cluster centroids
    # Rank them (0 to 4)
    ranked = centroids_df.rank()
    
    for cluster_id, row in ranked.iterrows():
        # High office + high transit -> Corporate Hub
        if row.get('office_hr_footfall', 0) >= 4:
            labels[cluster_id] = "Corporate Hub"
        # High college + low rent -> Student Zone
        elif row.get('norm_colleges', 0) >= 4 and row.get('norm_rent', 5) <= 2:
            labels[cluster_id] = "Student Zone"
        # High mall/weekend + high footfall -> Commercial Market
        elif row.get('weekend_footfall', 0) >= 4:
            labels[cluster_id] = "Commercial Market"
        # High footfall but low office/mall -> Residential Area
        elif row.get('overall_footfall', 0) >= 3 and row.get('norm_rent', 5) <= 3:
            labels[cluster_id] = "Residential Area"
        else:
            labels[cluster_id] = "Mixed-Use Locality"
            
    # Fallback to ensure unique names aren't strictly required but makes it nicer
    return labels

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_path = os.path.join(project_root, "data", "processed", "final_dataset.csv")
    map_path = os.path.join(project_root, "clusters_map.html")

    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        print("Please ensure Step 6 is completed.")
        return

    print("Loading final dataset...")
    df = pd.read_csv(input_path)
    
    # Prepare features for clustering
    df['norm_offices'] = df.get('offices', 0) / df.get('offices', 1).max() * 100
    df['norm_colleges'] = df.get('colleges', 0) / df.get('colleges', 1).max() * 100
    df['norm_rent'] = df.get('est_rent_sqft', 0) / df.get('est_rent_sqft', 1).max() * 100
    
    clustering_cols = [
        'overall_footfall', 
        'office_hr_footfall', 
        'weekend_footfall',
        'norm_offices',
        'norm_colleges',
        'norm_rent'
    ]
    
    X = df[clustering_cols].fillna(0)
    
    print("\nRunning Elbow Method for k=2 to 10...")
    inertias = []
    K_range = range(2, 11)
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X)
        inertias.append(kmeans.inertia_)
        
    # We will just print the inertias (could plot and save)
    for k, inertia in zip(K_range, inertias):
        print(f"  k={k}: inertia={inertia:.1f}")

    print("\nApplying KMeans with k=5...")
    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    df['cluster_id'] = kmeans.fit_predict(X)
    
    # Calculate centroids
    centroids = df.groupby('cluster_id')[clustering_cols].mean()
    cluster_mapping = assign_cluster_labels(centroids)
    
    df['cluster_label'] = df['cluster_id'].map(cluster_mapping)
    
    print("\n--- Cluster Summary Table ---")
    summary = df.groupby('cluster_label')[clustering_cols].mean().round(1)
    print(summary.to_string())
    
    # Save back to CSV
    df.to_csv(input_path, index=False)
    
    # Plot Map
    if folium is None:
        print("\nNotice: 'folium' library not installed. Skipping map generation.")
        print("To generate map, run: pip install folium")
    else:
        print("\nGenerating interactive map...")
        # Mumbai center
        mumbai_map = folium.Map(location=[19.0760, 72.8777], zoom_start=11)
        
        colors = {
            "Corporate Hub": "darkblue",
            "Student Zone": "orange",
            "Commercial Market": "purple",
            "Residential Area": "green",
            "Mixed-Use Locality": "gray"
        }
        
        for _, row in df.iterrows():
            if pd.notna(row['lat']) and pd.notna(row['lng']):
                color = colors.get(row['cluster_label'], "blue")
                folium.CircleMarker(
                    location=[row['lat'], row['lng']],
                    radius=6,
                    popup=f"<b>{row['name']}</b><br>Cluster: {row['cluster_label']}<br>Footfall: {row.get('overall_footfall',0)}",
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7
                ).add_to(mumbai_map)
                
        mumbai_map.save(map_path)
        print(f"Map saved to: {map_path}")

    print("-" * 50)
    print(f"[OK] Step 7 complete - ready for Step 8")

if __name__ == "__main__":
    main()
