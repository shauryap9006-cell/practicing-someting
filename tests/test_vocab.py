"""Unit and property tests for StationVocab (Task T1)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import pytest
from hypothesis import given, strategies as st

from ml.vocab import StationVocab, PAD, UNK


def test_station_vocab_from_db_determinism():
    """Two independent DB constructions produce byte-identical vocabularies and encodings."""
    v1 = StationVocab.from_db()
    v2 = StationVocab.from_db()
    assert len(v1) == len(v2)
    assert v1.itos == v2.itos
    assert v1.stoi == v2.stoi

    test_codes = ["NDLS", "CNB", "PRYJ", "DDU", "GZB", "ALJN", "TDL", "ETW", "MZP"]
    for code in test_codes:
        assert v1.encode(code) == v2.encode(code)
        assert v1.encode(code) != v1.encode(UNK)


def test_station_vocab_roundtrip_save_load():
    """Serialization and deserialization are lossless and preserve exact mappings."""
    v = StationVocab.from_db()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "vocab.json"
        v.save(path)
        assert path.exists()

        v_loaded = StationVocab.load(path)
        assert v_loaded.itos == v.itos
        assert v_loaded.stoi == v.stoi
        assert len(v_loaded) == len(v)

        for c in ["NDLS", "CNB", "PRYJ", "UNKNOWN_STATION_999", None, ""]:
            assert v_loaded.encode(c) == v.encode(c)


def test_station_vocab_special_tokens():
    """PAD maps to 0 and UNK maps to 1; unobserved codes map to UNK."""
    v = StationVocab(["NDLS", "CNB", "PRYJ"], min_size=64)
    assert v.encode(None) == 0
    assert v.encode("") == 0
    assert v.decode(0) == PAD
    assert v.encode("NONEXISTENT_XYZ") == 1
    assert v.decode(1) == UNK

    report = v.collision_report()
    assert report["real_codes"] == 3
    assert report["buckets"] == 64
    assert report["collisions"] == 0


@given(st.lists(st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")), min_size=1, max_size=8), min_size=1, max_size=150))
def test_station_vocab_zero_collisions_hypothesis(codes):
    """Hypothesis property: any input code list has zero index collisions among distinct codes."""
    vocab = StationVocab(codes, min_size=max(256, len(codes) + 10))
    encoded_map = {}
    for code in codes:
        norm = code.strip().upper()
        if not norm:
            continue
        idx = vocab.encode(code)
        if norm in encoded_map:
            assert encoded_map[norm] == idx
        else:
            encoded_map[norm] = idx

    # Values for distinct normalized codes must all be distinct
    distinct_indices = list(encoded_map.values())
    assert len(distinct_indices) == len(set(distinct_indices))
