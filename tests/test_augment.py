"""Unit tests for synthetic SimPy augmentation flywheel and Invariant I4 isolation (Task T9)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data.db import get_db
from ml.augment import (
    generate_synthetic_simpy_samples,
    mix_augmented_dataset,
    enforce_eval_holdout_isolation,
    MAX_SYNTHETIC_MIXING_RATIO,
)


def test_synthetic_generation_and_tagging():
    """Synthetic samples are properly generated and tagged source='synthetic_simpy'."""
    db = get_db()
    synth_df = generate_synthetic_simpy_samples(db, n_samples=50)

    assert len(synth_df) > 0
    assert (synth_df["source"] == "synthetic_simpy").all()
    assert "current_delay" in synth_df.columns
    assert "delay_target" in synth_df.columns


def test_mixing_ratio_hard_ceiling():
    """Augmented dataset strictly respects the <=7% synthetic mixing ceiling."""
    n_obs = 1000
    n_synth = 500  # Try to over-inject

    obs_df = pd.DataFrame({
        "current_delay": np.zeros(n_obs),
        "source": ["observed"] * n_obs,
    })
    synth_df = pd.DataFrame({
        "current_delay": np.ones(n_synth),
        "source": ["synthetic_simpy"] * n_synth,
    })

    mixed_df = mix_augmented_dataset(obs_df, synth_df, max_synthetic_ratio=0.07)
    synth_ratio = (mixed_df["source"] == "synthetic_simpy").mean()

    assert synth_ratio <= 0.070001
    assert len(mixed_df) == n_obs + int(np.floor(n_obs * 0.07 / (1.0 - 0.07)))


def test_invariant_i4_eval_isolation_guard():
    """Invariant I4: Rejects any synthetic row entering held-out evaluation sets."""
    # Clean evaluation dataset
    clean_eval_df = pd.DataFrame({
        "current_delay": [5.0, 10.0, 15.0],
        "source": ["observed", "observed", "observed"],
    })
    enforce_eval_holdout_isolation(clean_eval_df)  # Should pass without error

    # Contaminated evaluation dataset
    contaminated_eval_df = pd.DataFrame({
        "current_delay": [5.0, 10.0, 15.0],
        "source": ["observed", "synthetic_simpy", "observed"],
    })
    with pytest.raises(AssertionError, match="Invariant I4 Violation"):
        enforce_eval_holdout_isolation(contaminated_eval_df)
