from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import PolicyLinkSubjectType
from app.graphs.guardian import build_guardian_graph
from app.models import PolicyLink, PolicyVersion
from app.policy_guardian.schemas import GuardianChangeSummary


DeterministicDiffFn = Callable[[str, str], dict]
SummarizeChangesFn = Callable[
    [str, str, str, dict],
    GuardianChangeSummary,
]


class GuardianGraphError(ValueError):
    pass


@dataclass
class GuardianGraphResult:
    deterministic: dict
    summary: GuardianChangeSummary
    links: list[PolicyLink]
    impact_descriptors: list[dict]


def analyze_policy_change_via_graph(
    *,
    db: Session,
    old_version: PolicyVersion,
    new_version: PolicyVersion,
    old_text: str,
    new_text: str,
    deterministic_diff_fn: DeterministicDiffFn,
    summarize_changes_fn: SummarizeChangesFn,
) -> GuardianGraphResult:
    """
    Run Policy Guardian analysis through LangGraph.

    The graph is deliberately non-committing:
    - exact policy versions are fixed before invocation;
    - deterministic diff is preserved even if later model reasoning fails;
    - impact targets come only from existing PolicyLink rows;
    - PostgreSQL mutations/commit remain in the existing Guardian service.

    The final persist_result node packages validated graph output for the
    service to persist using its existing business logic.
    """

    loaded_links: list[PolicyLink] = []

    def load_exact_versions_fn(
        old_version_id: str,
        new_version_id: str,
    ) -> dict:
        if str(old_version.id) != str(old_version_id):
            raise GuardianGraphError(
                "Guardian graph old_version_id does not match the loaded version."
            )

        if str(new_version.id) != str(new_version_id):
            raise GuardianGraphError(
                "Guardian graph new_version_id does not match the loaded version."
            )

        return {
            "old_version_id": str(old_version.id),
            "new_version_id": str(new_version.id),
            "policy_code": old_version.policy_code,
            "old_version_number": old_version.version_number,
            "new_version_number": new_version.version_number,
            "old_content_hash": old_version.content_hash,
            "new_content_hash": new_version.content_hash,
        }

    def graph_deterministic_diff_fn(
        _versions: dict,
    ) -> dict:
        return deterministic_diff_fn(
            old_text,
            new_text,
        )

    def explain_changes_fn(
        versions: dict,
        deterministic: dict,
    ) -> dict:
        summary = summarize_changes_fn(
            versions["policy_code"],
            old_text,
            new_text,
            deterministic,
        )

        return {
            "deterministic": deterministic,
            "summary": summary.model_dump(mode="json"),
        }

    def load_policy_links_fn(
        _versions: dict,
    ) -> list[dict]:
        links = list(
            db.scalars(
                select(PolicyLink).where(
                    PolicyLink.policy_version_id == old_version.id
                )
            )
        )

        loaded_links.clear()
        loaded_links.extend(links)

        return [
            {
                "policy_link_id": str(link.id),
                "policy_version_id": str(link.policy_version_id),
                "subject_type": link.subject_type.value,
                "subject_id": str(link.subject_id),
            }
            for link in links
        ]

    def classify_impacts_fn(
        _analysis: dict,
        links: list[dict],
    ) -> list[dict]:
        """
        Classify only the target identity here.

        Risk/action decisions remain in the existing deterministic Guardian
        service helpers, which have access to live Case/Plan/Learning state.
        This prevents the LLM from inventing impacted target IDs.
        """
        descriptors: list[dict] = []

        for link in links:
            subject_type = str(link["subject_type"])

            if subject_type not in {
                PolicyLinkSubjectType.LEARNING.value,
                PolicyLinkSubjectType.PLAN.value,
            }:
                continue

            descriptors.append(
                {
                    "policy_link_id": str(link["policy_link_id"]),
                    "target_type": subject_type,
                    "target_id": str(link["subject_id"]),
                }
            )

        return descriptors

    def validate_impacts_fn(
        analysis: dict,
        impacts: list[dict],
        versions: dict,
    ) -> list[str]:
        errors: list[str] = []

        deterministic = analysis.get("deterministic") or {}
        summary_payload = analysis.get("summary") or {}

        old_hash = str(versions.get("old_content_hash") or "")
        new_hash = str(versions.get("new_content_hash") or "")

        if old_hash == new_hash:
            errors.append(
                "Old and new policy content hashes must differ."
            )

        if old_hash != new_hash:
            has_diff = bool(
                deterministic.get("added_lines")
                or deterministic.get("removed_lines")
                or deterministic.get("unified_diff")
            )
            if not has_diff:
                errors.append(
                    "Policy hashes differ but deterministic diff is empty."
                )

        try:
            GuardianChangeSummary.model_validate(summary_payload)
        except Exception as exc:
            errors.append(
                f"Guardian summary validation failed: {exc}"
            )

        allowed_targets = {
            (
                link.subject_type.value,
                str(link.subject_id),
            )
            for link in loaded_links
        }

        seen_targets: set[tuple[str, str]] = set()

        for impact in impacts:
            target = (
                str(impact.get("target_type") or ""),
                str(impact.get("target_id") or ""),
            )

            if target not in allowed_targets:
                errors.append(
                    "Guardian graph produced an impact target that is "
                    "not present in PolicyLink."
                )
                continue

            if target in seen_targets:
                errors.append(
                    "Guardian graph produced a duplicate impact target."
                )

            seen_targets.add(target)

        return errors

    def persist_result_fn(
        analysis: dict,
        impacts: list[dict],
        versions: dict,
    ) -> dict:
        # This node intentionally does not commit. It packages the validated
        # result; the existing service remains the persistence authority.
        return {
            "policy_code": versions["policy_code"],
            "old_version_id": versions["old_version_id"],
            "new_version_id": versions["new_version_id"],
            "deterministic": analysis["deterministic"],
            "summary": analysis["summary"],
            "impact_descriptors": impacts,
        }

    graph = build_guardian_graph(
        load_exact_versions_fn=load_exact_versions_fn,
        deterministic_diff_fn=graph_deterministic_diff_fn,
        explain_changes_fn=explain_changes_fn,
        load_policy_links_fn=load_policy_links_fn,
        classify_impacts_fn=classify_impacts_fn,
        validate_impacts_fn=validate_impacts_fn,
        persist_result_fn=persist_result_fn,
    )

    result = graph.invoke(
        {
            "old_version_id": str(old_version.id),
            "new_version_id": str(new_version.id),
            "correlation_id": str(new_version.id),
            "repair_count": 0,
        }
    )

    if result.get("terminal_state") == "NEEDS_HUMAN_REVIEW":
        errors = result.get("validation_errors") or []
        raise GuardianGraphError(
            "Policy Guardian LangGraph requires human review. "
            f"Errors: {'; '.join(errors)}"
        )

    final_output = result.get("final_output")
    if not final_output:
        raise GuardianGraphError(
            "Policy Guardian LangGraph returned no final output."
        )

    deterministic = dict(final_output["deterministic"])
    summary = GuardianChangeSummary.model_validate(
        final_output["summary"]
    )
    impact_descriptors = list(
        final_output.get("impact_descriptors") or []
    )

    return GuardianGraphResult(
        deterministic=deterministic,
        summary=summary,
        links=list(loaded_links),
        impact_descriptors=impact_descriptors,
    )
