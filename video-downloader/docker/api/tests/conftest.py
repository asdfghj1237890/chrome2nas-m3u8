import sys
from pathlib import Path

# Allow importing api modules that use flat imports.
API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))
