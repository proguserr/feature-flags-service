from pydantic import BaseModel, Field, conint
from typing import List, Optional, Any, Dict

class TargetRule(BaseModel):
    attr: str = Field(..., description="attribute name, e.g., country, tier")
    op: str = Field(..., description="operator: eq, ne, in, nin")
    value: Any

class FeatureCreate(BaseModel):
    key: str
    description: Optional[str] = None
    enabled: bool = False
    rollout_percentage: conint(ge=0, le=100) = 0
    target_groups: List[TargetRule] = []

class FeatureUpdate(BaseModel):
    description: Optional[str] = None
    enabled: Optional[bool] = None
    rollout_percentage: Optional[conint(ge=0, le=100)] = None
    target_groups: Optional[List[TargetRule]] = None

class FeatureOut(BaseModel):
    key: str
    description: Optional[str] = None
    enabled: bool
    rollout_percentage: int
    target_groups: List[TargetRule]
    version: int

class EvaluationResult(BaseModel):
    key: str
    enabled: bool
    reason: str
    version: int
