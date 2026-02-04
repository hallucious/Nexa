# AI 7-Gate Pipeline (MVP Skeleton)

7-Gate 상태머신 기반 AI 협업 파이프라인 스켈레톤.

## Quick Start (WSL)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "Test request" > runs/new_request.md
python scripts/run_pipeline.py --dry-run --request runs/new_request.md
pytest -q
