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
from app.models.learner import Learner

router = APIRouter()


@router.get("/scores")
async def get_scores_histogram(
    lab: str,
    session: AsyncSession = Depends(get_session),
):
    """Get distribution of scores in four buckets."""
    lab_number = lab.split("-")[1]
    lab_title = f"Lab {lab_number.upper()}"
    
    lab_item = (await session.exec(
        select(Item).where(col(Item.title).contains(lab_title))
    )).first()
    
    if not lab_item:
        return [{"bucket": "0-25", "count": 0}, {"bucket": "26-50", "count": 0}, 
                {"bucket": "51-75", "count": 0}, {"bucket": "76-100", "count": 0}]
    
    tasks = (await session.exec(
        select(Item).where(Item.parent_id == lab_item.id)
    )).all()
    task_ids = [t.id for t in tasks]
    
    interactions = (await session.exec(
        select(InteractionLog).where(InteractionLog.item_id.in_(task_ids))
    )).all()
    
    scored_interactions = [i for i in interactions if i.score is not None]
    
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
    
    lab_item = (await session.exec(
        select(Item).where(col(Item.title).contains(lab_title))
    )).first()
    
    if not lab_item:
        return []
    
    tasks = (await session.exec(
        select(Item).where(Item.parent_id == lab_item.id)
    )).all()
    
    result = []
    for task in tasks:
        interactions = (await session.exec(
            select(InteractionLog).where(InteractionLog.item_id == task.id)
        )).all()
        
        total = len(interactions)
        passed = len([i for i in interactions if i.score is not None and i.score >= 75])
        
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        
        scored_interactions = [i for i in interactions if i.score is not None]
        avg_score = sum(i.score for i in scored_interactions) / len(scored_interactions) if scored_interactions else 0.0
        
        result.append({
            "task": task.title,
            "avg_score": round(avg_score, 1),
            "attempts": total
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
    
    lab_item = (await session.exec(
        select(Item).where(col(Item.title).contains(lab_title))
    )).first()
    
    if not lab_item:
        return []
    
    tasks = (await session.exec(
        select(Item).where(Item.parent_id == lab_item.id)
    )).all()
    task_ids = [t.id for t in tasks]
    
    interactions = (await session.exec(
        select(InteractionLog).where(InteractionLog.item_id.in_(task_ids))
    )).all()
    
    timeline = defaultdict(lambda: {"submissions": 0, "passed": 0})
    for inter in interactions:
        date_str = inter.created_at.strftime("%Y-%m-%d")
        timeline[date_str]["submissions"] += 1
        if inter.score is not None and inter.score >= 75:
            timeline[date_str]["passed"] += 1
    
    result = []
    for date_str in sorted(timeline.keys()):
        data = timeline[date_str]
        total = data["submissions"]
        passed = data["passed"]
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        result.append({
            "date": date_str,
            "submissions": data["submissions"],
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
    
    lab_item = (await session.exec(
        select(Item).where(col(Item.title).contains(lab_title))
    )).first()
    
    if not lab_item:
        return []
    
    tasks = (await session.exec(
        select(Item).where(Item.parent_id == lab_item.id)
    )).all()
    task_ids = [t.id for t in tasks]
    
    # JOIN InteractionLog with Learner to get student_group
    stmt = select(InteractionLog, Learner.student_group).join(
        Learner, InteractionLog.learner_id == Learner.id
    ).where(InteractionLog.item_id.in_(task_ids))
    
    results = (await session.exec(stmt)).all()
    
    # Group by student_group
    groups_data = defaultdict(lambda: {"scores": [], "passed": 0, "students": set()})
    
    for interaction, student_group in results:
        groups_data[student_group]["students"].add(interaction.learner_id)
        if interaction.score is not None:
            groups_data[student_group]["scores"].append(interaction.score)
            if interaction.score >= 75:
                groups_data[student_group]["passed"] += 1
    
    result = []
    for group_name in sorted(groups_data.keys()):
        data = groups_data[group_name]
        total = len(data["scores"])
        passed = data["passed"]
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        
        result.append({
            "group": group_name,
            "avg_score": round(avg_score, 1),
            "students": len(data["students"]),
            "pass_rate": round(pass_rate, 1)
        })
    
    return result