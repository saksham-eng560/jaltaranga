"""Provenance and QC Ledger for Jaltaranga.

Tracks provenance, licensing, retrieval metadata, and quality-control flags
for every dataset used across the hydrological and routing pipeline.
"""
from __future__ import annotations

import argparse
import datetime
import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

VALID_QC_FLAGS = {"ok", "suspect", "synthetic", "digitized"}

DEFAULT_LEDGER_PATH = Path(__file__).resolve().parent.parent / "data" / "ledger.jsonl"


@dataclass
class LedgerEntry:
    entry_id: str
    dataset: str
    source_url: str
    source_name: str
    retrieved_at: str
    licence: str
    qc_flag: str
    qc_notes: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate integrity and schema constraints."""
        if not self.entry_id:
            raise ValueError("entry_id cannot be empty")
        if not self.dataset:
            raise ValueError("dataset cannot be empty")
        if not self.source_name:
            raise ValueError("source_name cannot be empty")
        if self.qc_flag not in VALID_QC_FLAGS:
            raise ValueError(
                f"Invalid qc_flag '{self.qc_flag}'. Must be one of {sorted(VALID_QC_FLAGS)}"
            )
        # Verify ISO timestamp
        try:
            datetime.datetime.fromisoformat(self.retrieved_at.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(f"Invalid retrieved_at ISO timestamp '{self.retrieved_at}': {e}")
        if not self.licence:
            raise ValueError("licence cannot be empty")


def record(
    dataset: str,
    source_url: str,
    source_name: str,
    licence: str,
    qc_flag: str,
    qc_notes: str,
    entry_id: Optional[str] = None,
    retrieved_at: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
) -> LedgerEntry:
    """Record a dataset provenance entry into the JSONL ledger."""
    if entry_id is None:
        entry_id = f"LE-{uuid.uuid4().hex[:10]}"
    if retrieved_at is None:
        retrieved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if metadata is None:
        metadata = {}

    entry = LedgerEntry(
        entry_id=entry_id,
        dataset=dataset,
        source_url=source_url,
        source_name=source_name,
        retrieved_at=retrieved_at,
        licence=licence,
        qc_flag=qc_flag,
        qc_notes=qc_notes,
        metadata=metadata,
    )
    entry.validate()

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    return entry


def load_ledger(ledger_path: Path = DEFAULT_LEDGER_PATH) -> List[LedgerEntry]:
    """Load all entries from the ledger file."""
    if not ledger_path.exists():
        return []
    entries = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            entry = LedgerEntry(**data)
            entries.append(entry)
    return entries


def validate_ledger(ledger_path: Path = DEFAULT_LEDGER_PATH) -> bool:
    """Validate all entries in the ledger."""
    entries = load_ledger(ledger_path)
    if not entries:
        print(f"Warning: Ledger at {ledger_path} is empty.")
        return True
    for i, entry in enumerate(entries):
        try:
            entry.validate()
        except ValueError as e:
            print(f"Validation failure at entry #{i} ({entry.entry_id}): {e}")
            return False
    return True


def inspect_ledger(ledger_path: Path = DEFAULT_LEDGER_PATH) -> None:
    """Print a summary table of the ledger entries."""
    entries = load_ledger(ledger_path)
    print("=" * 80)
    print(f"JALTARANGA PROVENANCE & QC LEDGER ({len(entries)} entries)")
    print("=" * 80)
    if not entries:
        print("Ledger is currently empty.")
        return

    for entry in entries:
        print(f"[{entry.qc_flag.upper()}] {entry.dataset} (ID: {entry.entry_id})")
        print(f"  Source   : {entry.source_name} ({entry.source_url})")
        print(f"  Licence  : {entry.licence}")
        print(f"  Retrieved: {entry.retrieved_at}")
        print(f"  QC Notes : {entry.qc_notes}")
        if entry.metadata:
            print(f"  Metadata : {json.dumps(entry.metadata)}")
        print("-" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Jaltaranga Provenance & QC Ledger CLI")
    parser.add_argument("--inspect", action="store_true", help="Inspect and display ledger entries")
    parser.add_argument("--validate", action="store_true", help="Validate all ledger entries")
    parser.add_argument("--path", type=str, default=str(DEFAULT_LEDGER_PATH), help="Custom path to ledger file")
    args = parser.parse_args()

    path = Path(args.path)
    if args.validate:
        is_valid = validate_ledger(path)
        if is_valid:
            print(f"Success: All entries in {path} passed validation.")
        else:
            raise SystemExit(1)
    else:
        inspect_ledger(path)


if __name__ == "__main__":
    main()
