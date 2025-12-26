"""
Admin Controllers - Quản lý bài học và users
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.lesson import LessonResponse, LessonCreate, LessonUpdate
from app.services.lesson_service import LessonService
from app.repositories.lesson_repository import LessonRepository
from app.repositories.user_repository import UserRepository
from app.controllers.auth import get_current_user
from app.models.user import User
from pydantic import BaseModel


router = APIRouter(prefix="/api/admin", tags=["Admin"])


# === Response Models ===

class UserListResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    experience_points: int
    created_at: str
    last_login: Optional[str] = None
    
    class Config:
        from_attributes = True


class AdminStatsResponse(BaseModel):
    total_users: int
    total_lessons: int
    active_lessons: int
    total_completions: int


# === Helper: Check Admin ===
# TODO: Implement proper admin role check
# For now, we'll check if user exists

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Check if current user is admin"""
    # TODO: Add proper admin check (e.g., is_admin field in User model)
    # For now, allow all authenticated users
    return current_user


# === Lesson Management ===

@router.get("/lessons", response_model=List[LessonResponse])
async def admin_get_lessons(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False),  # Admin sees all
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Lấy danh sách tất cả lessons"""
    lessons = LessonRepository.get_all(db, skip=skip, limit=limit, active_only=active_only)
    return lessons


@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
async def admin_get_lesson(
    lesson_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Lấy chi tiết lesson"""
    lesson = LessonRepository.get_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    return lesson


@router.post("/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_lesson(
    lesson_data: LessonCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Tạo lesson mới"""
    lesson = LessonService.create_lesson(db, lesson_data)
    return lesson


@router.put("/lessons/{lesson_id}", response_model=LessonResponse)
async def admin_update_lesson(
    lesson_id: int,
    lesson_data: LessonUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Cập nhật lesson"""
    lesson, error = LessonService.update_lesson(db, lesson_id, lesson_data)
    if error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error
        )
    return lesson


@router.delete("/lessons/{lesson_id}")
async def admin_delete_lesson(
    lesson_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Xóa lesson"""
    success, error = LessonService.delete_lesson(db, lesson_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error
        )
    return {"message": "Lesson deleted successfully"}


# === User Management ===

@router.get("/users")
async def admin_get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Lấy danh sách users"""
    users = db.query(User).offset(skip).limit(limit).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "experience_points": u.experience_points,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login": u.last_login.isoformat() if u.last_login else None
        }
        for u in users
    ]


@router.get("/users/{user_id}")
async def admin_get_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Lấy thông tin user"""
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user's lesson progress
    progress_list = LessonRepository.get_all_progress(db, user_id)
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "experience_points": user.experience_points,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "lesson_progress": [
            {
                "lesson_id": p.lesson_id,
                "status": p.status,
                "quiz_score": p.quiz_score,
                "quiz_passed": p.quiz_passed,
                "stars_earned": p.stars_earned
            }
            for p in progress_list
        ]
    }


@router.put("/users/{user_id}/experience")
async def admin_update_user_experience(
    user_id: int,
    points: int = Query(..., description="New experience points value"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Cập nhật experience points của user"""
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Set absolute value (not increment)
    user.experience_points = max(0, points)
    db.commit()
    
    return {
        "id": user.id,
        "username": user.username,
        "experience_points": user.experience_points
    }


# === Statistics ===

@router.get("/stats", response_model=AdminStatsResponse)
async def admin_get_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Lấy thống kê tổng quan"""
    from app.models.lesson import Lesson, LessonProgress
    
    total_users = db.query(User).count()
    total_lessons = db.query(Lesson).count()
    active_lessons = db.query(Lesson).filter(Lesson.is_active == True).count()
    total_completions = db.query(LessonProgress).filter(LessonProgress.status == "COMPLETED").count()
    
    return AdminStatsResponse(
        total_users=total_users,
        total_lessons=total_lessons,
        active_lessons=active_lessons,
        total_completions=total_completions
    )


@router.get("/stats/lessons")
async def admin_get_lesson_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Lấy thống kê theo bài học"""
    from app.models.lesson import Lesson, LessonProgress
    from sqlalchemy import func
    
    # Get completion stats per lesson
    lesson_stats = db.query(
        Lesson.id,
        Lesson.title,
        Lesson.difficulty_level,
        func.count(LessonProgress.id).label("total_attempts"),
        func.sum(
            func.cast(LessonProgress.status == "COMPLETED", db.bind.dialect.type_descriptor(type(1)))
        ).label("completions"),
        func.avg(LessonProgress.quiz_score).label("avg_quiz_score")
    ).outerjoin(
        LessonProgress, Lesson.id == LessonProgress.lesson_id
    ).group_by(
        Lesson.id, Lesson.title, Lesson.difficulty_level
    ).all()
    
    return [
        {
            "id": stat.id,
            "title": stat.title,
            "difficulty_level": stat.difficulty_level,
            "total_attempts": stat.total_attempts or 0,
            "completions": stat.completions or 0,
            "avg_quiz_score": round(float(stat.avg_quiz_score or 0), 2)
        }
        for stat in lesson_stats
    ]
