import hashlib
from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5


@dataclass
class PolicyChunk:
    point_id: str
    evidence_id: str
    text: str
    payload: dict[str, object]


def build_policy_chunks(
    chunks: list[str],
    *,
    policy_version_id: UUID,
    policy_code: str,
    version_number: int,
    title: str,
    department: str,
    document_text: str,
) -> list[PolicyChunk]:
    content_hash = hashlib.sha256(document_text.encode("utf-8")).hexdigest()

    records = []

    for index, chunk in enumerate(chunks):
        evidence_id = f"POL-{policy_code.upper()}-V{version_number}-C{index}"

        point_id = str(
            uuid5(
                NAMESPACE_URL,
                f"{evidence_id}:{content_hash}",
            )
        )

        records.append(
            PolicyChunk(
                point_id=point_id,
                evidence_id=evidence_id,
                text=chunk,
                payload={
                    "source_type": "POLICY",
                    "policy_version_id": str(policy_version_id),
                    "policy_code": policy_code.upper(),
                    "version_number": version_number,
                    "title": title,
                    "department": department,
                    "chunk_index": index,
                    "evidence_id": evidence_id,
                    "content_hash": content_hash,
                    "text": chunk,
                },
            )
        )

    return records
