SENSITIVE_KEYWORDS = (
    "transfer money", "send funds", "delete permanently",
    "change security policy", "export secrets", "withdraw"
)

def classify_risk(text: str) -> str:
    normalized = text.casefold()
    if any(term in normalized for term in SENSITIVE_KEYWORDS):
        return "high"
    return "unclassified"
