"""RailTwin-X LightGBM Quantile Training & Split-Conformal Calibration Engine.

Trains 6 LightGBM estimators (Direct & Delta for p10, p50, p90) with strict time split
and computes Conformalized Quantile Regression (CQR) adjustment parameters.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Dict, Tuple, Optional
import lightgbm as lgb
import numpy as np
import pandas as pd

from config import settings
from data.db import Database, get_db
from ml.features import FEATURE_NAMES
from ml.snapshots import SnapshotGenerator


class ModelTrainer:
    """Orchestrates training of the 6 LightGBM quantile models and conformal calibration."""

    def __init__(self, db: Optional[Database] = None, artifacts_dir: Optional[Path] = None):
        self.db = db or get_db()
        self.artifacts_dir = artifacts_dir or settings.ARTIFACTS_DIR
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_gen = SnapshotGenerator(self.db)


    def prepare_datasets(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Loads and splits snapshot data into TRAIN (full archive) and TEST sets.

        F25 FIX: Uses FULL archive from MIN(run_date) to train_cutoff instead of
        the previous 21-day cap. Streaming per-day (DaySpatialIndex) keeps memory flat.
        ESS printed for transparency.
        """
        with self.db.transaction() as cur:
            cur.execute("SELECT MIN(run_date) as min_date, MAX(run_date) as max_date FROM station_events")
            row = cur.fetchone()

        if row and row["max_date"] and row["min_date"]:
            max_d = datetime.date.fromisoformat(row["max_date"])
            min_db_d = datetime.date.fromisoformat(row["min_date"])

            test_len = settings.ML_TEST_DAYS
            # F25 FIX: train uses FULL archive from first event to cutoff
            test_start_d = max_d - datetime.timedelta(days=test_len - 1)
            train_cutoff_d = test_start_d - datetime.timedelta(days=1)
            start_date_d = min_db_d   # <-- was: train_cutoff - 21 days; now: full archive

            start_date = start_date_d.strftime("%Y-%m-%d")
            train_cutoff = train_cutoff_d.strftime("%Y-%m-%d")
            test_start = test_start_d.strftime("%Y-%m-%d")
            test_end = max_d.strftime("%Y-%m-%d")

            span_days = (train_cutoff_d - start_date_d).days + 1
            span_months = round(span_days / 30.44, 1)
            print(f"[F25] Training span: {start_date} -> {train_cutoff} = {span_days} days ({span_months} months)")
        else:
            today = datetime.date.today()
            start_date = (today - datetime.timedelta(days=settings.ML_TRAIN_DAYS + settings.ML_TEST_DAYS)).strftime("%Y-%m-%d")
            train_cutoff = (today - datetime.timedelta(days=settings.ML_TEST_DAYS + 1)).strftime("%Y-%m-%d")
            test_start = (today - datetime.timedelta(days=settings.ML_TEST_DAYS)).strftime("%Y-%m-%d")
            test_end = today.strftime("%Y-%m-%d")

        print(f"[INFO] Dynamic time-based split: TRAIN [{start_date} to {train_cutoff}], TEST [{test_start} to {test_end}]")

        self.split_info = {
            "start_date": start_date,
            "train_cutoff": train_cutoff,
            "test_start": test_start,
            "test_end": test_end,
        }

        train_df = self.snapshot_gen.build_dataset(start_date, train_cutoff, train_cutoff)
        test_df = self.snapshot_gen.build_dataset(test_start, test_end, train_cutoff)

        # F25: Compute and print Effective Sample Size (λ=0.0077, half-life=90d)
        if "sample_weight" in train_df.columns:
            w = train_df["sample_weight"].values
            ess = float((w.sum() ** 2) / (w ** 2).sum())
            print(f"[F25] ESS (half-life=90d, span={span_days if 'span_days' in dir() else '?'}d): {ess:,.0f}")
        else:
            print("[F25] sample_weight column missing - ESS not computed")

        print(f"[F25] Training rows: {len(train_df):,}  (expect >>88,200 with full archive)")
        span_actual = (datetime.date.fromisoformat(train_cutoff) - datetime.date.fromisoformat(start_date)).days
        print(f"[F25] Span check: {span_actual} days >= 90? {'PASS' if span_actual >= 90 else 'FAIL'}")

        return train_df, test_df

    def train_quantile_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        alpha: float,
        model_name: str,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        sample_weights: Optional[np.ndarray] = None,
        is_delta: bool = False,
    ) -> lgb.Booster:
        """Trains a single LightGBM regressor with pinball quantile loss.

        TASK-6a: Delta models use stronger regularization (lambda_l2=1.0, min_data_in_leaf=80)
        to handle noisy section-level increments at long horizons.
        """
        print(f"[INFO] Training LightGBM Booster: {model_name} (alpha={alpha}, is_delta={is_delta})...")

        train_data = lgb.Dataset(
            X_train[FEATURE_NAMES],
            label=y_train,
            weight=sample_weights,
        )

        params = {
            "objective": "quantile",
            "alpha": alpha,
            "num_leaves": settings.LGBM_NUM_LEAVES,
            "learning_rate": settings.LGBM_LEARNING_RATE,
            "min_child_samples": settings.LGBM_MIN_CHILD_SAMPLES,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "verbosity": -1,
            "force_col_wise": True,
        }
        if is_delta:
            # TASK-6a: Delta model Huber-tolerant params
            # Higher regularization to combat long-horizon label noise
            params["lambda_l2"] = 1.0
            params["min_child_samples"] = 80
            params["min_data_in_leaf"] = 80

        valid_sets = [train_data]
        callbacks = []
        if X_val is not None and y_val is not None and len(X_val) > 0:
            val_data = lgb.Dataset(X_val[FEATURE_NAMES], label=y_val, reference=train_data)
            valid_sets.append(val_data)
            callbacks.append(lgb.early_stopping(stopping_rounds=50, verbose=False))

        booster = lgb.train(
            params,
            train_data,
            valid_sets=valid_sets if len(valid_sets) > 1 else None,
            num_boost_round=settings.LGBM_N_ESTIMATORS,
            callbacks=callbacks if callbacks else None,
        )

        model_path = self.artifacts_dir / f"{model_name}.txt"
        booster.save_model(str(model_path))
        print(f"[SUCCESS] Saved booster to {model_path} (best iteration: {booster.best_iteration})")
        return booster

    def compute_conformal_calibration(
        self,
        models: Dict[float, lgb.Booster],
        X_calib: pd.DataFrame,
        y_calib: pd.Series,
        alpha_coverage: float = settings.CONFORMAL_MISCOVERAGE_ALPHA,
        model_type: str = "direct",
    ) -> Dict[str, float]:
        """Computes Mondrian CQR non-conformity score adjustments partitioned by horizon (F03).

        TASK-5a fix: (1) Use correct MondrianCQR group key names ('short_1h', 'medium_3h',
        'long_6h'); (2) Use full km range in calibration (don't filter to direct hops only)
        so the long_6h Mondrian cell receives actual >250km rows.
        """
        from ml.conformal import MondrianCQR

        print(f"[INFO] Computing Mondrian Conformal CQR calibration for {model_type} (target coverage: {(1-alpha_coverage)*100:.0f}%)...")
        q_lo_pred = models[0.1].predict(X_calib[FEATURE_NAMES])
        q_hi_pred = models[0.9].predict(X_calib[FEATURE_NAMES])
        y_actual = y_calib.values

        hops_arr = X_calib["hops_remaining"].values if "hops_remaining" in X_calib.columns else np.ones(len(y_actual))
        km_arr   = X_calib["km_remaining"].values   if "km_remaining"   in X_calib.columns else np.zeros(len(y_actual))

        mondrian = MondrianCQR(target_coverage=1.0 - alpha_coverage)
        bucket_q_hats = mondrian.calibrate(q_lo_pred, q_hi_pred, y_actual, hops_arr, km_arr)

        # TASK-5a fix: use correct key names matching MondrianCQR._get_group_key()
        # Keys are 'short_1h', 'medium_3h', 'long_6h' (set in _get_group_key)
        glob = bucket_q_hats.get("global", 2.0)
        bucket_q_hats["1h"] = bucket_q_hats.get("short_1h", glob)
        bucket_q_hats["3h"] = bucket_q_hats.get("medium_3h", glob)
        bucket_q_hats["6h"] = bucket_q_hats.get("long_6h", glob)

        # Log Mondrian cell counts for verification
        for cell_key in ["short_1h", "medium_3h", "long_6h"]:
            q = bucket_q_hats.get(cell_key, glob)
            mask = None
            if cell_key == "short_1h":
                mask = km_arr <= 90
            elif cell_key == "medium_3h":
                mask = (km_arr > 90) & (km_arr <= 250)
            else:
                mask = km_arr > 250
            n_cell = int(np.sum(mask)) if mask is not None else 0
            print(f"  [MONDRIAN] {cell_key}: n={n_cell:,}  q_hat={q:.4f}")

        print(f"[SUCCESS] Conformal adjustment factors for {model_type}: 1h={bucket_q_hats['1h']:.4f}  3h={bucket_q_hats['3h']:.4f}  6h={bucket_q_hats['6h']:.4f}")
        return bucket_q_hats


    def train_all(self) -> dict:
        """Executes end-to-end training pipeline for all 6 models + calibration + baselines."""
        import joblib
        train_df, test_df = self.prepare_datasets()

        # Split train into training core (80%) and calibration/validation tail (20%)
        calib_cutoff = int(len(train_df) * 0.8)
        train_core = train_df.iloc[:calib_cutoff].copy()
        train_calib = train_df.iloc[calib_cutoff:].copy()

        # F25: Time-decay weighted training archive (half-life = 90 days, lambda = 0.0077)
        if "run_date" in train_core.columns:
            max_d = pd.to_datetime(train_core["run_date"]).max()
            days_diff = (max_d - pd.to_datetime(train_core["run_date"])).dt.days.values
            direct_weights = np.exp(-0.0077 * days_diff)
        else:
            direct_weights = None

        # Filter direct model data (hops <= DIRECT_MODEL_MAX_HOPS)
        direct_mask = train_core["hops_remaining"] <= settings.DIRECT_MODEL_MAX_HOPS
        direct_train = train_core[direct_mask].copy()
        direct_train_weights = direct_weights[direct_mask] if direct_weights is not None else None
        direct_calib = train_calib[train_calib["hops_remaining"] <= settings.DIRECT_MODEL_MAX_HOPS].copy()

        # Tail-Safety Oversampling for target_direct_delay > 120 (3x)
        extreme_mask = direct_train["target_direct_delay"] > 120
        if extreme_mask.any():
            extreme_rows = direct_train[extreme_mask]
            direct_train = pd.concat([direct_train, extreme_rows, extreme_rows], ignore_index=True)
            if direct_train_weights is not None:
                extreme_w = direct_train_weights[extreme_mask]
                direct_train_weights = np.concatenate([direct_train_weights, extreme_w, extreme_w])
            print(f"[INFO] Tail-Safety: Oversampled {len(extreme_rows)} rows with delay > 120m by 3x (total direct train: {len(direct_train):,} rows)")


        # 1. Train 3 DIRECT models (q=0.1, 0.5, 0.9) with early stopping
        direct_models = {}
        for q in settings.QUANTILE_ALPHAS:
            name = f"model_direct_q{int(q*100)}"
            direct_models[q] = self.train_quantile_model(
                direct_train, direct_train["target_direct_delay"], q, name,
                X_val=direct_calib, y_val=direct_calib["target_direct_delay"]
            )

        # 2. Train 3 DELTA models (q=0.1, 0.5, 0.9) with stronger regularization (TASK-6a)
        delta_models = {}
        for q in settings.QUANTILE_ALPHAS:
            name = f"model_delta_q{int(q*100)}"
            delta_models[q] = self.train_quantile_model(
                train_core, train_core["target_section_delta"], q, name,
                X_val=train_calib, y_val=train_calib["target_section_delta"],
                is_delta=True,  # TASK-6a: use robust delta hyperparams
            )

        # 3. Conformal Calibration (TASK-5a fix: use train_calib for direct models too,
        #    so all 3 Mondrian horizon cells get rows. direct_calib only has hops<=3
        #    which means km<90 only, leaving long_6h cell empty and q_hat=global fallback)
        calib_direct = self.compute_conformal_calibration(
            direct_models, train_calib, train_calib["target_direct_delay"],
            model_type="direct"
        )
        calib_delta = self.compute_conformal_calibration(
            delta_models, train_calib, train_calib["target_section_delta"],
            model_type="delta"
        )


        # 4. Feature Importance Analysis (Gain and Split)
        importance_gain = direct_models[0.5].feature_importance(importance_type="gain")
        total_gain = max(1e-6, sum(importance_gain))
        feat_importance_dict = {
            f: float(g / total_gain * 100.0)
            for f, g in zip(FEATURE_NAMES, importance_gain)
        }

        # 5. Baseline B3: Scikit-learn Linear Regression on direct training set & Persist benchmark
        from sklearn.linear_model import LinearRegression
        lr_model = LinearRegression()
        lr_model.fit(train_core[FEATURE_NAMES], train_core["target_direct_delay"])
        lr_bench_path = self.artifacts_dir / "model_lr_benchmark.pkl"
        joblib.dump(lr_model, lr_bench_path)
        print(f"[SUCCESS] Persisted linear regression benchmark to {lr_bench_path}")

        lr_calib_pred = lr_model.predict(direct_calib[FEATURE_NAMES])
        b3_calib_mae = float(np.mean(np.abs(direct_calib["target_direct_delay"].values - lr_calib_pred)))

        manifest = {
            "trained_at": datetime.datetime.now().isoformat(),
            "train_rows": len(train_df),
            "test_rows": len(test_df),
            "split_info": getattr(self, "split_info", {}),
            "direct_model_max_hops": settings.DIRECT_MODEL_MAX_HOPS,
            "quantiles": settings.QUANTILE_ALPHAS,
            "conformal_q_hat": calib_direct["global"],
            "conformal_q_hat_direct": calib_direct["global"],
            "conformal_q_hat_direct_1h": calib_direct["1h"],
            "conformal_q_hat_direct_3h": calib_direct["3h"],
            "conformal_q_hat_direct_6h": calib_direct["6h"],
            "conformal_q_hat_delta": calib_delta["global"],
            "conformal_q_hat_delta_1h": calib_delta["1h"],
            "conformal_q_hat_delta_3h": calib_delta["3h"],
            "conformal_q_hat_delta_6h": calib_delta["6h"],
            "target_coverage": 1.0 - settings.CONFORMAL_MISCOVERAGE_ALPHA,
            "features": FEATURE_NAMES,
            "feature_importance_gain_pct": feat_importance_dict,
            "b3_linear_regression_calib_mae": round(b3_calib_mae, 2),
        }

        manifest_path = self.artifacts_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        print(f"[SUCCESS] All 6 models + calibration manifest saved in {self.artifacts_dir}")
        return manifest


if __name__ == "__main__":
    print("=== RailTwin-X Quantile Model Training ===")
    trainer = ModelTrainer()
    res = trainer.train_all()
    print("Training summary:", res)

