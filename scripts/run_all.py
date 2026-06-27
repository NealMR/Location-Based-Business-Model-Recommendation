import subprocess
import os

print("Starting FULL real data pipeline...")

# Set API key for the environment (loads from your system variables)
env = os.environ.copy()

print("Launching Step 2 (OSM) and Step 3 (Google Maps) in parallel...")
print("This will take about 45-50 minutes due to API rate limits.")

# Run in parallel
p2 = subprocess.Popen(['python', 'scripts/02_osm_features.py'], stdout=open('data/raw/osm_log.txt', 'w'), stderr=subprocess.STDOUT)
p3 = subprocess.Popen(['python', 'scripts/03_ground_truth.py'], env=env, stdout=open('data/raw/gt_log.txt', 'w'), stderr=subprocess.STDOUT)

# Wait for both to finish
p2.wait()
p3.wait()

print("Data fetching complete. Running processing and modeling pipeline...")

for script in ['scripts/05_merge.py', 'scripts/06_footfall.py', 'scripts/07_clustering.py', 'scripts/08_model.py']:
    print(f"Running {script}...")
    subprocess.run(['python', script], check=True)

print("\n" + "="*50)
print("PIPELINE FINISHED SUCCESSFULLY!")
print("You can now run: python app/predictor.py")
print("="*50)
