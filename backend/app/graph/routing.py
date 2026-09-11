"""Intent classification (Section 8 of the brief). Deterministic keyword matching, not an
LLM call — consistent with this project's existing bias toward deterministic, auditable logic
wherever a choice doesn't strictly require an LLM (plan.md Section 16's boundary statement).
An ambiguous message falls through to GENERAL_QUERY, which still gets a grounded answer via
the Scheme Knowledge Base's RAG search rather than failing closed.

This is a deliberate scope simplification: the brief allows an "LLM-assisted fallback for
ambiguous free text," which would sit here as an additional step if the keyword pass returns
GENERAL_QUERY and the caller wants better recall on very open-ended phrasing.
"""

INTENTS = (
    "VERIFY_DOCUMENT",
    "CHECK_DEADLINE",
    "SET_REMINDER",
    "REGISTER_GRIEVANCE",
    "CHECK_GRIEVANCE_STATUS",
    "SUBMIT_FEEDBACK",
    "REPORT_SUSPICIOUS_ACTIVITY",
    "CHANGE_LANGUAGE",
    "COMPARE_SCHEMES",
    "CHECK_ELIGIBILITY",
    "DISCOVER_SCHEME",
    "GENERAL_QUERY",
)

# Order matters: first matching intent wins, so more specific intents are listed first.
_KEYWORDS: dict[str, tuple[str, ...]] = {
    "VERIFY_DOCUMENT": ("verify document", "verify my document", "check my document", "upload"),
    "CHECK_DEADLINE": ("deadline", "last date", "closing date", "when is the last date"),
    "SET_REMINDER": ("remind me", "set a reminder", "notify me", "reminder"),
    "REGISTER_GRIEVANCE": ("file a complaint", "grievance", "register a complaint", "raise a complaint"),
    "CHECK_GRIEVANCE_STATUS": ("status of my complaint", "grievance status", "ticket status"),
    "SUBMIT_FEEDBACK": ("feedback", "suggestion"),
    "REPORT_SUSPICIOUS_ACTIVITY": ("suspicious", "report fraud", "fake document", "scam"),
    "CHANGE_LANGUAGE": ("switch language", "change language", "reply in", "speak in"),
    "COMPARE_SCHEMES": ("compare", "difference between", "which is better"),
    "CHECK_ELIGIBILITY": ("am i eligible", "eligibility", "do i qualify", "check my eligibility"),
    "DISCOVER_SCHEME": ("scheme for", "schemes for", "what schemes", "find scheme", "looking for a scheme"),
}


def detect_intent(query: str) -> str:
    text = (query or "").lower()
    for intent, keywords in _KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return intent
    return "GENERAL_QUERY"
