"""
Runtime Environment Detection for ONR ITSS POC
Detects the current deployment environment from Databricks App name or ENVIRONMENT variable.
"""

import os
import re

# Allowed environment names
_ALLOWED = {"dev", "staging", "prod"}


def get_runtime_env() -> str:
    """
    Extract environment from DATABRICKS_APP_NAME, assuming naming convention:
      app-onr-demo-${bundle.target}  -> app-onr-demo-dev/prod
    
    Falls back to ENVIRONMENT env var, then defaults to 'dev'.
    Always returns a valid string ('dev', 'staging', or 'prod').
    """
    # Primary: Extract from app name
    name = os.getenv("DATABRICKS_APP_NAME", "")
    if name:
        m = re.search(r"(dev|staging|prod)\b", name, flags=re.IGNORECASE)
        if m:
            return m.group(1).lower()

    # Fallback: Explicit ENVIRONMENT variable
    env = os.getenv("ENVIRONMENT", "dev").lower().strip()
    if env in _ALLOWED:
        return env

    # Safe default
    return "dev"


def is_production() -> bool:
    """Check if running in production environment."""
    return get_runtime_env() == "prod"


def is_debug_mode() -> bool:
    """Check if debug mode is enabled (typically in dev)."""
    return get_runtime_env() in ("dev", "staging")
