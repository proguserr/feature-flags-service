import hashlib
from typing import Dict, List

def _stable_hash(value: str) -> int:
    # 0..100
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    pct = int(digest[:8], 16) % 101
    return pct

def match_target_groups(target_groups: List[dict], attributes: Dict[str, str]) -> bool:
    if not target_groups:
        return True
    for rule in target_groups:
        attr = rule.get("attr")
        op = rule.get("op", "eq")
        val = rule.get("value")
        candidate = attributes.get(attr)
        if candidate is None:
            continue
        if op == "eq" and str(candidate) == str(val):
            return True
        if op == "ne" and str(candidate) != str(val):
            return True
        if op == "in" and str(candidate) in set(map(str, val if isinstance(val, list) else [val])):
            return True
        if op == "nin" and str(candidate) not in set(map(str, val if isinstance(val, list) else [val])):
            return True
    return False

def evaluate_flag(key: str, enabled: bool, rollout_percentage: int, target_groups: List[dict], user_id: str, attributes: Dict[str, str]) -> (bool, str):
    if not enabled:
        return False, "disabled"
    if not match_target_groups(target_groups, attributes):
        return False, "no-target-match"
    pct = _stable_hash(f"{key}:{user_id}")
    if pct <= rollout_percentage:
        return True, f"rollout-{rollout_percentage}%"
    return False, f"rollout-miss-{rollout_percentage}%"
