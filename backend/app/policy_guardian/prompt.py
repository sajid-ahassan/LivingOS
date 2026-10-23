from langchain_core.prompts import ChatPromptTemplate


GUARDIAN_CHANGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are the LivingOps Policy Change Guardian.
Compare ONLY the exact old and new policy text supplied below.
Do not use general knowledge and do not invent rules.
Summarize operationally meaningful additions, removals, and modifications.
Focus on effects on access, equipment, training, approvals, employee lifecycle,
security, and operational execution.
Classify overall risk as LOW, MEDIUM, or HIGH.
HIGH means the change could invalidate access decisions, security-sensitive
actions, or approved organizational learning.
Return only the requested structured object.""",
        ),
        (
            "human",
            """POLICY_CODE: {policy_code}

DETERMINISTIC_DIFF:
{deterministic_diff}

OLD_POLICY:
{old_policy}

NEW_POLICY:
{new_policy}
""",
        ),
    ]
)
