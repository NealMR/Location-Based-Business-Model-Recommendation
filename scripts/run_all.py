"""
run_all.py
----------
Orchestrates the full data pipeline from raw data to enriched predictions.

Usage:
    python scripts/run_all.py            # resume: skips steps whose outputs exist
    python scripts/run_all.py --force    # re-run everything from scratch
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJECT_ROOT, DATA_RAW, DATA_PROCESSED, MODELS_DIR

FORCE = "--force" in sys.argv

# (script, label, output that marks the step complete)
STEPS_FETCH = [
    ("scripts/01_localities.py", "Step 1: Localities", os.path.join(DATA_RAW, "localities.csv")),
]
STEPS_PARALLEL = [
    ("scripts/02_osm_features.py", "Step 2: OSM features", os.path.join(DATA_RAW, "osm_features.csv")),
    ("scripts/03_ground_truth.py", "Step 3: Ground truth", os.path.join(DATA_RAW, "ground_truth.csv")),
]
STEPS_SEQUENTIAL = [
    ("scripts/04_rent_data.py", "Step 4: Rent estimation", os.path.join(DATA_RAW, "rent_data.csv")),
    ("scripts/05_merge.py", "Step 5: Merge & imputation", os.path.join(DATA_PROCESSED, "features.csv")),
    ("scripts/06_footfall.py", "Step 6: Footfall scoring", os.path.join(DATA_PROCESSED, "final_dataset.csv")),
    ("scripts/07_clustering.py", "Step 7: Clustering", None),  # updates final_dataset in place
    ("scripts/08_model.py", "Step 8: Model training", os.path.join(MODELS_DIR, "model_confidence.json")),
    ("scripts/09_enrich.py", "Step 9: Enrichment", os.path.join(DATA_PROCESSED, "enriched_dataset.csv")),
    ("scripts/10_similarity.py", "Step 10: Similarity & gap analysis", os.path.join(MODELS_DIR, "gap_report.json")),
]


def should_skip(output):
    return not FORCE and output is not None and os.path.exists(output)


def run_step(script, label):
    print(f"\n[{label}]")
    subprocess.run([sys.executable, script], check=True, cwd=PROJECT_ROOT)


def main():
    print("=" * 60)
    print("  LOCATION-BASED BUSINESS MODEL RECOMMENDATION")
    print(f"  Full Pipeline Runner ({'force' if FORCE else 'resume'} mode)")
    print("=" * 60)

    for script, label, output in STEPS_FETCH:
        if should_skip(output):
            print(f"\n[{label}] SKIPPED (output exists: {output})")
        else:
            run_step(script, label)

    # Steps 2 & 3 are network-bound and independent -> run in parallel
    os.makedirs(DATA_RAW, exist_ok=True)
    procs = []
    for script, label, output in STEPS_PARALLEL:
        if should_skip(output):
            print(f"\n[{label}] SKIPPED (output exists: {output})")
            continue
        log_path = output.replace(".csv", "_log.txt")
        print(f"\n[{label}] started (log: {log_path})")
        log = open(log_path, "w")
        procs.append((label, subprocess.Popen(
            [sys.executable, script], stdout=log, stderr=subprocess.STDOUT, cwd=PROJECT_ROOT
        )))
    for label, p in procs:
        if p.wait() != 0:
            print(f"ERROR: {label} failed - check its log file.")
            sys.exit(1)

    for script, label, output in STEPS_SEQUENTIAL:
        if should_skip(output):
            print(f"\n[{label}] SKIPPED (output exists: {output})")
        else:
            run_step(script, label)

    print("\n" + "=" * 60)
    print("  PIPELINE FINISHED SUCCESSFULLY!")
    print("  Run the dashboard: streamlit run app/dashboard.py")
    print("  Or CLI predictor:  python app/predictor.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
