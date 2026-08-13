"""
ONR ITSS POC — Mock data packager

Loads the Compass synthetic grants fixture (grants_portfolio.json) and
derives Financial ERP transactions keyed to grant_no.

No CUI / PII / classified data.

Usage:
    python generate_mock_data.py [--output-dir ./] [--format all]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from pathlib import Path
from typing import Dict, List

FINANCIAL_CATEGORIES = [
    "Personnel",
    "Equipment",
    "Travel",
    "Contractors",
    "Supplies",
    "Training",
    "Facilities",
    "Other Direct Costs",
]

HERE = Path(__file__).resolve().parent
DEFAULT_FIXTURE = HERE / "grants_portfolio.json"


def load_grants(fixture_path: Path) -> List[Dict]:
    with fixture_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    grants = payload.get("grants", [])
    print(f"Loaded {len(grants)} grants from {fixture_path.name}")
    print(f"  fixture_contract={payload.get('fixture_contract')} seed={payload.get('generator_seed')}")
    return grants


def derive_financial(grants: List[Dict], txns_per_grant: int = 3, seed: int = 20260810) -> List[Dict]:
    rng = random.Random(seed)
    rows: List[Dict] = []
    txn = 0
    for rec in grants:
        amount = float(rec.get("amount_usd") or 0)
        if amount <= 0:
            continue
        weights = [rng.random() for _ in range(txns_per_grant)]
        total_w = sum(weights) or 1.0
        remaining = amount
        for i, w in enumerate(weights):
            share = amount * (w / total_w) if i < txns_per_grant - 1 else remaining
            remaining -= share if i < txns_per_grant - 1 else 0
            exec_rate = rng.uniform(0.72, 1.08)
            budget = round(share, 2)
            actual = round(budget * exec_rate, 2)
            fy = int(rec.get("fiscal_year") or 2025)
            txn += 1
            rows.append(
                {
                    "transaction_id": f"FIN-{100000 + txn}",
                    "grant_no": rec["grant_no"],
                    "cost_center": rec.get("org_unit"),
                    "program_area": rec.get("program_area"),
                    "category": rng.choice(FINANCIAL_CATEGORIES),
                    "fiscal_year": fy,
                    "quarter": rng.choice(["Q1", "Q2", "Q3", "Q4"]),
                    "budget_allocated": budget,
                    "actual_expenditure": actual,
                    "execution_rate": round(exec_rate * 100, 1),
                    "variance": round(budget - actual, 2),
                    "status": "Closed" if fy < 2026 else "Open",
                    "batch_id": rec.get("batch_id") or "seed-initial-2026",
                }
            )
    return rows


def save_csv(data: List[Dict], filename: str) -> None:
    if not data:
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
    print(f"Saved {len(data)} records to {filename}")


def save_json(data, filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Saved {filename}")


def save_parquet(data: List[Dict], filename: str) -> None:
    try:
        import pandas as pd

        pd.DataFrame(data).to_parquet(filename, index=False)
        print(f"Saved {len(data)} records to {filename}")
    except ImportError:
        print("pyarrow/pandas not installed — skipping Parquet")


def main() -> None:
    parser = argparse.ArgumentParser(description="Package ONR fixture + derived ERP")
    parser.add_argument("--fixture", type=str, default=str(DEFAULT_FIXTURE))
    parser.add_argument("--output-dir", type=str, default=str(HERE))
    parser.add_argument("--format", type=str, default="all", choices=["csv", "json", "parquet", "all"])
    parser.add_argument("--txns-per-grant", type=int, default=3)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    grants = load_grants(Path(args.fixture))
    financial = derive_financial(grants, txns_per_grant=args.txns_per_grant)

    formats = ["csv", "json", "parquet"] if args.format == "all" else [args.format]
    for fmt in formats:
        if fmt == "csv":
            save_csv(grants, os.path.join(args.output_dir, "sample_grants.csv"))
            save_csv(financial, os.path.join(args.output_dir, "sample_financial.csv"))
        elif fmt == "json":
            save_json(grants, os.path.join(args.output_dir, "sample_grants.json"))
            save_json(financial, os.path.join(args.output_dir, "sample_financial.json"))
        elif fmt == "parquet":
            save_parquet(grants, os.path.join(args.output_dir, "sample_grants.parquet"))
            save_parquet(financial, os.path.join(args.output_dir, "sample_financial.parquet"))

    print(f"\nGrants: {len(grants):,}  Financial txns: {len(financial):,}")
    print("MOCK / SYNTHETIC ONLY — no CUI/PII/classified information")


if __name__ == "__main__":
    main()
