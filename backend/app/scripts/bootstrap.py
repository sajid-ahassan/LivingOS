"""One command to make an empty or existing environment demo-ready.

1. alembic upgrade head      (fresh database: creates the schema)
2. Qdrant collection + index (fresh cluster)
3. seed policies             (ACCESS, EQUIPMENT, OFFBOARDING, AGENT V1)
4. seed company              (85 people, 24 agents, story characters)

Every step is idempotent, so it is safe on the Supabase demo database too.
In OFFLINE mode the policy embeddings must already be in data/demo_cache/
(run this once in LIVE or CACHED_AI mode to record them).

Run: python -m app.scripts.bootstrap
"""
from __future__ import annotations

from alembic import command
from alembic.config import Config

from app.config import PROJECT_ROOT


BACKEND_ROOT = PROJECT_ROOT / "backend"


def migrate() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    command.upgrade(config, "head")


def main() -> None:
    from app.rag.qdrant_collections import ensure_policy_collection, ensure_policy_version_index
    from app.scripts import ingest_seed_policies, seed_company

    print("1/4 database schema"); migrate()
    print("2/4 vector store"); print(" ", ensure_policy_collection()); print(" ", ensure_policy_version_index())
    print("3/4 seed policies"); ingest_seed_policies.main()
    print("4/4 demo company"); seed_company.main()
    print("\nReady. Start the API, the frontend and (optionally) the MCP gateway.")


if __name__ == "__main__":
    main()
