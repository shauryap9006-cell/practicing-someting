"""Deterministic station vocabulary. Replaces abs(hash(code)) % 1200.

Fixes: (a) PYTHONHASHSEED salting => silent per-process embedding corruption;
(b) pigeonhole collisions (>=23 guaranteed, ~600 expected pairs).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Union

PAD, UNK = "<PAD>", "<UNK>"


class StationVocab:
    """Persistent, zero-collision vocabulary for mapping railway station codes to embedding indices."""

    def __init__(self, codes: List[str], min_size: int = 2048):
        cleaned = {c.strip().upper() for c in codes if c and isinstance(c, str) and c.strip()}
        unique = sorted(cleaned)
        assert unique, "empty station vocabulary"
        self.itos: List[str] = [PAD, UNK, *unique]
        while len(self.itos) < min_size:  # headroom for new corridor stations
            self.itos.append(f"<RESV_{len(self.itos)}>")
        self.stoi: Dict[str, int] = {c: i for i, c in enumerate(self.itos)}
        assert len(self.stoi) == len(self.itos), "uniqueness invariant violated in StationVocab"

    def __len__(self) -> int:
        return len(self.itos)

    def encode(self, code: Optional[str]) -> int:
        """Encodes a station code to an index. Returns PAD for None, UNK for unseen codes."""
        if code is None:
            return self.stoi[PAD]
        code_str = str(code).strip().upper()
        if not code_str:
            return self.stoi[PAD]
        return self.stoi.get(code_str, self.stoi[UNK])

    def decode(self, idx: int) -> str:
        """Decodes an index to a station code token."""
        if 0 <= idx < len(self.itos):
            return self.itos[idx]
        return UNK

    def save(self, path: Union[Path, str]) -> None:
        """Saves vocabulary to JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"version": 2, "itos": self.itos}, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Union[Path, str]) -> StationVocab:
        """Loads vocabulary from JSON file."""
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        v = cls.__new__(cls)
        v.itos = d["itos"]
        v.stoi = {c: i for i, c in enumerate(v.itos)}
        return v

    @classmethod
    def from_db(cls, db_path: str = "data/railtwin.db", min_size: int = 2048) -> StationVocab:
        """Constructs station vocabulary directly from distinct station codes in database."""
        con = sqlite3.connect(db_path)
        try:
            rows = con.execute("SELECT DISTINCT code FROM stations WHERE code IS NOT NULL").fetchall()
        finally:
            con.close()
        return cls([r[0] for r in rows], min_size=min_size)

    def collision_report(self) -> Dict[str, int]:
        """Reports station vocabulary coverage and collision statistics."""
        resv_prefix = "<RESV_"
        real = [c for c in self.itos[2:] if not c.startswith(resv_prefix)]
        return {
            "real_codes": len(real),
            "buckets": len(self.itos),
            "collisions": 0,  # structural guarantee: 0 collisions by construction
        }
