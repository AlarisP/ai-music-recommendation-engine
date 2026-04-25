"""Generate one JSON model file per demo profile and a neutral default model.

Run from the project root:
    python train_models.py

Output goes to docs/data/models/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.ai_model import export_all_models

if __name__ == "__main__":
    export_all_models()
