"""Router for analytics endpoints."""

from collections import defaultdict
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.interaction import InteractionLog
from app.models.item import ItemRecord as Item

router = APIRouter()


@router.get("/scores")
async def get_scores_histogram(
    lab: str,
    session: AsyncSession = Depends(get_session),
):
    """Get distribution of scores in four buckets."""
    lab_number = lab.split("-")[1]
    lab_title = f"Lab {lab_number.upper()}"
    
    # Find the lab item
    lab_item = (await session.exec(
        select(Item).where(col(Item.title).contains(lab_title))
    )).first()
    
    if not lab_item:
        return [{"bucket": "0-25", "count": 0}, {"bucket": "26-50", "count": 0}, 
                {"bucket": "51-75", "count": 0}, {"bucket": "76-100", "count": 0}]
    
    # Find all task items that belong to this lab
    tasks = (await session.exec(
        select(Item).where(Item.parent_id == lab_item.id)
    )).all()
    task_ids = [t.id for t in tasks]
    
    # Query interactions for these tasks that have a score
    interactions = (await session.exec(
        select(InteractionLog).where(InteractionLog.task_id.in_(task_ids))
    )).all()
    
    # Filter interactions with scores
    scored_interactions = [i for i in interactions if i.score is not None]
    
    # Group scores into 4 buckets
    buckets = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
    for inter in scored_interactions:
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
async def get_pass_rates(
    lab: str,
    session: AsyncSession = Depends(get_session),
):
    """Get pass rates for each task in the lab."""
    lab_number = lab.split("-")[1]
    lab_title = f"Lab {lab_number.upper()}"
    
    # Find the lab item
    lab_item = (await session.exec(
        select(Item).where(col(Item.title).contains(lab_title))
    )).first()
    
    if not lab_item:
        return []
    
    # Find all task items that belong to this lab
    tasks = (await session.exec(
        select(Item).where(Item.parent_id == lab_item.id)
    )).all()
    
    result = []
    for task in tasks:
        # Get all interactions for this task
        interactions = (await session.exec(
            select(InteractionLog).where(InteractionLog.task_id == task.id)
        )).all()
        
        total = len(interactions)
        passed = len([i for i in interactions if i.score is not None and i.score >= 75])
        
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        
        result.append({
            "task": task.title,
            "pass_rate": round(pass_rate, 1)
        })
    
    return result


@router.get("/timeline")
async def get_timeline(
    lab: str,
    session: AsyncSession = Depends(get_session),
):
    """Get timeline of submissions."""
    lab_number = lab.split("-")[1]
    lab_title = f"Lab {lab_number.upper()}"
    
    # Find the lab item
    lab_item = (await session.exec(
        select(Item).where(col(Item.title).contains(lab_title))
    )).first()
    
    if not lab_item:
        return []
    
    # Find all task items that belong to this lab
    tasks = (await session.exec(
        select(Item).where(Item.parent_id == lab_item.id)
    )).all()
    task_ids = [t.id for t in tasks]
    
    # Query interactions for these tasks
    interactions = (await session.exec(
        select(InteractionLog).where(InteractionLog.task_id.in_(task_ids))
    )).all()
    
    # Group by date
    timeline = defaultdict(lambda: {"total": 0, "passed": 0})
    for inter in interactions:
        date_str = inter.timestamp.strftime("%Y-%m-%d")
        timeline[date_str]["total"] += 1
        if inter.score is not None and inter.score >= 75:
            timeline[date_str]["passed"] += 1
    
    result = []
    for date_str in sorted(timeline.keys()):
        data = timeline[date_str]
        pass_rate = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0.0
        result.append({
            "date": date_str,
            "total": data["total"],
            "passed": data["passed"],
            "pass_rate": round(pass_rate, 1)
        })
    
    return result


@router.get("/groups")
async def get_groups(
    lab: str,
    session: AsyncSession = Depends(get_session),
):
    """Get statistics grouped by group_id."""
    lab_number = lab.split("-")[1]
    lab_title = f"Lab {lab_number.upper()}"
    
    # Find the lab item
    lab_item = (await session.exec(
        select(Item).where(col(Item.title).contains(lab_title))
    )).first()
    
    if not lab_item:
        return []
    
    # Find all task items that belong to this lab
    tasks = (await session.exec(
        select(Item).where(Item.parent_id == lab_item.id)
    )).all()
    task_ids = [t.id for t in tasks]
    
    # Query interactions for these tasks
    interactions = (await session.exec(
        select(InteractionLog).where(InteractionLog.task_id.in_(task_ids))
    )).all()
    
    # Group by group_id
    groups = defaultdict(lambda: {"total": 0, "passed": 0, "scores": []})
    for inter in interactions:
        group_id = inter.group_id or "unknown"
        groups[group_id]["total"] += 1
        if inter.score is not None:
            groups[group_id]["scores"].append(inter.score)
            if inter.score >= 75:
                groups[group_id]["passed"] += 1
    
    result = []
    for group_id in sorted(groups.keys()):
        data = groups[group_id]
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0
        pass_rate = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0.0
        result.append({
            "group": group_id,
            "avg_score": round(avg_score, 1),
            "students": data["total"],
            "pass_rate": round(pass_rate, 1)
        })
    
    return result