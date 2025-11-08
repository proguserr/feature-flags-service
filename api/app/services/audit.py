from sqlalchemy import text
from sqlalchemy.orm import Session
import json

def record_audit(db: Session, feature_key: str, actor: str, action: str, before_state: dict, after_state: dict):
    db.execute(
        text(
            """INSERT INTO audits (feature_key, actor, action, before_state, after_state)
            VALUES (:feature_key, :actor, :action, :before_state, :after_state)"""
        ),
        {
            "feature_key": feature_key,
            "actor": actor,
            "action": action,
            "before_state": before_state and json.dumps(before_state),
            "after_state": after_state and json.dumps(after_state),
        },
    )
