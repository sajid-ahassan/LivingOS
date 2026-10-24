from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy import Enum

from app import enums
from app.database import Base
from app import models  # noqa: F401


VERSIONS_DIR = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def _load(filename: str):
    path = VERSIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _migrations():
    return [_load(path.name) for path in sorted(VERSIONS_DIR.glob("[0-9]*.py"))]


def _latest_enum_checks() -> dict[str, tuple[str, ...]]:
    checks: dict[str, tuple[str, ...]] = {}
    for module in _migrations():
        checks.update(getattr(module, "ENUM_CHECKS", {}))
    return checks


def _model_enum_columns() -> dict[str, Enum]:
    return {
        f"{table.name}.{column.name}": column.type
        for table in Base.metadata.sorted_tables
        for column in table.columns
        if isinstance(column.type, Enum)
    }


def test_revision_chain_is_linear():
    migrations = _migrations()
    assert migrations[0].down_revision is None
    for previous, current in zip(migrations, migrations[1:]):
        assert current.down_revision == previous.revision


def test_baseline_creates_every_model_table():
    baseline = _load("0001_baseline.py")
    model_tables = {table.name for table in Base.metadata.sorted_tables}

    assert set(baseline.TABLES) == model_tables
    for table in baseline.TABLES:
        assert any(
            statement.strip().startswith(f"CREATE TABLE {table} (")
            for statement in baseline.STATEMENTS
        )


def test_every_enum_column_has_a_migrated_check():
    assert set(_latest_enum_checks()) == set(_model_enum_columns())


def test_migrated_checks_match_python_enums():
    checks = _latest_enum_checks()
    for key, column_type in _model_enum_columns().items():
        assert set(checks[key]) == set(column_type.enums), (
            f"{key}: app.enums changed without a migration"
        )


def test_migrated_values_fit_column_length():
    checks = _latest_enum_checks()
    for key, column_type in _model_enum_columns().items():
        assert max(len(value) for value in checks[key]) <= column_type.length, key


def test_agent_values_are_added():
    assert enums.ResourceType.AI_AGENT in enums.ResourceType
    assert enums.ResourceType.AGENT_CREDENTIAL in enums.ResourceType
    assert enums.ActionType.DOWNSCOPE in enums.ActionType
    assert enums.ActionType.GRANT_TEMPORARY in enums.ActionType
    assert enums.ResourceState.SUSPENDED in enums.ResourceState
    assert enums.ResourceState.EXPIRED in enums.ResourceState
    assert enums.CaseType.ACCESS_REQUEST in enums.CaseType
    assert enums.PolicyImpactTargetType.RESOURCE in enums.PolicyImpactTargetType
    assert enums.AuditActorType.AGENT in enums.AuditActorType


def test_downgrade_lists_drop_only_added_values():
    migration = _load("0002_agent_enums.py")
    for key, values in migration.ENUM_CHECKS.items():
        added = migration.ADDED_VALUES.get(migration.ENUM_CLASSES[key], ())
        assert set(added) <= set(values), key
