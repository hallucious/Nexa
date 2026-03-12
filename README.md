# AI Execution Engine (MVP Skeleton)



## Quick Start (WSL)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "Test request" > runs/new_request.md
python scripts/run_pipeline.py --dry-run --request runs/new_request.md
pytest -q
