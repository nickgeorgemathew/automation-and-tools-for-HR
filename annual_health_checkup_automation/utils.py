# utils.py – shared helpers for the HR health‑check automation
"""Utility module providing:

* Centralised logger configuration
* Typed helpers for loading configuration, reading Excel files, and writing JSON logs
* Simple type‑annotated wrappers around common I/O operations

All production code should import these helpers rather than using raw `print` or
un‑typed `open` calls.  This keeps concerns separated (config / I/O / logging) and
makes the codebase easier to test and maintain.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict
from datetime import datetime
import pandas as pd
import yaml
import os
import tempfile

# ---------------------------------------------------------------------------
# Logger configuration
# ---------------------------------------------------------------------------
LOGGER_NAME = "hr_health_check"

# Create a module‑level logger.  Applications can adjust the level via environment
# variables or by calling `utils.set_log_level(...)`.
logger = logging.getLogger(LOGGER_NAME)
if not logger.handlers:
    # Configure only once – subsequent imports reuse the same logger.
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def set_log_level(level: str | int) -> None:
    """Adjust the logger level at runtime.

    Parameters
    ----------
    level:
        Logging level name (e.g. "DEBUG") or numeric value from the ``logging``
        module.
    """
    logger.setLevel(level)

# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------
def load_config(config_path: str | Path) -> Dict[str, Any]:
    """Load a YAML configuration file and return a dictionary.

    The function validates that the file exists and raises a clear ``FileNotFoundError``
    if it cannot be located.
    """
    cfg_path = Path(config_path)
    if not cfg_path.is_file():
        logger.error("Configuration file not found: %s", cfg_path)
        raise FileNotFoundError(f"Configuration file not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    logger.debug("Loaded config from %s: %s", cfg_path, cfg)
    return cfg

# ---------------------------------------------------------------------------
# Data‑frame helpers
# ---------------------------------------------------------------------------
def read_excel(file_path: str | Path) -> pd.DataFrame:
    """Read an Excel workbook into a ``pandas.DataFrame``.

    Parameters
    ----------
    file_path:
        Path to the ``.xlsx`` file.
    """
    path = Path(file_path)
    logger.info("Reading source Excel file: %s", path)
    return pd.read_excel(path)

# ---------------------------------------------------------------------------
# JSON helpers (used for the reminder log & processed data)
# ---------------------------------------------------------------------------
def dump_json(data: Any, file_path: str | Path, *, indent: int = 2) -> None:
    """Write *data* as JSON to *file_path*.

    The directory hierarchy is created automatically.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
    logger.debug("Wrote JSON to %s", path)


def load_json(file_path: str | Path) -> Any:
    """Load JSON from *file_path*.

    Returns an empty ``dict`` if the file does not exist or is empty.
    """
    path = Path(file_path)
    if not path.is_file():
        logger.warning("JSON file not found, returning empty dict: %s", path)
        return {}
    with path.open("r", encoding="utf-8") as f:
        content = f.read().strip()
        return json.loads(content) if content else {}





# Resolve paths consistently regardless of working directory
BASE_DIR = Path(__file__).resolve().parent

def get_path(relative_path: str) -> Path:
    """Returns an absolute path relative to the project root."""
    return BASE_DIR / relative_path

def build_reminder_key(emp_id: str, due_date: str) -> str:
    """Generates a stable key that auto-resets when the due date changes."""
    clean_date = str(due_date).split("T")[0].split(" ")[0]
    return f"{emp_id}_{clean_date}"

def load_reminder_log(file_path: Path) -> dict:
    """Safely loads the JSON log, handling missing files and corruption."""
    Path(file_path)
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def save_reminder_log_atomic(data: dict, file_path: Path) -> None:
    """Writes to a temporary file first and replaces atomically to prevent corruption."""
    Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temp file in the same directory for atomic cross-filesystem replace
    with tempfile.NamedTemporaryFile("w", dir=file_path.parent, delete=False, encoding="utf-8") as tf:
        json.dump(data, tf, indent=4, default=str)
        temp_name = tf.name
        
    os.replace(temp_name, file_path)



# End of utils.py
