"""
ONR ITSS POC — Mock Data Generator
Generates sanitized mock data for S&T Research Grants and Financial ERP data.
No CUI, PII, or classified information — for demonstration purposes only.

Usage:
    python generate_mock_data.py [--records 500] [--output-dir ./]
"""

import argparse
import csv
import json
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict


# -------------------------------
# CONSTANTS
# -------------------------------

RESEARCH_AREAS = [
    "Artificial Intelligence",
    "Cybersecurity",
    "Autonomous Systems",
    "Directed Energy",
    "Quantum Computing",
    "Hypersonics",
    "Undersea Warfare",
    "Space Systems",
    "Advanced Materials",
    "Biotechnology",
]

INSTITUTIONS = [
    "Massachusetts Institute of Technology",
    "Stanford University",
    "Naval Postgraduate School",
    "Naval Research Laboratory",
    "Johns Hopkins Applied Physics Laboratory",
    "Georgia Institute of Technology",
    "California Institute of Technology",
    "University of Michigan",
    "Carnegie Mellon University",
    "University of Texas at Austin",
    "Purdue University",
    "Virginia Tech",
    "University of Maryland",
    "Penn State University",
    "Duke University",
]

PI_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Anderson", "Thomas", "Taylor",
    "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris",
    "Clark", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Green", "Baker", "Adams", "Nelson", "Hill",
    "Campbell", "Mitchell", "Roberts", "Carter", "Phillips", "Evans",
]

GRANT_STATUSES = ["Active", "Completed", "Pending Review", "On Hold"]

COST_CENTERS = [
    "R&D-001", "R&D-002", "R&D-003", "ADMIN-001", "OPS-001",
    "LAB-001", "LAB-002", "IT-001", "IT-002", "HQ-001",
    "FLEET-001", "FLEET-002", "TRAINING-001",
]

FINANCIAL_CATEGORIES = [
    "Personnel", "Equipment", "Travel", "Contractors",
    "Supplies", "Training", "Facilities", "Other Direct Costs",
    "Subcontracts", "Materials",
]

FISCAL_YEARS = [2022, 2023, 2024, 2025, 2026]
QUARTERS = ["Q1", "Q2", "Q3", "Q4"]


# -------------------------------
# GENERATORS
# -------------------------------

def generate_grant_id(index: int) -> str:
    """Generate a unique grant ID."""
    return f"ONR-{10000 + index}"


def generate_pi_name() -> str:
    """Generate a fake Principal Investigator name."""
    first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer",
                   "Michael", "Linda", "David", "Elizabeth", "William", "Barbara",
                   "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah",
                   "Christopher", "Karen", "Charles", "Lisa", "Daniel", "Nancy"]
    return f"Dr. {random.choice(first_names)} {random.choice(PI_LAST_NAMES)}"


def generate_grant_title(research_area: str) -> str:
    """Generate a realistic grant title."""
    adjectives = ["Advanced", "Next-Generation", "Innovative", "Novel", "Integrated"]
    nouns = ["Techniques", "Methods", "Systems", "Approaches", "Frameworks"]
    applications = [
        "for Naval Operations", "for Defense Applications",
        "for Maritime Security", "for Force Protection",
        "for Undersea Dominance", "for Information Warfare",
    ]
    return f"{random.choice(adjectives)} {research_area} {random.choice(nouns)} {random.choice(applications)}"


def generate_grants_data(num_records: int) -> List[Dict]:
    """Generate mock grants data."""
    data = []
    
    for i in range(num_records):
        research_area = random.choice(RESEARCH_AREAS)
        start_date = datetime.now() - timedelta(days=random.randint(0, 1095))
        duration = timedelta(days=random.randint(365, 1095))
        end_date = start_date + duration
        
        grant = {
            "grant_id": generate_grant_id(i),
            "title": generate_grant_title(research_area),
            "principal_investigator": generate_pi_name(),
            "institution": random.choice(INSTITUTIONS),
            "research_area": research_area,
            "award_amount": round(random.uniform(50000, 5000000), 2),
            "status": random.choice(GRANT_STATUSES),
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "fiscal_year": random.choice(FISCAL_YEARS),
        }
        data.append(grant)
    
    return data


def generate_financial_data(num_records: int) -> List[Dict]:
    """Generate mock financial ERP data."""
    data = []
    
    for i in range(num_records):
        fiscal_year = random.choice(FISCAL_YEARS)
        quarter = random.choice(QUARTERS)
        budget = round(random.uniform(10000, 1000000), 2)
        execution_rate = random.uniform(0.65, 1.15)
        actual = round(budget * execution_rate, 2)
        
        transaction = {
            "transaction_id": f"FIN-{100000 + i}",
            "cost_center": random.choice(COST_CENTERS),
            "category": random.choice(FINANCIAL_CATEGORIES),
            "fiscal_year": fiscal_year,
            "quarter": quarter,
            "budget_allocated": budget,
            "actual_expenditure": actual,
            "execution_rate": round(execution_rate * 100, 1),
            "variance": round(budget - actual, 2),
            "status": "Closed" if fiscal_year < 2026 else "Open",
        }
        data.append(transaction)
    
    return data


