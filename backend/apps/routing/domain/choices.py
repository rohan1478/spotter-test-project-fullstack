from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"
    NO_TRAVEL = "no-travel"


RISK_CHOICES = [(risk.value, risk.value) for risk in RiskLevel]
RISK_SCORES = {risk: score for score, risk in enumerate(RiskLevel)}
WEATHER_STATUS_CHOICES = [(value, value) for value in ("available", "missing")]
