"""
Runtime environment for ONR ITSS POC.

Single POC workspace — medallion schemas bronze / silver / gold / app.
"""

import os


def get_runtime_env() -> str:
    """Always 'poc' for this demonstration (no prod split)."""
    return os.getenv("ENVIRONMENT", "poc").lower().strip() or "poc"


def is_production() -> bool:
    return False


def is_debug_mode() -> bool:
    return True
