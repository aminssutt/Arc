"""Run script (BE.1): `python backend/run.py` from anywhere."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn

from backend.app.settings import settings

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port)
