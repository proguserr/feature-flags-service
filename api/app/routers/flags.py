from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.schemas import FeatureCreate, FeatureUpdate, FeatureOut, EvaluationResult
from app.cache import get_feature_cache, set_feature_cache, delete_feature_cache, publish_update
from app.services.rollout import evaluate_flag
from app.services.audit import record_audit
from app.metrics import EVALS
import json

router = APIRouter(tags=["flags"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def row_to_feature(row) -> dict:
    return {
        "key": row[0],
        "description": row[1],
        "enabled": row[2],
        "rollout_percentage": row[3],
        "target_groups": row[4] or [],
        "version": row[5],
    }

@router.get("/flags", response_model=List[FeatureOut])
def list_flags(db: Session = Depends(get_db)):
    rs = db.execute(text("SELECT key, description, enabled, rollout_percentage, target_groups, version FROM features ORDER BY key"))
    items = [row_to_feature(r) for r in rs.fetchall()]
    return items

@router.get("/flags/{key}", response_model=FeatureOut)
def get_flag(key: str, db: Session = Depends(get_db)):
    cached = get_feature_cache(key)
    if cached:
        return cached
    row = db.execute(text("SELECT key, description, enabled, rollout_percentage, target_groups, version FROM features WHERE key=:k"), {"k": key}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="flag not found")
    item = row_to_feature(row)
    set_feature_cache(key, item)
    return item

@router.post("/flags", response_model=FeatureOut, status_code=201)
def create_flag(payload: FeatureCreate, request: Request, db: Session = Depends(get_db)):
    actor = request.headers.get("X-Actor", "anonymous")
    # check exists
    existing = db.execute(text("SELECT 1 FROM features WHERE key=:k"), {"k": payload.key}).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="flag already exists")
    db.execute(
        text("""INSERT INTO features (key, description, enabled, rollout_percentage, target_groups, version)
                VALUES (:key, :description, :enabled, :rollout_percentage, :target_groups, 1)"""),
        {
            "key": payload.key,
            "description": payload.description,
            "enabled": payload.enabled,
            "rollout_percentage": payload.rollout_percentage,
            "target_groups": json.dumps([r.model_dump() for r in payload.target_groups]),
        }
    )
    db.commit()
    row = db.execute(text("SELECT key, description, enabled, rollout_percentage, target_groups, version FROM features WHERE key=:k"), {"k": payload.key}).fetchone()
    item = row_to_feature(row)
    set_feature_cache(payload.key, item)
    publish_update(payload.key)
    record_audit(db, payload.key, actor, "create", before_state=None, after_state=item)
    db.commit()
    return item

@router.put("/flags/{key}", response_model=FeatureOut)
def update_flag(key: str, payload: FeatureUpdate, request: Request, db: Session = Depends(get_db)):
    actor = request.headers.get("X-Actor", "anonymous")
    row = db.execute(text("SELECT key, description, enabled, rollout_percentage, target_groups, version FROM features WHERE key=:k"), {"k": key}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="flag not found")
    before = row_to_feature(row)

    # Merge
    description = payload.description if payload.description is not None else before["description"]
    enabled = payload.enabled if payload.enabled is not None else before["enabled"]
    rollout = payload.rollout_percentage if payload.rollout_percentage is not None else before["rollout_percentage"]
    targets = [r.model_dump() for r in payload.target_groups] if payload.target_groups is not None else before["target_groups"]
    new_version = before["version"] + 1

    db.execute(
        text("""UPDATE features
                 SET description=:description,
                     enabled=:enabled,
                     rollout_percentage=:rollout_percentage,
                     target_groups=:target_groups,
                     version=:version,
                     updated_at=NOW()
                 WHERE key=:key"""),
        {
            "description": description,
            "enabled": enabled,
            "rollout_percentage": rollout,
            "target_groups": json.dumps(targets),
            "version": new_version,
            "key": key,
        }
    )
    db.commit()
    row = db.execute(text("SELECT key, description, enabled, rollout_percentage, target_groups, version FROM features WHERE key=:k"), {"k": key}).fetchone()
    item = row_to_feature(row)
    set_feature_cache(key, item)
    publish_update(key)
    record_audit(db, key, actor, "update", before_state=before, after_state=item)
    db.commit()
    return item

@router.delete("/flags/{key}", status_code=204)
def delete_flag(key: str, request: Request, db: Session = Depends(get_db)):
    actor = request.headers.get("X-Actor", "anonymous")
    row = db.execute(text("SELECT key, description, enabled, rollout_percentage, target_groups, version FROM features WHERE key=:k"), {"k": key}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="flag not found")
    before = row_to_feature(row)
    db.execute(text("DELETE FROM features WHERE key=:k"), {"k": key})
    db.commit()
    delete_feature_cache(key)
    publish_update(key)
    record_audit(db, key, actor, "delete", before_state=before, after_state=None)
    db.commit()
    return

@router.get("/evaluate/{key}", response_model=EvaluationResult)
def evaluate(key: str, user_id: str = Query(...), request: Request = None, db: Session = Depends(get_db)):
    # Collect attributes from query params (except user_id)
    attributes = {k: v for k, v in request.query_params.items() if k != "user_id"}
    # fetch flag
    cached = get_feature_cache(key)
    if cached is None:
        row = db.execute(text("SELECT key, description, enabled, rollout_percentage, target_groups, version FROM features WHERE key=:k"), {"k": key}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="flag not found")
        flag = row_to_feature(row)
        set_feature_cache(key, flag)
    else:
        flag = cached

    enabled, reason = evaluate_flag(
        key=flag["key"],
        enabled=flag["enabled"],
        rollout_percentage=flag["rollout_percentage"],
        target_groups=flag["target_groups"],
        user_id=user_id,
        attributes=attributes,
    )
    EVALS.labels(key, str(enabled)).inc()
    return {"key": key, "enabled": enabled, "reason": reason, "version": flag["version"]}
