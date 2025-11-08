from dataclasses import dataclass

@dataclass
class Feature:
    key: str
    description: str
    enabled: bool
    rollout_percentage: int
    target_groups: list
    version: int
