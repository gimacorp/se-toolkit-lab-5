"""Router for analytics endpoints.

Each endpoint performs SQL aggregation queries on the interaction data
populated by the ETL pipeline. All endpoints require a `lab` query
parameter to filter results by lab (e.g., "lab-01").
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.interaction import InteractionLog
from app.models.item import ItemRecord
from app.models.learner import Learner

router = APIRouter()


@router.get("/scores")
def get_scores_histogram(lab: str) -> List[dict]:
    # Transform "lab-04" → "Lab 04"
    lab_number = lab.split("-")[1]
    lab_title = f"Lab {lab_number.upper()}"
    
    # Find the lab item
    lab_item = session.query(Item).filter(
        Item.title.contains(lab_title)
    ).first()
    
    if not lab_item:
        return [{"bucket": k, "count": 0} for k in ["0-25", "26-50", "51-75", "76-100"]]
    
    # Find all task items that belong to this lab
    tasks = session.query(Item).filter(
        Item.parent_id == lab_item.id
    ).all()
    task_ids = [t.id for t in tasks]
    
    # Query interactions for these tasks that have a score
    interactions = session.query(Interaction).filter(
        Interaction.task_id.in_(task_ids),
        Interaction.score.isnot(None)
    ).all()
    
    # Group scores into 4 buckets
    buckets = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
    for inter in interactions:
        if inter.score <= 25:
            buckets["0-25"] += 1
        elif inter.score <= 50:
            buckets["26-50"] += 1
        elif inter.score <= 75:
            buckets["51-75"] += 1
        else:
            buckets["76-100"] += 1
    
    return [{"bucket": k, "count": v} for k, v in buckets.items()]
@router.get("/pass-rates")
def get_pass_rates(lab: str) -> List[dict]:
    # Transform "lab-04" → "Lab 04"
    lab_number = lab.split("-")[1]
    lab_title = f"Lab {lab_number.upper()}"
    
    # Find the lab item
    lab_item = session.query(Item).filter(
        Item.title.contains(lab_title)
    ).first()
    
    if not lab_item:
        return []
    
    # Find all task items that belong to this lab
    tasks = session.query(Item).filter(
        Item.parent_id == lab_item.id
    ).all()
    
    result = []
    for task in tasks:
        # Count total interactions for this task
        total = session.query(Interaction).filter(
            Interaction.task_id == task.id
        ).count()
        
        # Count passed interactions (score >= 75)
        passed = session.query(Interaction).filter(
            Interaction.task_id == task.id,
            Interaction.score >= 75
        ).count()
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        result.append({
            "task": task.title,
            "pass_rate": round(pass_rate, 2)
        })
    
    return result


@router.get("/timeline")
def get_timeline(lab: str) -> List[dict]:
    # Transform "lab-04" → "Lab 04"
    lab_number = lab.split("-")[1]
    lab_title = f"Lab {lab_number.upper()}"
    
    # Find the lab item
    lab_item = session.query(Item).filter(
        Item.title.contains(lab_title)
    ).first()
    
    if not lab_item:
        return []
    
    # Find all task items that belong to this lab
    tasks = session.query(Item).filter(
        Item.parent_id == lab_item.id
    ).all()
    task_ids = [t.id for t in tasks]
    
    # Query interactions for these tasks
    interactions = session.query(Interaction).filter(
        Interaction.task_id.in_(task_ids),
        Interaction.score.isnot(None)
    ).all()
    
    # Group by date
    timeline = {}
    for inter in interactions:
        date_str = inter.timestamp.strftime("%Y-%m-%d")
        if date_str not in timeline:
            timeline[date_str] = {"total": 0, "passed": 0}
        
        timeline[date_str]["total"] += 1
        if inter.score >= 75:
            timeline[date_str]["passed"] += 1
    
    result = []
    for date_str in sorted(timeline.keys()):
        data = timeline[date_str]
        pass_rate = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0
        result.append({
            "date": date_str,
            "total": data["total"],
            "passed": data["passed"],
            "pass_rate": round(pass_rate, 2)
        })
    
    return result


@router.get("/groups")
def get_groups(lab: str) -> List[dict]:
    # Transform "lab-04" → "Lab 04"
    lab_number = lab.split("-")[1]
    lab_title = f"Lab {lab_number.upper()}"
    
    # Find the lab item
    lab_item = session.query(Item).filter(
        Item.title.contains(lab_title)
    ).first()
    
    if not lab_item:
        return []
    
    # Find all task items that belong to this lab
    tasks = session.query(Item).filter(
        Item.parent_id == lab_item.id
    ).all()
    task_ids = [t.id for t in tasks]
    
    # Query interactions for these tasks
    interactions = session.query(Interaction).filter(
        Interaction.task_id.in_(task_ids),
        Interaction.score.isnot(None)
    ).all()
    
    # Group by group_id
    groups = {}
    for inter in interactions:
        group_id = inter.group_id
        if group_id not in groups:
            groups[group_id] = {"total": 0, "passed": 0}
        
        groups[group_id]["total"] += 1
        if inter.score >= 75:
            groups[group_id]["passed"] += 1
    
    result = []
    for group_id in sorted(groups.keys()):
        data = groups[group_id]
        pass_rate = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0
        result.append({
            "group_id": group_id,
            "total": data["total"],
            "passed": data["passed"],
            "pass_rate": round(pass_rate, 2)
        })
    
    return result