# -------------------------------
# EXPORT FUNCTIONS
# -------------------------------

def save_to_csv(data: List[Dict], filename: str):
    """Save data to CSV file."""
    if not data:
        return
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ Saved {len(data)} records to {filename}")


def save_to_json(data: List[Dict], filename: str):
    """Save data to JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"✅ Saved {len(data)} records to {filename}")


def save_to_parquet(data: List[Dict], filename: str):
    """Save data to Parquet file (requires pyarrow)."""
    try:
        import pandas as pd
        df = pd.DataFrame(data)
        df.to_parquet(filename, index=False)
        print(f"✅ Saved {len(data)} records to {filename}")
    except ImportError:
        print("⚠️ pyarrow not installed — skipping Parquet export")
        print("   Install with: pip install pyarrow")


# -------------------------------
# DATABRICKS DIRECT UPLOAD
# -------------------------------

def upload_to_databricks(data: List[Dict], table_name: str, catalog: str, schema: str):
    """Upload data directly to Databricks table."""
    try:
        from databricks.sdk import WorkspaceClient
        from pyspark.sql import SparkSession
        
        spark = SparkSession.builder.getOrCreate()
        df = spark.createDataFrame(data)
        
        full_table = f"`{catalog}`.`{schema}`.{table_name}"
        df.write.mode("append").saveAsTable(full_table)
        
        print(f"✅ Uploaded {len(data)} records to {full_table}")
    except Exception as e:
        print(f"⚠️ Direct upload failed: {str(e)}")
        print("   Save to CSV/JSON and upload manually or use Auto Loader")


# -------------------------------
# MAIN
# -------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate mock data for ONR ITSS POC")
    parser.add_argument("--grants", type=int, default=500, help="Number of grants records")
    parser.add_argument("--financial", type=int, default=2000, help="Number of financial records")
    parser.add_argument("--output-dir", type=str, default=".", help="Output directory")
    parser.add_argument("--format", type=str, default="all", choices=["csv", "json", "parquet", "all"],
                        help="Output format")
    parser.add_argument("--databricks", action="store_true", help="Upload directly to Databricks")
    parser.add_argument("--catalog", type=str, default="onr_demo", help="Unity Catalog catalog")
    parser.add_argument("--schema", type=str, default="dev", help="Unity Catalog schema")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    print("=" * 60)
    print("ONR ITSS POC — Mock Data Generator")
    print("=" * 60)
    print(f"\nGenerating:")
    print(f"  - {args.grants:,} grants records")
    print(f"  - {args.financial:,} financial records")
    print(f"\nOutput directory: {os.path.abspath(args.output_dir)}")
    print()
    
    # Generate data
    print("Generating grants data...")
    grants_data = generate_grants_data(args.grants)
    
    print("Generating financial data...")
    financial_data = generate_financial_data(args.financial)
    
    # Save files
    formats = ["csv", "json", "parquet"] if args.format == "all" else [args.format]
    
    for fmt in formats:
        if fmt == "csv":
            save_to_csv(grants_data, os.path.join(args.output_dir, "sample_grants.csv"))
            save_to_csv(financial_data, os.path.join(args.output_dir, "sample_financial.csv"))
        elif fmt == "json":
            save_to_json(grants_data, os.path.join(args.output_dir, "sample_grants.json"))
            save_to_json(financial_data, os.path.join(args.output_dir, "sample_financial.json"))
        elif fmt == "parquet":
            save_to_parquet(grants_data, os.path.join(args.output_dir, "sample_grants.parquet"))
            save_to_parquet(financial_data, os.path.join(args.output_dir, "sample_financial.parquet"))
    
    # Upload to Databricks if requested
    if args.databricks:
        print("\nUploading to Databricks...")
        upload_to_databricks(grants_data, "bronze_grants", args.catalog, args.schema)
        upload_to_databricks(financial_data, "bronze_financial", args.catalog, args.schema)
    
    # Summary
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"\nFiles generated:")
    for f in os.listdir(args.output_dir):
        if f.startswith("sample_"):
            filepath = os.path.join(args.output_dir, f)
            size = os.path.getsize(filepath)
            print(f"  - {f} ({size:,} bytes)")
    
    print(f"\n✅ Total records generated: {args.grants + args.financial:,}")
    print("\n⚠️ REMINDER: This is MOCK DATA only — no CUI/PII/classified information")


if __name__ == "__main__":
    main()
