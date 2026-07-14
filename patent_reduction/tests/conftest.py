import sys
from pathlib import Path

# Allow `import patent_reduction...` when tests run from repo root.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
