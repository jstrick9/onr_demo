# ONR ITSS Proof of Concept — Databricks Streamlit Demo

## Office of Naval Research (ONR) Code 08 IT Support Services
### Technical Demonstration: Elements 3–7

This repository contains a **Databricks Streamlit application** designed for the ONR ITSS technical demonstration, showcasing capabilities across five key scenario elements:

| Page | Element | Focus |
|------|---------|-------|
| **01 Ingestion** | Element 3 | Automated Ingestion, Data Operations, and Streaming |
| **02 Governance** | Element 4 | Data Governance, Quality, and Cataloging |
| **03 Analytics** | Element 5 | Decision-Support Analytics and Modeling |
| **04 Dashboard** | Element 6 | Unified Dashboard, Visualizations, and Process Automation |
| **05 Integration** | Element 7 | Interoperability, Data Portability, and Secure Export |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Databricks Streamlit App                         │
│  ┌───────────┬───────────┬───────────┬───────────┬───────────┐     │
│  │ Ingestion │Governance │ Analytics │ Dashboard │Integration│     │
│  │   (E3)    │   (E4)    │   (E5)    │   (E6)    │   (E7)    │     │
│  └─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┘     │
│        │           │           │           │           │           │
│  ┌─────▼───────────▼───────────▼───────────▼───────────▼─────┐     │
│  │         Unity Catalog onr_demo.{bronze | silver | gold | app}     │     │
│  └───────────────────────────────────────────────────────────┘     │
│                           │                                        │
│  ┌────────────────────────▼────────────────────────────────┐       │
│  │          Medallion Architecture (Bronze/Silver/Gold)     │       │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐             │       │
│  │  │ Bronze  │───▶│ Silver  │───▶│  Gold   │             │       │
│  │  │  (Raw)  │    │(Cleansed)│   │(Business)│            │       │
│  │  └─────────┘    └─────────┘    └─────────┘             │       │
│  └─────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- Databricks workspace with Apps enabled (AWS)
- Unity Catalog catalog `onr_demo` with schemas `bronze`, `silver`, `gold`, `app`
- SQL Warehouse access
- Service Principal with appropriate permissions
- Python 3.10+

## Deployment

### Using Databricks Asset Bundles:

```bash
# Validate the bundle
databricks bundle validate -t dev

# Deploy to dev environment
databricks bundle deploy -t dev

# Run the pipeline
databricks bundle run onr_demo_pipeline -t dev

# Deploy to production
databricks bundle deploy -t prod
```

### Manual Deployment:

1. Upload the `app-onr-demo` folder to your Databricks workspace
2. Run the SQL setup scripts in `sql/setup_uc_objects.sql`
3. Run the mock data generator in `resources/mock_data/generate_mock_data.py`
4. Create the Databricks App pointing to `app.yml`

---

## Project Structure

```
onr_demo/
├── README.md                          # This file
├── databricks.yml                     # DABs configuration
│
├── app-onr-demo/                      # Streamlit Application
│   ├── Home.py                        # Main entry point
│   ├── app.yml                        # App configuration
│   ├── requirements.txt               # Python dependencies
│   ├── config/
│   │   ├── dev/onr-conf.yaml          # Dev environment config
│   │   └── prod/onr-conf.yaml         # Prod environment config
│   ├── pages/
│   │   ├── 01_🔍_Ingestion.py         # Element 3
│   │   ├── 02_📊_Governance.py        # Element 4
│   │   ├── 03_🤖_Analytics.py         # Element 5
│   │   ├── 04_📈_Dashboard.py         # Element 6
│   │   └── 05_🔗_Integration.py       # Element 7
│   └── utils/
│       ├── db_helpers.py              # Database connection
│       ├── page_config_helpers.py     # UI configuration
│       ├── runtime_env.py             # Environment detection
│       ├── user_helpers.py            # SSO user management
│       ├── ingestion_helpers.py       # Element 3 utilities
│       ├── governance_helpers.py      # Element 4 utilities
│       ├── analytics_helpers.py       # Element 5 utilities
│       ├── dashboard_helpers.py       # Element 6 utilities
│       └── export_helpers.py          # Element 7 utilities
│
├── resources/
│   ├── images/                        # Logo and assets
│   └── mock_data/                     # Mock data generation
│
├── sql/                               # SQL scripts
│   ├── setup_uc_objects.sql           # Unity Catalog DDL
│   └── validation_queries.sql         # QA queries
│
├── notebooks/                         # Databricks notebooks
│   ├── 01_bronze_ingestion.py         # Auto Loader ingestion
│   ├── 02_silver_quality.py           # Data quality transforms
│   ├── 03_gold_aggregation.py         # Business aggregations
│   ├── 04_analytics_model.py          # ML/Analytics
│   └── 05_rag_agent.py               # RAG agent (optional)
│
└── documentation/                     # Supporting docs
```

---

## Mock Data

The demo uses **sanitized mock data** representing typical ONR command datasets:

- **S&T Research Grants Registry**: Grant IDs, Principal Investigators, funding amounts, research areas, statuses
- **Financial ERP Data**: Budget categories, quarterly expenditures, cost centers, execution rates

All data is synthetically generated — **no CUI, PII, or classified information**.

---

## Evaluation Criteria Alignment

This POC addresses the Government's evaluation criteria:

| Criterion | How This POC Addresses It |
|-----------|---------------------------|
| **Technical Competence** | Key Personnel demonstrate live platform navigation, code execution, and pipeline management |
| **Completeness** | All 5 elements executed sequentially with seamless transitions |
| **Open Architecture** | Standard APIs, portable data formats (CSV/JSON/Parquet), non-proprietary storage |
| **Strategic Alignment** | Modular design supports rapid adaptation to evolving command needs |

---

## Security & Compliance

- **Zero Trust**: MFA, least-privilege access, continuous authorization
- **IL4/IL5 Baseline**: Architecture supports DoD Impact Level 5 hosting
- **Data Constraints**: Mock/sanitized data only — no CUI/PII/classified information
- **Unity Catalog Governance**: Row-level filters, column masks, ABAC tags

---

## Contact

For questions about this POC:
- **Technical Lead**: [Your Name]
- **Email**: [your.email@domain.com]

---

*Built with Databricks on AWS — Serverless-first, Unity Catalog-governed*

## Mock data (Compass fixture)

Primary grants source: `resources/mock_data/grants_portfolio.json`  
- Contract: `compass.synthetic.v1` (400 synthetic S&T grants, no CUI/PII)
- Exact fields: `grant_no`, `title`, `abstract`, `program_area`, `fiscal_year`, `amount_usd`, `awardee`, `org_unit`, `classification_band`, `batch_id`, `created_at`
- Financial ERP is **derived** from those grants (3 transactions per grant, keyed by `grant_no`) via `resources/mock_data/generate_mock_data.py`

```bash
python resources/mock_data/generate_mock_data.py --format csv
```
