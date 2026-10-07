"""Write build_info.json (bundled into the launcher; shown on the About page).

Uses the environment variables GitHub Actions provides.  Run locally with no
arguments to produce a "development" stamp.  Contains no secrets.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

info = {
    "build": os.environ.get("GITHUB_RUN_NUMBER", ""),
    "commit": os.environ.get("GITHUB_SHA", "")[:7],
    "ref": os.environ.get("GITHUB_REF_NAME", ""),
    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
}
path = Path(__file__).resolve().parent.parent / "build_info.json"
path.write_text(json.dumps(info, indent=2), encoding="utf-8")
print(f"Wrote {path}: {info}")
