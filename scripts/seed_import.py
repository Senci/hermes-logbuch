#!/usr/bin/env python3
"""Load a tab-separated file of labels as manual labels into <home>/logbuch/labels.db.

Usage: seed_import.py <tsv> --home <hermes-home> [--allow-live]

The tsv has four tab-separated columns: session id, topic, value 0-3, summary. The topic must be a key of
the data file the backend would load for that home (lb_data). Idempotent: an existing
manual label is kept, an llm label is replaced, nothing else changes. Refuses the live Hermes home
(~/.hermes, or $HERMES_HOME) unless --allow-live is given; seeding the live store is an operator step.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))

import lb_data  # noqa: E402
import lb_labels  # noqa: E402
from lb_topics import SUMMARY_MAX, VALUES  # noqa: E402


def read_rows(tsv: Path, topics: dict) -> list[tuple[str, str, int, str]]:
    rows = []
    seen = set()
    with open(tsv, newline="", encoding="utf-8") as fh:
        for n, rec in enumerate(csv.reader(fh, delimiter="\t"), 1):
            if not rec or not "".join(rec).strip():
                continue
            if len(rec) < 4:
                raise SystemExit(f"{tsv}:{n}: expected 4 columns, got {len(rec)}")
            sid, topic, raw_value, summary = rec[0].strip(), rec[1].strip(), rec[2].strip(), rec[3].strip()
            if topic not in topics:
                raise SystemExit(f"{tsv}:{n}: unknown topic {topic!r}")
            if not raw_value.isdigit() or int(raw_value) not in VALUES:
                raise SystemExit(f"{tsv}:{n}: value must be 0-3, got {raw_value!r}")
            if not sid or not summary:
                raise SystemExit(f"{tsv}:{n}: empty id or summary")
            if sid in seen:
                raise SystemExit(f"{tsv}:{n}: duplicate id {sid}")
            seen.add(sid)
            rows.append((sid, topic, int(raw_value), " ".join(summary.split())[:SUMMARY_MAX].rstrip()))
    return rows


def live_homes() -> set[Path]:
    homes = {Path.home() / ".hermes"}
    if os.environ.get("HERMES_HOME"):
        homes.add(Path(os.environ["HERMES_HOME"]))
    return {h.resolve() for h in homes}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tsv", type=Path)
    ap.add_argument("--home", type=Path, required=True)
    ap.add_argument("--allow-live", action="store_true", help="permit the live Hermes home (operator gate)")
    args = ap.parse_args()
    home = args.home.expanduser().resolve()
    if home in live_homes() and not args.allow_live:
        print(f"refusing the live Hermes home {home}; pass --allow-live only on the operator's go", file=sys.stderr)
        return 2
    counts = lb_labels.seed_manual(home, read_rows(args.tsv, lb_data.load(home).topics))
    print(f"labels.db: {lb_labels.db_path(home)}")
    print(" ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
