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

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Check if current user is admin"""
    if current_user.role != 'ADMIN':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Admin mới có quyền truy cập"
        )
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
            "role": u.role,
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


@router.put("/users/{user_id}/role")
async def admin_update_user_role(
    user_id: int,
    role: str = Query(..., description="Role mới: ADMIN hoặc USER"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Cập nhật role của user"""
    if role not in ['ADMIN', 'USER']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role phải là 'ADMIN' hoặc 'USER'"
        )
    
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Không cho phép tự thay đổi role của chính mình
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể thay đổi role của chính mình"
        )
    
    user.role = role
    db.commit()
    
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "message": f"Đã cập nhật role thành {role}"
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
    from sqlalchemy import func, case
    
    # Get completion stats per lesson
    lesson_stats = db.query(
        Lesson.id,
        Lesson.title,
        Lesson.difficulty_level,
        func.count(LessonProgress.id).label("total_attempts"),
        func.sum(
            case(
                (LessonProgress.status == "COMPLETED", 1),
                else_=0
            )
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
            "completions": int(stat.completions or 0),
            "avg_quiz_score": round(float(stat.avg_quiz_score or 0), 2)
        }
        for stat in lesson_stats
    ]


@router.get("/stats/trading")
async def admin_get_trading_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """[Admin] Lấy thống kê giao dịch"""
    from app.models.portfolio import VirtualOrder, Portfolio
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Total orders
    total_orders = db.query(VirtualOrder).count()
    filled_orders = db.query(VirtualOrder).filter(VirtualOrder.status == "FILLED").count()
    
    # Total trading value (sum of filled_price * filled_quantity)
    total_value_result = db.query(
        func.sum(VirtualOrder.filled_price * VirtualOrder.filled_quantity)
    ).filter(VirtualOrder.status == "FILLED").scalar()
    total_trading_value = float(total_value_result or 0)
    
    # New users this month
    first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_month = db.query(User).filter(User.created_at >= first_of_month).count()
    
    # Active traders (users with at least 1 order)
    active_traders = db.query(func.count(func.distinct(VirtualOrder.user_id))).scalar() or 0
    
    return {
        "total_orders": total_orders,
        "filled_orders": filled_orders,
        "total_trading_value": total_trading_value,
        "new_users_month": new_users_month,
        "active_traders": active_traders
    }


@router.get("/stats/leaderboard")
async def admin_get_leaderboard(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
):
    """[Admin] Lấy bảng xếp hạng top traders theo lợi nhuận"""
    from app.models.portfolio import Portfolio
    from sqlalchemy import desc
    
    # Get top portfolios by total_value (profit = total_value - initial 10M)
    INITIAL_BALANCE = 10000000  # 10M VND
    
    top_portfolios = db.query(
        Portfolio.user_id,
        Portfolio.total_value,
        Portfolio.cash_balance,
        User.username
    ).join(User, Portfolio.user_id == User.id).order_by(
        desc(Portfolio.total_value)
    ).limit(limit).all()
    
    return [
        {
            "rank": idx + 1,
            "user_id": p.user_id,
            "username": p.username,
            "total_value": float(p.total_value),
            "profit": float(p.total_value) - INITIAL_BALANCE,
            "profit_percent": round((float(p.total_value) - INITIAL_BALANCE) / INITIAL_BALANCE * 100, 2)
        }
        for idx, p in enumerate(top_portfolios)
    ]


@router.get("/stats/popular-stocks")
async def admin_get_popular_stocks(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
):
    """[Admin] Lấy danh sách mã cổ phiếu được giao dịch nhiều nhất"""
    from app.models.portfolio import VirtualOrder
    from sqlalchemy import func, desc, case
    
    # Get most traded stocks
    popular_stocks = db.query(
        VirtualOrder.symbol,
        func.count(VirtualOrder.id).label("total_orders"),
        func.sum(VirtualOrder.filled_quantity).label("total_volume"),
        func.sum(
            case(
                (VirtualOrder.side == "BUY", 1),
                else_=0
            )
        ).label("buy_orders"),
        func.sum(
            case(
                (VirtualOrder.side == "SELL", 1),
                else_=0
            )
        ).label("sell_orders")
    ).filter(
        VirtualOrder.status == "FILLED"
    ).group_by(
        VirtualOrder.symbol
    ).order_by(
        desc("total_orders")
    ).limit(limit).all()
    
    return [
        {
            "symbol": stock.symbol,
            "total_orders": stock.total_orders,
            "total_volume": int(stock.total_volume or 0),
            "buy_orders": int(stock.buy_orders or 0),
            "sell_orders": int(stock.sell_orders or 0)
        }
        for stock in popular_stocks
    ]

