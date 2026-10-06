from pydantic import BaseModel


class RiskAssessRequest(BaseModel):
    threat_scenario_id: int
    impact: str
    feasibility: str
    assessed_by: str = "engineer"


class ApproveMitigationRequest(BaseModel):
    approved_by: str = "reviewer"
