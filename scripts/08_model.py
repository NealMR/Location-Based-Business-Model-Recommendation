"""
08_model.py
-----------
Trains and evaluates ML models to predict business viability (success %).

Key improvements over the original:
  1. Spatial cross-validation (GroupKFold by zone) - prevents geographic leakage
  2. sklearn Pipeline encapsulation - normalisation fitted on train folds only
  3. Multiple model comparison (RF, XGBoost, zone-mean baseline)
  4. SHAP explainability - global + per-prediction feature attribution
  5. Confidence intervals via cross-fold statistics
  6. Comprehensive metrics reporting

Output: models/*.joblib, models/metrics_report.csv, models/shap_summary.png
"""

import os
import json
import warnings
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, RegressorMixin
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore', category=FutureWarning)

try:
    import shap
except ImportError:
    shap = None

try:
    import seaborn as sns
except ImportError:
    sns = None

from common import BUSINESS_TYPES, model_path

N_FOLDS = 5  # Spatial CV folds (we have 6 zones, so 5-fold works well)


class ZoneMeanBaseline(BaseEstimator, RegressorMixin):
    """Predicts the zone-level mean viability. Used as a sanity-check baseline."""
    def __init__(self):
        self.zone_means_ = {}
        self.global_mean_ = 0.0

    def fit(self, X, y, groups=None):
        self.global_mean_ = y.mean()
        if groups is not None:
            df = pd.DataFrame({'y': y, 'zone': groups})
            self.zone_means_ = df.groupby('zone')['y'].mean().to_dict()
        return self

    def predict(self, X, groups=None):
        if groups is not None:
            return np.array([self.zone_means_.get(z, self.global_mean_) for z in groups])
        return np.full(len(X), self.global_mean_)


def get_feature_columns(df):
    """Determine feature columns, excluding targets, identifiers, and leak-prone columns."""
    exclude_cols = {'name', 'ward', 'zone', 'rent_tier', 'cluster_label',
                    'cluster_id', 'lat', 'lng'}
    viability_cols = {c for c in df.columns if 'viability' in c}
    count_cols = {c for c in df.columns if c.endswith('_count')}
    rating_cols = {c for c in df.columns if c.endswith('_rating')}
    # existing_* are the same OSM business counts as the target at a different
    # radius (same-source leakage); norm_* are duplicates of raw columns
    # normalized over the FULL dataset before the CV split (leaks across folds).
    leak_cols = {c for c in df.columns if c.startswith('existing_') or c.startswith('norm_')}

    drop_cols = exclude_cols | viability_cols | count_cols | rating_cols | leak_cols
    feature_cols = [c for c in df.columns if c not in drop_cols]
    return feature_cols


