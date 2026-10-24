from __future__ import annotations

import hashlib
from uuid import uuid4

import pytest

from app.enums import PolicyState
from app.models import PolicyVersion
from app.scripts.reindex_policies import (
    PolicyReindexError,
    select_versions_to_reindex,
    verify_content_hash,
)


def _version(code: str, number: int, status: PolicyState, text: str = "rules") -> PolicyVersion:
    return PolicyVersion(
        id=uuid4(),
        policy_code=code,
        title=f"{code.title()} Policy",
        version_number=number,
        status=status,
        department="GLOBAL",
        content_text=text,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def test_reindexes_v1_of_each_seed_policy_including_archived():
    access_v1 = _version("ACCESS", 1, PolicyState.ARCHIVED)
    access_v2 = _version("ACCESS", 2, PolicyState.CURRENT)
    equipment = _version("EQUIPMENT", 1, PolicyState.CURRENT)
    offboarding = _version("OFFBOARDING", 1, PolicyState.CURRENT)
    other = _version("TRAVEL", 1, PolicyState.CURRENT)

    selected = select_versions_to_reindex(
        [offboarding, other, access_v2, equipment, access_v1]
    )

    assert selected == [access_v1, equipment, offboarding]


def test_policy_not_ingested_yet_is_skipped():
    selected = select_versions_to_reindex(
        [_version("ACCESS", 1, PolicyState.CURRENT)],
        codes=["ACCESS", "AGENT"],
    )
    assert [version.policy_code for version in selected] == ["ACCESS"]


def test_matching_text_passes_hash_check():
    verify_content_hash(_version("ACCESS", 1, PolicyState.CURRENT, "1. Rule one."))


def test_altered_text_is_refused():
    version = _version("ACCESS", 1, PolicyState.CURRENT, "1. Rule one.")
    version.content_text = "1. Rule one, quietly changed."
    with pytest.raises(PolicyReindexError, match="content hash"):
        verify_content_hash(version)
