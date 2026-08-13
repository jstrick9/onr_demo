"""
Load the Compass synthetic grants fixture and derive ERP transactions.

Source of truth: resources/mock_data/grants_portfolio.json
Schema (exact): grant_no, title, abstract, program_area, fiscal_year,
amount_usd, awardee, org_unit, classification_band, batch_id, created_at
"""

from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

GRANT_COLUMNS = [
    "grant_no",
    "title",
    "abstract",
    "program_area",
    "fiscal_year",
    "amount_usd",
    "awardee",
    "org_unit",
    "classification_band",
    "batch_id",
    "created_at",
]

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

FIXTURE_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "resources" / "mock_data" / "grants_portfolio.json",
    Path(__file__).resolve().parents[1] / "data" / "grants_portfolio.json",
    Path("/home/user/uploads/grants_portfolio.json"),
]


def _find_fixture() -> Path:
    for p in FIXTURE_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError(
        "grants_portfolio.json not found. Expected under resources/mock_data/."
    )


@lru_cache(maxsize=1)
def load_fixture() -> Dict:
    path = _find_fixture()
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def grants_dataframe() -> pd.DataFrame:
    fixture = load_fixture()
    df = pd.DataFrame(fixture.get("grants", []))
    for col in GRANT_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[GRANT_COLUMNS].copy()
    df["fiscal_year"] = pd.to_numeric(df["fiscal_year"], errors="coerce").astype("Int64")
    df["amount_usd"] = pd.to_numeric(df["amount_usd"], errors="coerce")
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    return df


def derive_financial_records(txns_per_grant: int = 3, seed: int = 20260810) -> pd.DataFrame:
    """Derive synthetic ERP lines keyed to grant_no / amount_usd / org_unit."""
    rng = random.Random(seed)
    grants = grants_dataframe()
    rows: List[Dict] = []
    txn = 0
    for rec in grants.to_dict(orient="records"):
        amount = float(rec["amount_usd"] or 0)
        if amount <= 0:
            continue
        n = txns_per_grant
        weights = [rng.random() for _ in range(n)]
        total_w = sum(weights) or 1.0
        remaining = amount
        for i, w in enumerate(weights):
            share = amount * (w / total_w) if i < n - 1 else remaining
            remaining -= share if i < n - 1 else 0
            exec_rate = rng.uniform(0.72, 1.08)
            budget = round(share, 2)
            actual = round(budget * exec_rate, 2)
            fy = int(rec["fiscal_year"] or 2025)
            txn += 1
            rows.append(
                {
                    "transaction_id": f"FIN-{100000 + txn}",
                    "grant_no": rec["grant_no"],
                    "cost_center": rec["org_unit"],
                    "program_area": rec["program_area"],
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
    return pd.DataFrame(rows)


@lru_cache(maxsize=1)
def financial_dataframe() -> pd.DataFrame:
    return derive_financial_records()


def program_areas() -> List[str]:
    df = grants_dataframe()
    return sorted(df["program_area"].dropna().unique().tolist())


def fiscal_years() -> List[int]:
    df = grants_dataframe()
    return sorted(int(y) for y in df["fiscal_year"].dropna().unique().tolist())


def portfolio_kpis() -> Dict:
    g = grants_dataframe()
    f = financial_dataframe()
    total = float(g["amount_usd"].sum())
    n = int(len(g))
    exec_rate = (
        float(f["actual_expenditure"].sum() / f["budget_allocated"].sum() * 100)
        if len(f) and f["budget_allocated"].sum()
        else 0.0
    )
    return {
        "grant_count": n,
        "total_funding": total,
        "avg_award": total / n if n else 0,
        "execution_rate": exec_rate,
        "awardee_count": int(g["awardee"].nunique()),
        "program_areas": int(g["program_area"].nunique()),
        "fy_min": int(g["fiscal_year"].min()),
        "fy_max": int(g["fiscal_year"].max()),
        "transaction_count": int(len(f)),
    }


def filter_grants(
    fiscal_years_sel: Optional[List[int]] = None,
    program_areas_sel: Optional[List[str]] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
    search: Optional[str] = None,
) -> pd.DataFrame:
    df = grants_dataframe()
    if fiscal_years_sel:
        df = df[df["fiscal_year"].isin(fiscal_years_sel)]
    if program_areas_sel:
        df = df[df["program_area"].isin(program_areas_sel)]
    if amount_min is not None:
        df = df[df["amount_usd"] >= amount_min]
    if amount_max is not None:
        df = df[df["amount_usd"] <= amount_max]
    if search:
        q = search.lower()
        mask = (
            df["title"].fillna("").str.lower().str.contains(q)
            | df["awardee"].fillna("").str.lower().str.contains(q)
            | df["grant_no"].fillna("").str.lower().str.contains(q)
            | df["abstract"].fillna("").str.lower().str.contains(q)
            | df["org_unit"].fillna("").str.lower().str.contains(q)
        )
        df = df[mask]
    return df
