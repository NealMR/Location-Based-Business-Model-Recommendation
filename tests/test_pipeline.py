"""
tests/test_pipeline.py
----------------------
Unit tests for the Location-Based Business Model Recommendation pipeline.
Covers data schema validation, model I/O, viability formula, saturation, and revenue logic.

Run with:  pytest tests/ -v
"""

import os
import sys
import math
import pytest
import pandas as pd
import numpy as np

# Add project root to path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "app"))


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def localities_df():
    path = os.path.join(PROJECT_ROOT, "data", "raw", "localities.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    pytest.skip("localities.csv not found")


@pytest.fixture
def osm_df():
    path = os.path.join(PROJECT_ROOT, "data", "raw", "osm_features.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    pytest.skip("osm_features.csv not found")


@pytest.fixture
def ground_truth_df():
    path = os.path.join(PROJECT_ROOT, "data", "raw", "ground_truth.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    pytest.skip("ground_truth.csv not found")


@pytest.fixture
def final_df():
    path = os.path.join(PROJECT_ROOT, "data", "processed", "final_dataset.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    pytest.skip("final_dataset.csv not found")


@pytest.fixture
def enriched_df():
    path = os.path.join(PROJECT_ROOT, "data", "processed", "enriched_dataset.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    pytest.skip("enriched_dataset.csv not found")


# ═══════════════════════════════════════════════════════════════════════════
# DATA SCHEMA TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestLocalitiesSchema:
    """Validates the raw localities data."""

    def test_expected_columns(self, localities_df):
        expected = {'name', 'ward', 'lat', 'lng', 'zone'}
        assert expected.issubset(set(localities_df.columns))

    def test_no_duplicate_names(self, localities_df):
        assert localities_df['name'].is_unique, "Duplicate locality names found"

    def test_lat_lng_range(self, localities_df):
        assert localities_df['lat'].between(18.5, 20.0).all(), "Latitude out of Mumbai range"
        assert localities_df['lng'].between(72.5, 73.5).all(), "Longitude out of Mumbai range"

    def test_minimum_localities(self, localities_df):
        assert len(localities_df) >= 100, f"Expected ≥100 localities, got {len(localities_df)}"

    def test_zone_coverage(self, localities_df):
        expected_zones = {"South Mumbai", "Central Mumbai", "Western Suburbs",
                          "Eastern Suburbs", "Navi Mumbai", "Thane"}
        actual_zones = set(localities_df['zone'].unique())
        assert expected_zones.issubset(actual_zones), f"Missing zones: {expected_zones - actual_zones}"


class TestOSMSchema:
    """Validates the OSM features data."""

    def test_has_feature_columns(self, osm_df):
        expected_features = {'railway_stations', 'metro_stations', 'bus_stops',
                             'colleges', 'schools', 'offices', 'malls'}
        assert expected_features.issubset(set(osm_df.columns))

    def test_no_negative_counts(self, osm_df):
        feature_cols = [c for c in osm_df.columns if c not in ['name', 'ward', 'lat', 'lng', 'zone']]
        for col in feature_cols:
            assert (osm_df[col].fillna(0) >= 0).all(), f"Negative values in {col}"


class TestGroundTruth:
    """Validates the ground truth data."""

    BUSINESS_TYPES = ["restaurant", "cafe", "gym", "pharmacy", "beauty_salon",
                      "store", "school", "lodging", "bar", "night_club"]

    def test_has_viability_columns(self, ground_truth_df):
        for bt in self.BUSINESS_TYPES:
            assert f"{bt}_viability_norm" in ground_truth_df.columns, f"Missing {bt}_viability_norm"

    def test_viability_range(self, ground_truth_df):
        for bt in self.BUSINESS_TYPES:
            col = f"{bt}_viability_norm"
            if col in ground_truth_df.columns:
                assert ground_truth_df[col].between(0, 100).all(), f"{col} out of 0-100 range"

    def test_counts_non_negative(self, ground_truth_df):
        for bt in self.BUSINESS_TYPES:
            col = f"{bt}_count"
            if col in ground_truth_df.columns:
                assert (ground_truth_df[col] >= 0).all(), f"Negative {col}"


class TestFinalDataset:
    """Validates the merged final dataset."""

    def test_has_footfall_columns(self, final_df):
        for col in ['overall_footfall', 'morning_footfall', 'evening_footfall',
                     'office_hr_footfall', 'weekend_footfall']:
            assert col in final_df.columns, f"Missing {col}"

    def test_footfall_range(self, final_df):
        for col in ['overall_footfall', 'morning_footfall', 'evening_footfall']:
            if col in final_df.columns:
                assert final_df[col].between(0, 100).all(), f"{col} out of 0-100 range"

    def test_has_rent_data(self, final_df):
        assert 'est_rent_sqft' in final_df.columns
        assert (final_df['est_rent_sqft'] > 0).all()

    def test_no_all_null_rows(self, final_df):
        numeric = final_df.select_dtypes(include=[np.number])
        all_null_rows = numeric.isnull().all(axis=1).sum()
        assert all_null_rows == 0, f"{all_null_rows} rows with all-null numeric values"


# ═══════════════════════════════════════════════════════════════════════════
# FORMULA TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestViabilityFormula:
    """Tests the viability computation function."""

    def test_zero_count(self):
        from importlib import import_module
        gt = import_module("03_ground_truth")
        assert gt.compute_viability(0, 4.5) == 0.0

    def test_positive_values(self):
        from importlib import import_module
        gt = import_module("03_ground_truth")
        result = gt.compute_viability(10, 4.0)
        expected = 10 * 4.0 * math.log(11)
        assert abs(result - expected) < 0.01

    def test_monotonic_in_count(self):
        from importlib import import_module
        gt = import_module("03_ground_truth")
        v1 = gt.compute_viability(5, 4.0)
        v2 = gt.compute_viability(10, 4.0)
        v3 = gt.compute_viability(20, 4.0)
        assert v1 < v2 < v3, "Viability should increase with count"

    def test_monotonic_in_rating(self):
        from importlib import import_module
        gt = import_module("03_ground_truth")
        v1 = gt.compute_viability(10, 3.0)
        v2 = gt.compute_viability(10, 4.0)
        v3 = gt.compute_viability(10, 5.0)
        assert v1 < v2 < v3, "Viability should increase with rating"


# ═══════════════════════════════════════════════════════════════════════════
# MODEL I/O TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestModelIO:
    """Tests that saved models load correctly and produce valid predictions."""

    MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

    def test_feature_cols_exist(self):
        path = os.path.join(self.MODELS_DIR, "feature_cols.joblib")
        if not os.path.exists(path):
            pytest.skip("feature_cols.joblib not found")
        import joblib
        feature_cols = joblib.load(path)
        assert len(feature_cols) > 0

    def test_models_loadable(self):
        import joblib
        from common import BUSINESS_TYPES, model_path
        loaded = 0
        for bt in BUSINESS_TYPES:
            path = model_path(bt)
            if os.path.exists(path):
                # Safe: models are trained and written locally by scripts/08_model.py
                model = joblib.load(path)
                assert hasattr(model, 'predict'), f"Model for {bt} has no predict method"
                loaded += 1
        assert loaded > 0, "No models could be loaded"

    def test_prediction_shape(self):
        import joblib
        from common import model_path
        fc_path = os.path.join(self.MODELS_DIR, "feature_cols.joblib")
        restaurant_path = model_path("restaurant")
        if not os.path.exists(fc_path) or not os.path.exists(restaurant_path):
            pytest.skip("Model files not found")

        feature_cols = joblib.load(fc_path)
        model = joblib.load(restaurant_path)

        # Create dummy input with correct shape
        X = pd.DataFrame(np.zeros((1, len(feature_cols))), columns=feature_cols)
        preds = model.predict(X)

        assert preds.shape == (1,), f"Expected shape (1,), got {preds.shape}"

    def test_prediction_range(self):
        import joblib
        fc_path = os.path.join(self.MODELS_DIR, "feature_cols.joblib")
        if not os.path.exists(fc_path):
            pytest.skip("feature_cols.joblib not found")

        feature_cols = joblib.load(fc_path)

        from common import model_path
        for bt in ["restaurant", "cafe"]:
            path = model_path(bt)
            if not os.path.exists(path):
                continue
            model = joblib.load(path)
            X = pd.DataFrame(np.random.rand(5, len(feature_cols)) * 100, columns=feature_cols)
            preds = model.predict(X)
            # Predictions should be roughly in 0-100 range (viability scores)
            assert (preds >= -50).all() and (preds <= 200).all(), \
                f"{bt} predictions wildly out of range: {preds}"


class TestModelQuality:
    """Guards against silently shipping models worse than reported."""

    def test_confidence_report(self):
        import json
        path = os.path.join(PROJECT_ROOT, "models", "model_confidence.json")
        if not os.path.exists(path):
            pytest.skip("model_confidence.json not found")
        with open(path) as f:
            conf = json.load(f)
        assert len(conf) > 0
        for bt, c in conf.items():
            assert {'best_model', 'cv_mae', 'baseline_mae', 'beats_baseline'} <= set(c)
            # 0-100 target: MAE above 35 means the model is essentially noise
            assert c['cv_mae'] < 35, f"{bt}: CV MAE {c['cv_mae']} is unusably high"

    def test_footfall_formulas_match_pipeline(self, final_df):
        """common.compute_footfall_scores must reproduce 06_footfall.py output."""
        from common import compute_footfall_scores
        row = final_df.iloc[0]
        scores = compute_footfall_scores(row, final_df)
        for name, val in scores.items():
            assert abs(val - row[name]) < 0.15, f"{name}: {val} != pipeline {row[name]}"


class TestReport:
    """Smoke test: the PDF report builds for a real locality, with and without a scenario."""

    def test_report_builds(self, enriched_df):
        import joblib
        from common import BUSINESS_TYPES, model_path
        from report import build_report

        fc_path = os.path.join(PROJECT_ROOT, "models", "feature_cols.joblib")
        if not os.path.exists(fc_path) or "restaurant_gap" not in enriched_df.columns:
            pytest.skip("models or gap analysis not available")
        import json
        fc = joblib.load(fc_path)
        models = {bt: joblib.load(model_path(bt)) for bt in BUSINESS_TYPES
                  if os.path.exists(model_path(bt))}
        with open(os.path.join(PROJECT_ROOT, "models", "model_confidence.json")) as f:
            confidence = json.load(f)
        with open(os.path.join(PROJECT_ROOT, "models", "gap_report.json")) as f:
            gap_report = json.load(f)
        with open(os.path.join(PROJECT_ROOT, "models", "neighbors.json")) as f:
            neighbors = json.load(f)

        loc = enriched_df.iloc[0]
        x = pd.DataFrame([loc[fc].fillna(0)])
        preds = {bt: float(np.clip(m.predict(x)[0], 0, 99)) for bt, m in models.items()}

        pdf = build_report(loc_data=loc, df=enriched_df, category="cafe", cat_label="Cafe",
                           predictions=preds, confidence=confidence, gap_report=gap_report,
                           neighbors=neighbors, business_types=BUSINESS_TYPES)
        assert pdf[:5] == b"%PDF-" and len(pdf) > 10_000

        sim_state = {"changes": [("offices", 10.0, 30.0)], "sim_predictions": preds}
        pdf2 = build_report(loc_data=loc, df=enriched_df, category="cafe", cat_label="Cafe",
                            predictions=preds, confidence=confidence, gap_report=gap_report,
                            neighbors=neighbors, business_types=BUSINESS_TYPES,
                            sim_state=sim_state)
        assert pdf2[:5] == b"%PDF-" and len(pdf2) > len(pdf) // 2


class TestGapAnalysis:
    """Validates the similarity/gap-analysis layer (step 10)."""

    def test_gap_columns_consistent(self, enriched_df):
        for bt in ["restaurant", "cafe", "gym"]:
            exp, gap, cnt = f"{bt}_expected_count", f"{bt}_gap", f"{bt}_count"
            if exp not in enriched_df.columns:
                pytest.skip("gap analysis not run")
            assert (enriched_df[exp] >= 0).all(), f"negative expected count in {exp}"
            # gap must equal expected - actual (rounding tolerance)
            diff = enriched_df[gap] - (enriched_df[exp] - enriched_df[cnt])
            assert diff.abs().max() < 0.15, f"{gap} inconsistent with {exp} - {cnt}"

    def test_neighbors_exclude_self(self):
        import json
        path = os.path.join(PROJECT_ROOT, "models", "neighbors.json")
        if not os.path.exists(path):
            pytest.skip("neighbors.json not found")
        with open(path) as f:
            neighbors = json.load(f)
        assert len(neighbors) > 0
        for name, peers in neighbors.items():
            assert name not in [p["name"] for p in peers], f"{name} is its own peer"
            assert len(peers) >= 5

    def test_gap_report_beats_baseline_mostly(self):
        import json
        path = os.path.join(PROJECT_ROOT, "models", "gap_report.json")
        if not os.path.exists(path):
            pytest.skip("gap_report.json not found")
        with open(path) as f:
            report = json.load(f)
        n_better = sum(1 for r in report.values() if r["beats_baseline"])
        assert n_better >= len(report) / 2, \
            f"gap analysis beats baseline for only {n_better}/{len(report)} types"


# ═══════════════════════════════════════════════════════════════════════════
# ENRICHMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestEnrichment:
    """Tests the saturation and revenue enrichment layer."""

    def test_saturation_columns_exist(self, enriched_df):
        for bt in ["restaurant", "cafe"]:
            assert f"{bt}_saturation" in enriched_df.columns

    def test_saturation_non_negative(self, enriched_df):
        for bt in ["restaurant", "cafe", "gym"]:
            col = f"{bt}_saturation"
            if col in enriched_df.columns:
                assert (enriched_df[col] >= 0).all(), f"Negative saturation in {col}"

    def test_revenue_columns_exist(self, enriched_df):
        for bt in ["restaurant", "cafe"]:
            assert f"{bt}_est_revenue_lakhs" in enriched_df.columns
            assert f"{bt}_est_rent_cost_lakhs" in enriched_df.columns
            assert f"{bt}_est_roi_pct" in enriched_df.columns

    def test_market_tags_valid(self, enriched_df):
        valid_tags = {'Blue Ocean', 'Saturated', 'Growing', 'Low Demand', 'Unknown'}
        for bt in ["restaurant", "cafe"]:
            col = f"{bt}_market_tag"
            if col in enriched_df.columns:
                actual_tags = set(enriched_df[col].unique())
                assert actual_tags.issubset(valid_tags), f"Invalid tags in {col}: {actual_tags - valid_tags}"


# ═══════════════════════════════════════════════════════════════════════════
# REPRODUCIBILITY TEST
# ═══════════════════════════════════════════════════════════════════════════

class TestReproducibility:
    """Ensures the synthetic data fallback is deterministic."""

    def test_dummy_data_deterministic(self):
        import random
        from importlib import import_module
        gt = import_module("03_ground_truth")

        random.seed(42)
        r1 = gt.get_dummy_data("South Mumbai", "restaurant")
        random.seed(42)
        r2 = gt.get_dummy_data("South Mumbai", "restaurant")
        assert r1 == r2, "Dummy data not deterministic with same seed"
