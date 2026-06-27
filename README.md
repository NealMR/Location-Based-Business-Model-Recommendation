# Location-Based Business Model Recommendation

This project recommends the viability of various business types (e.g., Restaurants, Gyms, Pharmacies) across 150 localities in Mumbai. It leverages OpenStreetMap data for infrastructure density and integrates it with local commercial rent estimates and footfall scoring models.

## Structure
- `data/` - Raw inputs and processed features
- `models/` - Trained Random Forest models
- `scripts/` - Data ingestion, processing, and training pipeline
- `app/` - Streamlit dashboard and CLI prediction tools

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Generate data and train models (requires Google Maps API key):
```bash
export GOOGLE_MAPS_API_KEY="your_api_key_here"
python scripts/run_all.py
```
*(Note: The pipeline includes a fallback mode if the API key is unavailable or restricted).*

3. Run the interactive dashboard:
```bash
streamlit run app/dashboard.py
```
