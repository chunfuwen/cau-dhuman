"""Structured knowledge-base endpoints fed by the curated school_data.json.

These give the web client rich cards (college -> departments, majors ->
directions/key disciplines/courses; professor profiles; achievements) that
complement the free-form RAG chat.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app import config

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


def _load_data(request: Request) -> dict[str, Any]:
    state = request.app.state
    return state.school_data


@router.get("/kb/overview")
async def overview(request: Request) -> dict[str, Any]:
    data = _load_data(request)
    colleges = data["colleges"]
    dept_count = sum(len(c["depts"]) for c in colleges)
    major_count = sum(len(c["majors"]) for c in colleges)
    return {
        **data["overview"],
        "college_count": len(colleges),
        "dept_count": dept_count,
        "major_count": major_count,
    }


@router.get("/kb/colleges")
async def colleges(request: Request) -> dict[str, Any]:
    data = _load_data(request)
    items = []
    for c in data["colleges"]:
        items.append(
            {
                "id": c["id"],
                "name": c["name"],
                "intro": c["intro"],
                "dept_count": len(c["depts"]),
                "major_count": len(c["majors"]),
            }
        )
    return {"count": len(items), "items": items}


@router.get("/kb/colleges/{college_id}")
async def college_detail(college_id: str, request: Request) -> dict[str, Any]:
    data = _load_data(request)
    for c in data["colleges"]:
        if c["id"] == college_id:
            return c
    raise HTTPException(status_code=404, detail=f"未找到学院: {college_id}")


@router.get("/kb/majors")
async def majors(request: Request) -> dict[str, Any]:
    data = _load_data(request)
    items = []
    for c in data["colleges"]:
        for m in c["majors"]:
            items.append(
                {
                    "name": m["name"],
                    "college": c["name"],
                    "college_id": c["id"],
                    "directions": m["directions"],
                    "key_discipline": m["key_discipline"],
                }
            )
    return {"count": len(items), "items": items}


@router.get("/kb/professors")
async def professors(request: Request) -> dict[str, Any]:
    data = _load_data(request)
    return {"count": len(data["professors"]), "items": data["professors"]}


@router.get("/kb/professors/{professor_id}")
async def professor_detail(professor_id: str, request: Request) -> dict[str, Any]:
    data = _load_data(request)
    for p in data["professors"]:
        if p["id"] == professor_id:
            return p
    raise HTTPException(status_code=404, detail=f"未找到导师: {professor_id}")


@router.get("/kb/achievements")
async def achievements(request: Request) -> dict[str, Any]:
    data = _load_data(request)
    return {"count": len(data["achievements"]), "items": data["achievements"]}