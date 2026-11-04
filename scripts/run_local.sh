#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m pipeline.ingest --max-new 5
python -m pipeline.build_site
python3 -m http.server 8765 -d site
