# Deterministic risk matrix - NOT AI. Risk levels must be consistent and explainable every time.
RISK_MATRIX = {
    ("LOW", "LOW"): "LOW",
    ("LOW", "MEDIUM"): "LOW",
    ("LOW", "HIGH"): "MEDIUM",
    ("MEDIUM", "LOW"): "LOW",
    ("MEDIUM", "MEDIUM"): "MEDIUM",
    ("MEDIUM", "HIGH"): "HIGH",
    ("HIGH", "LOW"): "MEDIUM",
    ("HIGH", "MEDIUM"): "HIGH",
    ("HIGH", "HIGH"): "CRITICAL",
}


def compute_risk_level(impact: str, feasibility: str) -> str:
    return RISK_MATRIX.get((impact.upper(), feasibility.upper()), "MEDIUM")
