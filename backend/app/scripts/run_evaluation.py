"""Compute the evaluation panel numbers and save them to data/eval/latest.json.

Run after rehearsals and before reset_demo (reset removes the demo cases the
plan and execution metrics are measured on):

    python -m app.scripts.run_evaluation
"""
from __future__ import annotations

import json

from app.config import PROJECT_ROOT, get_settings
from app.database import SessionLocal
from app.evaluation.metrics import run_all


SEED_DIR = PROJECT_ROOT / "data" / "seed"
EVAL_PATH = PROJECT_ROOT / "data" / "eval" / "latest.json"


def main() -> None:
    from app.demo.ai_cache import install_demo_llm_cache

    install_demo_llm_cache()
    with SessionLocal() as db:
        result = run_all(
            db,
            access_v1=(SEED_DIR / "access_policy_v1.md").read_text(encoding="utf-8"),
            access_v2=(SEED_DIR / "access_policy_v2.md").read_text(encoding="utf-8"),
            demo_mode=get_settings().demo_mode,
        )
    EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVAL_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nSaved to {EVAL_PATH}")


if __name__ == "__main__":
    main()
