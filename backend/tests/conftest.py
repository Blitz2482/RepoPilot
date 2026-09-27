import os
import sys
from pathlib import Path

os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("MOCK_BOB", "true")
os.environ.setdefault("LOCAL_EMBEDDINGS", "true")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
