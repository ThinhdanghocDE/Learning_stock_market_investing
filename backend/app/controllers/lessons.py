"""
Lesson Controllers
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.lesson import LessonResponse, LessonProgressResponse, LessonProgressCreate
from app.repositories.lesson_repository import LessonRepository
from app.services.lesson_service import LessonService
from app.controllers.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/lessons", tags=["Lessons"])


@router.get("", response_model=List[LessonResponse])
async def get_lessons(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Lấy danh sách lessons"""
    lessons = LessonRepository.get_all(db, skip=skip, limit=limit, active_only=active_only)
    return lessons


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db)
):
    """Lấy chi tiết lesson"""
    lesson = LessonRepository.get_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    return lesson


@router.get("/{lesson_id}/progress", response_model=LessonProgressResponse)
async def get_lesson_progress(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy progress của user cho lesson"""
    progress = LessonRepository.get_progress(db, current_user.id, lesson_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress not found"
        )
    return progress


@router.get("/{lesson_id}/with-progress")
async def get_lesson_with_progress(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy lesson kèm progress và thông tin access"""
    result = LessonService.get_lesson_with_progress(db, current_user.id, lesson_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    return {
        "lesson": result["lesson"],
        "progress": result["progress"],
        "can_access": result["can_access"],
        "access_error": result["access_error"]
    }


@router.post("/{lesson_id}/start", response_model=LessonProgressResponse)
async def start_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bắt đầu lesson"""
    progress, error = LessonService.start_lesson(db, current_user.id, lesson_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    return progress


@router.post("/{lesson_id}/complete", response_model=LessonProgressResponse)
async def complete_lesson(
    lesson_id: int,
    score: int = Query(..., ge=0, le=100, description="Score từ 0-100"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Hoàn thành lesson"""
    progress, error = LessonService.complete_lesson(db, current_user.id, lesson_id, score)
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    return progress


@router.get("/progress/all", response_model=List[LessonProgressResponse])
async def get_all_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy tất cả progress của user"""
    progress_list = LessonRepository.get_all_progress(db, current_user.id)
    return progress_list


@router.get("/{lesson_id}/chart-data")
async def get_lesson_chart_data(
    lesson_id: int,
    symbol: Optional[str] = Query(None, description="Symbol override (nếu không dùng default)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin chart data cho lesson (để frontend vẽ chart)
    Returns: symbol, start_time, end_time, interval
    """
    chart_data = LessonService.get_lesson_chart_data(db, lesson_id, symbol)
    if not chart_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson chart data not configured or symbol not found"
        )
    
    return chart_data