def spatial_cv_evaluate(X, y, groups, model_factory, model_name, n_folds=N_FOLDS):
    """
    Runs GroupKFold spatial cross-validation.
    Returns per-fold metrics and the model trained on all data.
    """
    gkf = GroupKFold(n_splits=n_folds)
    fold_metrics = []
    oof_preds = np.full(len(y), np.nan)

    for fold_idx, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model = model_factory()
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        preds = np.clip(preds, 0, 100)

        oof_preds[test_idx] = preds

        mae = mean_absolute_error(y_test, preds)
        r2 = r2_score(y_test, preds) if len(y_test) > 1 else 0.0

        fold_metrics.append({
            'fold': fold_idx + 1,
            'model': model_name,
            'mae': round(mae, 2),
            'r2': round(r2, 3),
            'test_zone': list(groups.iloc[test_idx].unique()),
            'n_test': len(test_idx),
        })

    # Train final model on all data
    final_model = model_factory()
    final_model.fit(X, y)

    return final_model, fold_metrics, oof_preds


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_path = os.path.join(project_root, "data", "processed", "final_dataset.csv")
    models_dir = os.path.join(project_root, "models")

    os.makedirs(models_dir, exist_ok=True)

    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    print("Loading final dataset...")
    df = pd.read_csv(input_path)

    feature_cols = get_feature_columns(df)
    X = df[feature_cols].fillna(0)
    groups = df['zone']

    print(f"Using {len(feature_cols)} features for training.")
    print(f"Spatial CV groups (zones): {groups.nunique()} unique zones")
    print(f"Dataset size: {len(df)} localities")

    # -- Model factories --------------------------------------------------
    def baseline_factory():
        # Fit without groups -> predicts the train-fold global mean.
        # This is the honest baseline for a zone never seen in training.
        return ZoneMeanBaseline()

    def ridge_factory():
        return Pipeline([
            ('scaler', StandardScaler()),
            ('model', Ridge(alpha=10.0))
        ])

    def rf_factory():
        return Pipeline([
            ('scaler', StandardScaler()),
            ('model', RandomForestRegressor(n_estimators=200, max_depth=10,
                                            min_samples_leaf=3, random_state=42))
        ])

    def gb_factory():
        return Pipeline([
            ('scaler', StandardScaler()),
            ('model', GradientBoostingRegressor(n_estimators=200, max_depth=5,
                                                 learning_rate=0.05,
                                                 min_samples_leaf=3, random_state=42))
        ])

    # -- Per-business-type training ---------------------------------------
    all_metrics = []
    importance_dict = {}
    best_models = {}
    shap_data = {}
    confidence_report = {}

    print("\n" + "=" * 70)
    print("  SPATIAL CROSS-VALIDATION RESULTS (GroupKFold by Zone)")
    print("=" * 70)

    for bt in BUSINESS_TYPES:
        target_col = f"{bt}_viability_norm"
        if target_col not in df.columns:
            print(f"Skipping {bt}: target column not found.")
            continue

        y = df[target_col].fillna(0)

        print(f"\n{'-' * 50}")
        print(f"  {bt.upper()}")
        print(f"{'-' * 50}")

        # All candidates (baseline included) evaluated under the SAME
        # GroupKFold protocol so their scores are comparable.
        candidates = [
            ('MeanBaseline', baseline_factory),
            ('Ridge', ridge_factory),
            ('RandomForest', rf_factory),
            ('GradientBoosting', gb_factory),
        ]

        results = {}
        for model_name, factory in candidates:
            fitted, folds, _ = spatial_cv_evaluate(X, y, groups, factory, model_name)
            mae = np.mean([f['mae'] for f in folds])
            r2 = np.mean([f['r2'] for f in folds])
            mae_std = np.std([f['mae'] for f in folds])
            r2_std = np.std([f['r2'] for f in folds])
            results[model_name] = {'model': fitted, 'mae': mae, 'mae_std': mae_std}
            print(f"  {model_name:<18} | MAE: {mae:.2f} +/- {mae_std:.2f} | R2: {r2:.3f} +/- {r2_std:.3f}")
            all_metrics.append({
                'business_type': bt, 'model': model_name,
                'mae_mean': round(mae, 2), 'r2_mean': round(r2, 3),
                'mae_std': round(mae_std, 2), 'r2_std': round(r2_std, 3)
            })
            all_metrics.extend(folds)

        # --- Pick best LEARNED model (baseline excluded from deployment,
        # but flagged if it wins so the UI can communicate low confidence) ---
        learned = {k: v for k, v in results.items() if k != 'MeanBaseline'}
        best_name = min(learned, key=lambda k: learned[k]['mae'])
        best_model = learned[best_name]['model']
        beats_baseline = learned[best_name]['mae'] < results['MeanBaseline']['mae']
        status = "beats baseline" if beats_baseline else "DOES NOT beat baseline - treat scores as low-confidence"
        print(f"  [OK] Best learned model: {best_name} ({status})")

        confidence_report[bt] = {
            'best_model': best_name,
            'cv_mae': round(learned[best_name]['mae'], 2),
            'cv_mae_std': round(learned[best_name]['mae_std'], 2),
            'baseline_mae': round(results['MeanBaseline']['mae'], 2),
            'beats_baseline': bool(beats_baseline),
        }

        best_models[bt] = best_model
        # Name records nothing false: algorithm is in model_confidence.json
        joblib.dump(best_model, model_path(bt))

        # --- Feature importance (from the underlying estimator) ---
        underlying = best_model.named_steps['model']
        if hasattr(underlying, 'feature_importances_'):
            importances = pd.Series(underlying.feature_importances_, index=X.columns)
            importance_dict[bt] = importances.sort_values(ascending=False)
        elif hasattr(underlying, 'coef_'):
            importances = pd.Series(np.abs(underlying.coef_), index=X.columns)
            importance_dict[bt] = importances.sort_values(ascending=False)

        # --- SHAP (tree models only; Ridge coefficients are already interpretable) ---
        if shap is not None and hasattr(underlying, 'feature_importances_'):
            try:
                X_scaled = best_model.named_steps['scaler'].transform(X)
                X_shap = pd.DataFrame(X_scaled, columns=X.columns)
                explainer = shap.TreeExplainer(underlying)
                sv = explainer.shap_values(X_shap)
                shap_data[bt] = {
                    'shap_values': sv,
                    'X': X_shap,
                    'explainer': explainer,
                }
            except Exception as e:
                print(f"  SHAP computation skipped: {e}")

    # -- Save feature columns ---------------------------------------------
    joblib.dump(feature_cols, os.path.join(models_dir, "feature_cols.joblib"))

    # -- Save per-type confidence report (consumed by the dashboard) -------
    conf_path = os.path.join(models_dir, "model_confidence.json")
    with open(conf_path, 'w') as f:
        json.dump(confidence_report, f, indent=2)
    print(f"[OK] Confidence report saved to: {conf_path}")

    # -- Save metrics report ----------------------------------------------
    metrics_df = pd.DataFrame(all_metrics)
    metrics_path = os.path.join(models_dir, "metrics_report.csv")
    metrics_df.to_csv(metrics_path, index=False)
    print(f"\n[OK] Metrics report saved to: {metrics_path}")

    # -- Feature importance heatmap ---------------------------------------
    if importance_dict and sns is not None:
        try:
            print("Generating feature importance heatmap...")
            imp_df = pd.DataFrame(importance_dict).T
            plt.figure(figsize=(14, 8))
            sns.heatmap(imp_df, cmap="YlGnBu", xticklabels=True, yticklabels=True)
            plt.title("Feature Importance by Business Type (Best Model)")
            plt.tight_layout()
            heatmap_path = os.path.join(models_dir, "feature_importance.png")
            plt.savefig(heatmap_path, dpi=150)
            plt.close()
            print(f"[OK] Heatmap saved to: {heatmap_path}")
        except Exception as e:
            print(f"Could not generate heatmap: {e}")

    # -- SHAP summary plots -----------------------------------------------
    if shap is not None and shap_data:
        print("Generating SHAP summary plots...")
        n_plots = len(shap_data)
        fig, axes = plt.subplots(1, min(n_plots, 5), figsize=(6 * min(n_plots, 5), 6))
        if n_plots == 1:
            axes = [axes]

        for ax, (bt, sd) in zip(axes, list(shap_data.items())[:5]):
            plt.sca(ax)
            shap.summary_plot(sd['shap_values'], sd['X'], plot_type="bar",
                              show=False, max_display=10)
            ax.set_title(bt.replace('_', ' ').title())

        plt.tight_layout()
        shap_path = os.path.join(models_dir, "shap_summary.png")
        plt.savefig(shap_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[OK] SHAP summary saved to: {shap_path}")

        # Save SHAP values for dashboard use
        shap_values_dict = {}
        for bt, sd in shap_data.items():
            shap_values_dict[bt] = {
                'mean_abs_shap': pd.Series(
                    np.abs(sd['shap_values']).mean(axis=0),
                    index=sd['X'].columns
                ).sort_values(ascending=False).head(10).to_dict()
            }
        shap_json_path = os.path.join(models_dir, "shap_importance.json")
        with open(shap_json_path, 'w') as f:
            json.dump(shap_values_dict, f, indent=2)
        print(f"[OK] SHAP importance JSON saved to: {shap_json_path}")

    # -- Summary ----------------------------------------------------------
    print("\n" + "=" * 70)
    print("  MODEL COMPARISON SUMMARY")
    print("=" * 70)

    # Filter to only aggregate rows (those with mae_mean, not per-fold rows)
    agg_mask = metrics_df['mae_mean'].notna() if 'mae_mean' in metrics_df.columns else pd.Series([True] * len(metrics_df))
    if 'fold' in metrics_df.columns:
        agg_mask = agg_mask & metrics_df['fold'].isna()

    agg_df = metrics_df[agg_mask]

    for bt in BUSINESS_TYPES:
        bt_rows = agg_df[agg_df['business_type'] == bt]
        if bt_rows.empty:
            continue
        print(f"\n  {bt.upper()}:")
        for _, row in bt_rows.iterrows():
            model_name = row.get('model', '?')
            mae = row.get('mae_mean', 0)
            r2 = row.get('r2_mean', 0)
            mae_std = row.get('mae_std', 0)
            r2_std = row.get('r2_std', 0)
            if mae_std > 0:
                print(f"    {model_name:<20} MAE: {mae:.2f} +/- {mae_std:.2f}  R2: {r2:.3f} +/- {r2_std:.3f}")
            else:
                print(f"    {model_name:<20} MAE: {mae:.2f}              R2: {r2:.3f}")

    print("\n" + "-" * 50)
    print(f"[OK] Step 8 complete - pipeline finished")
    print(f"Models saved to: {models_dir}")


if __name__ == "__main__":
    main()
