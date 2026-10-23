from langchain_core.prompts import ChatPromptTemplate


LEARNING_CANDIDATE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are the LivingOps organizational-learning engine.\n"
            "Convert one verified manager correction into a reusable operational lesson.\n"
            "Current policy is authoritative. The lesson is advisory and must never weaken policy.\n"
            "Preserve the decision pattern, not names, IDs, dates, resource keys, or private facts.\n"
            "Do not generalize beyond the supplied case type, department, role, and sensitivity.\n"
            "Use only the supplied structured difference and current policy evidence.\n"
            "Return only the requested structured object.""",
        ),
        (
            "human",
            """CASE_SCOPE:\n{case_scope}\n\n"
            "CORRECTION_SUMMARY:\n{correction_summary}\n\n"
            "STRUCTURED_DIFFERENCE:\n{structured_diff}\n\n"
            "CURRENT_POLICY_EVIDENCE:\n{policy_evidence}\n""",
        ),
    ]
)
