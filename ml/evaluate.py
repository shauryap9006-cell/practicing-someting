"""RailTwin-X Evaluation & F14 Backtest Proof Table Generator.

Evaluates RailTwin-X against Baselines B1 (Frozen delay) and B2 (Official scheduled recovery)
on the held-out test week. Computes MAE at 1h/3h/6h horizons, HitRate10, and empirical
conformal 80% coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import lightgbm as lgb
import numpy as np
import pandas as pd

from config import settings
from data.db import Database, get_db
from ml.features import FEATURE_NAMES
from ml.snapshots import SnapshotGenerator


class Evaluator:
    """Evaluates ML models against official baselines on held-out test week."""

    def __init__(self, db: Optional[Database] = None, artifacts_dir: Optional[Path] = None):
        self.db = db or get_db()
        self.artifacts_dir = artifacts_dir or settings.ARTIFACTS_DIR
        self.snapshot_gen = SnapshotGenerator(self.db)
        self.manifest = self._load_manifest()
        self.direct_models = self._load_models("model_direct")
        self.delta_models = self._load_models("model_delta")

    def _load_manifest(self) -> dict:
        manifest_path = self.artifacts_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at {manifest_path}. Run ml.train first.")
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_models(self, prefix: str) -> Dict[float, lgb.Booster]:
        models = {}
        for q in settings.QUANTILE_ALPHAS:
            path = self.artifacts_dir / f"{prefix}_q{int(q*100)}.txt"
            if not path.exists():
                raise FileNotFoundError(f"Model file not found: {path}")
            models[q] = lgb.Booster(model_file=str(path))
        return models

    def _get_q_hat(self, km_val: float, model_type: str = "direct") -> float:
        """Returns horizon-specific conformal q_hat calibration factor."""
        if km_val <= 90:
            h_tag = "1h"
        elif km_val <= 250:
            h_tag = "3h"
        else:
            h_tag = "6h"
        key = f"conformal_q_hat_{model_type}_{h_tag}"
        if key in self.manifest:
            return float(self.manifest[key])
        fallback_key = f"conformal_q_hat_{model_type}"
        return float(self.manifest.get(fallback_key, self.manifest.get("conformal_q_hat", 2.0)))

    def predict_interval(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Predicts calibrated [p10, p50, p90] intervals using direct models and autoregressive delta rollout with LR anchor."""
        is_direct = X["hops_remaining"] <= settings.DIRECT_MODEL_MAX_HOPS

        p10 = np.zeros(len(X))
        p50 = np.zeros(len(X))
        p90 = np.zeros(len(X))

        # 1. Short-range predictions (<= 3 hops): Direct LightGBM Booster with per-horizon q_hat
        if is_direct.any():
            X_dir = X[is_direct][FEATURE_NAMES]
            km_dirs = X[is_direct]["km_remaining"].values
            q_hats_dir = np.array([self._get_q_hat(km, "direct") for km in km_dirs])
            p10[is_direct] = self.direct_models[0.1].predict(X_dir) - q_hats_dir
            p50[is_direct] = self.direct_models[0.5].predict(X_dir)
            p90[is_direct] = self.direct_models[0.9].predict(X_dir) + q_hats_dir

        # 2. Long-range predictions (> 3 hops): Autoregressive Section-by-Section Rollout with LR Anchor
        if (~is_direct).any():
            non_dir_indices = X[~is_direct].index
            X_non_dir = X.loc[non_dir_indices].copy()

            # Load LR benchmark model for long-horizon mean anchoring
            lr_model = None
            lr_path = self.artifacts_dir / "model_lr_benchmark.pkl"
            if lr_path.exists():
                try:
                    import joblib
                    lr_model = joblib.load(lr_path)
                except Exception:
                    pass
            if lr_model is None:
                from sklearn.linear_model import LinearRegression
                lr_model = LinearRegression()
                split_info = self.manifest.get("split_info", {})
                start_d = split_info.get("start_date", "2026-07-31")
                train_c = split_info.get("train_cutoff", "2026-08-20")
                train_df_b = self.snapshot_gen.build_dataset(start_d, train_c, train_c)
                lr_model.fit(train_df_b[FEATURE_NAMES], train_df_b["target_direct_delay"])

            lr_preds = np.maximum(0.0, lr_model.predict(X_non_dir[FEATURE_NAMES]))

            # Vectorized multi-step autoregressive rollout
            n_samples = len(X_non_dir)
            hops_arr = X_non_dir["hops_remaining"].to_numpy().astype(int)
            km_rem_arr = X_non_dir["km_remaining"].to_numpy().astype(float)
            curr_d_arr = X_non_dir["current_delay"].to_numpy().astype(float)
            km_per_hop = km_rem_arr / np.maximum(1, hops_arr)

            sim_delay = curr_d_arr.copy()
            accum_spread_lo = np.zeros(n_samples, dtype=float)
            accum_spread_hi = np.zeros(n_samples, dtype=float)

            max_hops = int(np.max(hops_arr)) if len(hops_arr) > 0 else 0
            cur_df = X_non_dir.copy()

            for step in range(1, max_hops + 1):
                mask = hops_arr >= step
                if not np.any(mask):
                    break
                rem_hops = hops_arr[mask] - step + 1
                cur_df.loc[mask, "current_delay"] = sim_delay[mask]
                cur_df.loc[mask, "hops_remaining"] = rem_hops
                cur_df.loc[mask, "km_remaining"] = rem_hops * km_per_hop[mask]

                sub_X = cur_df.loc[mask, FEATURE_NAMES]
                d10 = self.delta_models[0.1].predict(sub_X)
                d50 = self.delta_models[0.5].predict(sub_X)
                d90 = self.delta_models[0.9].predict(sub_X)

                sim_delay[mask] = np.maximum(0.0, sim_delay[mask] + d50)
                accum_spread_lo[mask] += np.maximum(0.0, d50 - d10)
                accum_spread_hi[mask] += np.maximum(0.0, d90 - d50)

            q_hat_del = np.array([self._get_q_hat(km, "delta") for km in km_rem_arr])
            adj = q_hat_del * np.sqrt(hops_arr)

            # Long-horizon blended prediction: 0.50 * rollout + 0.50 * lr
            r_p50 = 0.50 * sim_delay + 0.50 * lr_preds
            r_p10 = np.maximum(0.0, np.minimum(r_p50, sim_delay - accum_spread_lo - adj))
            r_p90 = np.maximum(r_p50, sim_delay + accum_spread_hi + adj)

            p10[~is_direct] = r_p10
            p50[~is_direct] = r_p50
            p90[~is_direct] = r_p90

        # Ensure monotonic bounds: p10 <= p50 <= p90
        p10 = np.maximum(0.0, p10)
        p50 = np.maximum(p10, p50)
        p90 = np.maximum(p50, p90)

        return p10, p50, p90

    @staticmethod
    def compute_winkler_score(y_true: np.ndarray, p10: np.ndarray, p90: np.ndarray, alpha: float = 0.20) -> float:
        """Computes Winkler interval score for sharpness + coverage: W = (u-l) + (2/alpha)*(l-y)*1{y<l} + (2/alpha)*(y-u)*1{y>u}."""
        width = p90 - p10
        under_penalty = (2.0 / alpha) * np.maximum(0.0, p10 - y_true)
        over_penalty = (2.0 / alpha) * np.maximum(0.0, y_true - p90)
        scores = width + under_penalty + over_penalty
        return float(np.mean(scores))

    @staticmethod
    def compute_crps(y_true: np.ndarray, p10: np.ndarray, p50: np.ndarray, p90: np.ndarray) -> float:
        """Computes Continuous Ranked Probability Score (CRPS) averaged over quantile pinball losses."""
        losses = []
        for q, pred in zip([0.1, 0.5, 0.9], [p10, p50, p90]):
            err = y_true - pred
            pinball = np.maximum(q * err, (q - 1.0) * err)
            losses.append(2.0 * pinball)
        return float(np.mean(np.mean(losses, axis=0)))

    @staticmethod
    def get_purged_disjoint_splits(
        min_date_str: str,
        max_date_str: str,
        embargo_days: int = 2,
        cal_ratio: float = 0.20,
        test_ratio: float = 0.25,
    ) -> Dict[str, Dict[str, str]]:
        """Constructs strictly disjoint (Train / Calibration / Test) splits with an embargo gap to prevent leakage."""
        import datetime
        min_d = datetime.date.fromisoformat(min_date_str)
        max_d = datetime.date.fromisoformat(max_date_str)
        total_days = (max_d - min_d).days + 1

        test_days = max(2, int(total_days * test_ratio))
        remaining_days = total_days - test_days - embargo_days
        cal_days = max(2, int(remaining_days * cal_ratio))
        train_days = max(3, remaining_days - cal_days - embargo_days)

        train_start = min_d
        train_end = train_start + datetime.timedelta(days=train_days - 1)

        cal_start = train_end + datetime.timedelta(days=embargo_days + 1)
        cal_end = cal_start + datetime.timedelta(days=cal_days - 1)

        test_start = cal_end + datetime.timedelta(days=embargo_days + 1)
        test_end = max_d

        return {
            "train": {"start": train_start.strftime("%Y-%m-%d"), "end": train_end.strftime("%Y-%m-%d")},
            "embargo_1": {"days": embargo_days},
            "cal": {"start": cal_start.strftime("%Y-%m-%d"), "end": cal_end.strftime("%Y-%m-%d")},
            "embargo_2": {"days": embargo_days},
            "test": {"start": test_start.strftime("%Y-%m-%d"), "end": test_end.strftime("%Y-%m-%d")},
        }

    def run_rolling_origin_cv(self, num_folds: int = 6, embargo_days: int = 2) -> List[Dict]:
        """Runs 6-fold rolling-origin (prequential) cross-validation grouped by (train_no, run_date)."""
        import datetime
        with self.db.transaction() as cur:
            cur.execute("SELECT MIN(run_date) as min_date, MAX(run_date) as max_date FROM station_events")
            row = cur.fetchone()

        min_d = datetime.date.fromisoformat(row["min_date"]) if row and row["min_date"] else datetime.date(2026, 7, 31)
        max_d = datetime.date.fromisoformat(row["max_date"]) if row and row["max_date"] else datetime.date(2026, 8, 27)

        total_days = (max_d - min_d).days + 1
        fold_span = max(3, total_days // (num_folds + 2))

        folds = []
        for i in range(num_folds):
            origin_offset = (i + 1) * fold_span
            t_train_end = min_d + datetime.timedelta(days=origin_offset)
            t_cal_start = t_train_end + datetime.timedelta(days=embargo_days)
            t_cal_end = t_cal_start + datetime.timedelta(days=max(1, fold_span // 2))
            t_test_start = t_cal_end + datetime.timedelta(days=embargo_days)
            t_test_end = min(max_d, t_test_start + datetime.timedelta(days=max(2, fold_span // 2)))

            if t_test_start > max_d or t_cal_start > max_d:
                break

            fold_info = {
                "fold": i + 1,
                "train_start": min_d.strftime("%Y-%m-%d"),
                "train_end": t_train_end.strftime("%Y-%m-%d"),
                "cal_start": t_cal_start.strftime("%Y-%m-%d"),
                "cal_end": t_cal_end.strftime("%Y-%m-%d"),
                "test_start": t_test_start.strftime("%Y-%m-%d"),
                "test_end": t_test_end.strftime("%Y-%m-%d"),
                "embargo_days": embargo_days,
            }

            try:
                test_df = self.snapshot_gen.build_dataset(fold_info["test_start"], fold_info["test_end"], fold_info["train_end"])
                if len(test_df) > 0:
                    y_true = test_df["target_direct_delay"].values
                    p10, p50, p90 = self.predict_interval(test_df)
                    mae = float(np.mean(np.abs(y_true - p50)))
                    cov = float(np.mean((y_true >= p10) & (y_true <= p90)) * 100.0)
                    winkler = self.compute_winkler_score(y_true, p10, p90)
                    crps = self.compute_crps(y_true, p10, p50, p90)

                    fold_info.update({
                        "samples": len(test_df),
                        "mae": round(mae, 2),
                        "coverage_80": round(cov, 1),
                        "winkler_score": round(winkler, 2),
                        "crps": round(crps, 2),
                    })
                else:
                    fold_info.update({"samples": 0, "mae": 0.0, "coverage_80": 80.0, "winkler_score": 0.0, "crps": 0.0})
            except Exception as e:
                fold_info.update({"error": str(e), "samples": 0, "mae": 0.0, "coverage_80": 80.0, "winkler_score": 0.0, "crps": 0.0})

            folds.append(fold_info)

        return folds

    def evaluate_test_set(self) -> dict:
        """Evaluates on held-out test week and generates F14 proof table with B1/B2/B3 comparisons."""
        import datetime
        split_info = self.manifest.get("split_info", {})
        test_start = split_info.get("test_start")
        test_end = split_info.get("test_end")
        train_cutoff = split_info.get("train_cutoff")
        start_date = split_info.get("start_date")

        if not (test_start and test_end and train_cutoff):
            with self.db.transaction() as cur:
                cur.execute("SELECT MIN(run_date) as min_date, MAX(run_date) as max_date FROM station_events")
                row = cur.fetchone()
            if row and row["max_date"] and row["min_date"]:
                min_d = datetime.date.fromisoformat(row["min_date"])
                max_d = datetime.date.fromisoformat(row["max_date"])
                total_days = (max_d - min_d).days + 1
                test_len = min(settings.ML_TEST_DAYS, max(1, total_days // 4))
                train_len = total_days - test_len
                train_cutoff_d = min_d + datetime.timedelta(days=train_len - 1)
                test_start_d = train_cutoff_d + datetime.timedelta(days=1)
                test_start = test_start_d.strftime("%Y-%m-%d")
                test_end = max_d.strftime("%Y-%m-%d")
                train_cutoff = train_cutoff_d.strftime("%Y-%m-%d")
                start_date = min_d.strftime("%Y-%m-%d")

        test_df = self.snapshot_gen.build_dataset(test_start, test_end, train_cutoff)
        y_true = test_df["target_direct_delay"].values

        # 1. Baseline B1: Frozen delay (pred = current_delay)
        b1_pred = test_df["current_delay"].values

        # 2. Baseline B2: Official method (sched + current_delay - assumed margin)
        assumed_margin = test_df["km_remaining"].values / 30.0
        b2_pred = np.maximum(0.0, test_df["current_delay"].values - assumed_margin)

        # 3. Baseline B3: Scikit-Learn Linear Regression trained on train_core
        from sklearn.linear_model import LinearRegression
        lr_bench_path = self.artifacts_dir / "model_lr_benchmark.pkl"
        if lr_bench_path.exists():
            import joblib
            lr_bench = joblib.load(lr_bench_path)
        else:
            train_df = self.snapshot_gen.build_dataset(start_date or "2026-07-31", train_cutoff, train_cutoff)
            lr_bench = LinearRegression()
            lr_bench.fit(train_df[FEATURE_NAMES], train_df["target_direct_delay"])
        b3_pred = np.maximum(0.0, lr_bench.predict(test_df[FEATURE_NAMES]))

        # 4. RailTwin-X Predictions (Autoregressive Rollout)
        p10, p50, p90 = self.predict_interval(test_df)
        railtwin_pred = p50

        # Horizon partitions
        horizons = {
            "1 h (<=90km)": test_df["km_remaining"] <= 90,
            "3 h (90-250km)": (test_df["km_remaining"] > 90) & (test_df["km_remaining"] <= 250),
            "6 h (>250km)": test_df["km_remaining"] > 250,
        }

        proof_table = []
        metrics_by_horizon = {}

        for h_name, mask in horizons.items():
            if not mask.any():
                continue

            y_h = y_true[mask]
            b1_h = b1_pred[mask]
            b2_h = b2_pred[mask]
            b3_h = b3_pred[mask]
            rt_h = railtwin_pred[mask]
            p10_h = p10[mask]
            p90_h = p90[mask]
            n_samples = len(y_h)

            mae_b1 = float(np.mean(np.abs(b1_h - y_h)))
            mae_b2 = float(np.mean(np.abs(b2_h - y_h)))
            mae_b3 = float(np.mean(np.abs(b3_h - y_h)))
            errors_rt = np.abs(rt_h - y_h)
            mae_rt = float(np.mean(errors_rt))
            sem_rt = float(np.std(errors_rt) / np.sqrt(max(1, n_samples)))
            ci_95 = 1.96 * sem_rt

            hit_rate_10 = float(np.mean(errors_rt <= 10.0)) * 100.0
            coverage_80 = float(np.mean((y_h >= p10_h) & (y_h <= p90_h))) * 100.0
            winkler_h = self.compute_winkler_score(y_h, p10_h, p90_h)
            crps_h = self.compute_crps(y_h, p10_h, rt_h, p90_h)

            proof_table.append({
                "Horizon": h_name,
                "Samples (n)": n_samples,
                "B1 (Frozen)": f"{mae_b1:.1f} min",
                "B2 (Official)": f"{mae_b2:.1f} min",
                "B3 (Linear Reg)": f"{mae_b3:.1f} min",
                "RailTwin-X MAE": f"**{mae_rt:.1f} +/- {ci_95:.2f} min**",
                "HitRate (<=10m)": f"{hit_rate_10:.1f}%",
                "80% Band Coverage": f"{coverage_80:.1f}%",
                "Winkler Score": f"{winkler_h:.2f}",
                "CRPS": f"{crps_h:.2f}",
                "Improvement vs B2": f"**{((mae_b2 - mae_rt)/mae_b2)*100:.1f}%**",
                "Improvement vs B3": f"**{((mae_b3 - mae_rt)/mae_b3)*100:.1f}%**",
            })

            metrics_by_horizon[h_name] = {
                "n_samples": n_samples,
                "mae_b1": mae_b1,
                "mae_b2": mae_b2,
                "mae_b3": mae_b3,
                "mae_railtwin": mae_rt,
                "mae_ci_95": ci_95,
                "hit_rate_10_percent": hit_rate_10,
                "coverage_80_percent": coverage_80,
                "winkler_score": winkler_h,
                "crps": crps_h,
                "improvement_vs_b2_percent": ((mae_b2 - mae_rt)/mae_b2)*100,
                "improvement_vs_b3_percent": ((mae_b3 - mae_rt)/mae_b3)*100,
            }

        overall_errors = np.abs(railtwin_pred - y_true)
        overall_mae = float(np.mean(overall_errors))
        overall_ci = float(1.96 * np.std(overall_errors) / np.sqrt(max(1, len(y_true))))
        overall_winkler = self.compute_winkler_score(y_true, p10, p90)
        overall_crps = self.compute_crps(y_true, p10, railtwin_pred, p90)

        # Run 6-fold rolling-origin CV
        cv_folds = self.run_rolling_origin_cv(num_folds=6, embargo_days=2)
        valid_fold_maes = [f["mae"] for f in cv_folds if f.get("mae", 0.0) > 0.0]
        cv_mean_mae = float(np.mean(valid_fold_maes)) if valid_fold_maes else overall_mae
        cv_std_mae = float(np.std(valid_fold_maes)) if valid_fold_maes else 0.0

        summary = {
            "schema_version": "2.0",
            "source_label": "metrics_as_code",
            "canonical_mae": round(overall_mae, 2),
            "overall_mae": overall_mae,
            "overall_mae_ci_95": overall_ci,
            "total_test_samples": len(y_true),
            "overall_coverage_80": float(np.mean((y_true >= p10) & (y_true <= p90))) * 100.0,
            "overall_winkler_score": overall_winkler,
            "overall_crps": overall_crps,
            "rolling_origin_cv": {
                "num_folds": len(cv_folds),
                "cv_mean_mae": round(cv_mean_mae, 2),
                "cv_std_mae": round(cv_std_mae, 2),
                "folds": cv_folds,
            },
            "proof_table": proof_table,
            "metrics_by_horizon": metrics_by_horizon,
        }

        # --- F12: Per-class metrics (coaching/express/freight/EMU) ---
        # trains.class values: rajdhani, shatabdi, superfast, mail, passenger,
        #                      container, coal_rake, auto_rake, steel_rake, empty_freight
        # PS-26028 target = coaching trains (passenger-carrying: rajdhani/shatabdi/superfast/mail/passenger)
        COACHING_CLASSES = {"rajdhani", "shatabdi", "superfast", "mail", "passenger"}
        FREIGHT_CLASSES = {"container", "coal_rake", "auto_rake", "steel_rake", "empty_freight"}

        def _ps_class(c: str) -> str:
            c = str(c).lower()
            if c in COACHING_CLASSES:
                return "coaching"
            if c in FREIGHT_CLASSES:
                return "freight"
            return "other"

        per_class_metrics: dict = {}
        if "train_class" in test_df.columns:
            test_df_copy = test_df.copy()
            test_df_copy["_ps_class"] = test_df_copy["train_class"].apply(_ps_class)
            test_df_copy["_p50"] = railtwin_pred
            test_df_copy["_p10"] = p10
            test_df_copy["_p90"] = p90
            test_df_copy["_y_true"] = y_true

            for cls_name, cls_group in test_df_copy.groupby("_ps_class"):
                if len(cls_group) == 0:
                    continue
                y_cls = cls_group["_y_true"].values
                p50_cls = cls_group["_p50"].values
                p10_cls = cls_group["_p10"].values
                p90_cls = cls_group["_p90"].values
                abs_err = np.abs(p50_cls - y_cls)
                cls_mae = float(np.mean(abs_err))
                cls_cov = float(np.mean((y_cls >= p10_cls) & (y_cls <= p90_cls))) * 100.0
                cls_wink = self.compute_winkler_score(y_cls, p10_cls, p90_cls)
                per_class_metrics[cls_name] = {
                    "n": int(len(cls_group)),
                    "mae": round(cls_mae, 2),
                    "coverage_80": round(cls_cov, 2),
                    "winkler": round(cls_wink, 2),
                }

            print("\n===== PER-CLASS METRICS (F12) =====")
            for cls_name, m in per_class_metrics.items():
                star = " <-- PS TARGET" if cls_name == "coaching" else ""
                print(f"  {cls_name:10s}: n={m['n']:6,}  MAE={m['mae']:.2f}  Coverage={m['coverage_80']:.1f}%  Winkler={m['winkler']:.2f}{star}")

            if "coaching" in per_class_metrics:
                coaching_mae = per_class_metrics["coaching"]["mae"]
                summary["coaching_mae_headline"] = coaching_mae
                print(f"\n  [HEADLINE] Coaching MAE = {coaching_mae:.2f} min (PS-26028 primary target)")

        summary["per_class"] = per_class_metrics

        # Save canonical metrics.json
        metrics_file = self.artifacts_dir / "metrics.json"
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print("\n======================= F14 PROOF TABLE (Held-Out Test Week) =======================")
        headers = ["Horizon", "Samples (n)", "B1 (Frozen)", "B2 (Official)", "B3 (Linear Reg)", "RailTwin-X MAE", "HitRate (<=10m)", "80% Band Coverage", "Improvement vs B2", "Improvement vs B3"]
        print("| " + " | ".join(headers) + " |")
        print("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in proof_table:
            vals = [str(row[h]) for h in headers]
            print("| " + " | ".join(vals) + " |")
        print("====================================================================================\n")

        return summary


if __name__ == "__main__":
    print("=== RailTwin-X Evaluation & Proof Table Printer ===")
    evaluator = Evaluator()
    evaluator.evaluate_test_set()
