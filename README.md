# Locality — Mumbai Business Location Intelligence

### 🚀 [Live Demo — Try it now!](https://locality-intelligence-mumbai.streamlit.app/)

Where should a business open in Mumbai — and why. An end-to-end data science
project that scores the viability of 10 business types (restaurants, gyms,
pharmacies, cafés, and more) across **137 Mumbai localities**, combining
OpenStreetMap infrastructure data, commercial rent estimates, footfall
modelling, and machine learning — with every score reported alongside its
real, measured uncertainty.

## Key features

- **Spatial cross-validation** — models are evaluated with GroupKFold by zone, so scores reflect performance on unseen geography, not memorized localities
- **Model comparison, apples to apples** — Ridge, Random Forest, and Gradient Boosting are all measured against a mean baseline under the *identical* CV protocol; the best model per business type is kept only if it actually beats that baseline
- **Similarity & gap analysis** — a model-free, k-NN peer comparison: what do the 8 most similar localities support vs. what already exists here, self-validated with leave-one-out error
- **SHAP explainability** — per-prediction feature attribution, translated into plain-English drivers
- **Competitive saturation & market gaps** — Blue Ocean / Saturated / Growing / Low Demand tagging per locality and business type
- **Interactive what-if simulator** — adjust infrastructure sliders and watch every downstream score, including derived foot-traffic scores, recompute live
- **Downloadable PDF reports** — a structured report per locality and business category, generated in real time from the live dashboard state, including any active what-if scenario
- **Built-in honesty** — every score ships with its measured error band, every revenue figure is labelled a scenario estimate, and a floating help panel explains the method in plain language on every page

## Project structure

```
├── data/
│   ├── raw/               # Localities, OSM features, ground truth, rent data
│   └── processed/         # Merged features, final dataset, enriched dataset
├── models/                # Trained models, SHAP data, confidence & gap reports
├── scripts/
│   ├── common.py          # Shared constants, paths, footfall formulas
│   ├── 01_localities.py   # 137 Mumbai localities with coordinates
│   ├── 02_osm_features.py # Infrastructure density via Overpass API
│   ├── 03_ground_truth.py # Business counts (Google Maps / OSM / synthetic)
│   ├── 04_rent_data.py    # Commercial rent from Ready Reckoner rates
│   ├── 05_merge.py        # Data merge + imputation
│   ├── 06_footfall.py     # Time-of-day footfall scoring
│   ├── 07_clustering.py   # KMeans locality profiling
│   ├── 08_model.py        # ML training, spatial CV, SHAP
│   ├── 09_enrich.py       # Saturation, revenue, market gap analysis
│   ├── 10_similarity.py   # k-NN peer similarity + supply-gap analysis
│   └── run_all.py         # Full pipeline orchestrator (supports resume / --force)
├── app/
│   ├── dashboard.py       # Streamlit dashboard (7 tabs)
│   ├── report.py          # Real-time PDF report builder
│   ├── predictor.py       # CLI prediction tool
│   └── batch_predict.py   # Batch predictions for all localities
├── tests/
│   └── test_pipeline.py   # pytest suite
└── pyproject.toml
```

## Setup

1. Install dependencies:
```bash
pip install -e ".[explain,maps,dev]"   # or: pip install -r requirements.txt
```

2. Generate data and train models:
```bash
python scripts/run_all.py           # resumes: skips steps whose outputs already exist
python scripts/run_all.py --force   # full re-run from scratch
```
> **Note:** The pipeline uses OpenStreetMap data by default. For Google Maps ground truth, set:
> ```bash
> export GOOGLE_MAPS_API_KEY="your_key_here"
> ```

3. Run the interactive dashboard:
```bash
streamlit run app/dashboard.py
```

4. Run tests:
```bash
pytest tests/ -v
```

## Dashboard tabs

| Tab | What it shows |
|-----|---------------|
| **Explore** | Interactive map, viability estimates, daily foot-traffic rhythm, infrastructure profile |
| **Why these scores** | Global & per-locality feature attribution — explains *why* each score, in plain English |
| **Market view** | Saturation positioning, Blue Ocean opportunities, rough revenue/ROI scenarios |
| **Compare** | Side-by-side comparison of any two localities |
| **Simulate** | Drag sliders to simulate infrastructure changes and see every score respond live |
| **Peer gaps** | Model-free peer comparison: what do the 8 most similar localities support vs. what exists here? |
| **Report** | Download a structured PDF for one locality and business category, including any active what-if scenario |

Every chart carries a view toggle with a convention-correct alternative (ranked
bars ↔ dots, paired bars ↔ dumbbells, radar ↔ bars), and a floating help button
on every page explains how predictions are made, what data is used, how
reliable it is, and the honest limits of the method.

## Methodology

1. **Data collection** — infrastructure counts from OpenStreetMap Overpass API; business counts from Google Places API (with OSM/synthetic fallbacks)
2. **Feature engineering** — time-of-day footfall scores, rent tiers, competitive saturation indices
3. **Unsupervised learning** — KMeans clustering profiles localities as Corporate Hub, Student Zone, Commercial Market, Residential Area, or Mixed-Use
4. **Supervised learning** — per-business-type regressors (Ridge / Random Forest / Gradient Boosting, best-by-CV-MAE) predict viability (0–100), evaluated with spatial cross-validation against a mean baseline run under the *same* CV protocol. Per-type error bars and baseline comparisons are saved to `models/model_confidence.json` and surfaced throughout the dashboard and PDF report.
5. **Enrichment** — revenue estimation, market gap tagging (Blue Ocean / Saturated / Growing / Low Demand)
6. **Similarity & gap analysis** — k-NN on standardized raw infrastructure + rent finds each locality's 8 nearest peers; `expected_count = peer average`, `gap = expected − actual`. Self-validated with leave-one-out MAE against a global-mean baseline (results in `models/gap_report.json`; business types where the baseline wins are flagged as weak signals in the UI and the report).

## Honesty notes

- Viability scores carry a typical spatial-CV error of ±18–25 points; the dashboard and the PDF report show them as banded, directional guidance — not probabilities.
- Revenue/ROI figures are rough scenario estimates (rent-only costs, industry-average revenue) intended for relative comparison between localities, not business planning.
- Business counts come from OpenStreetMap and may undercount small or unregistered businesses.
- The downloadable report ends with a rule-based recommendation that only recommends proceeding when both the predictive model and the peer-gap analysis agree — and says so plainly when they don't.
