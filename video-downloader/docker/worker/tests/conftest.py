import sys
from pathlib import Path

# Allow importing worker modules that use flat imports (e.g. `from ssl_adapter import ...`).
WORKER_DIR = Path(__file__).resolve().parents[1]
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))
