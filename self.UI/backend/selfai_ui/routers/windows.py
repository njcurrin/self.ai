import logging
import uuid
import json
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from selfai_ui.config import DATA_DIR

WINDOWS_FILE = Path(DATA_DIR) / "job-windows.json"