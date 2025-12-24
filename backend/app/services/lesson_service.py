"""
Lesson Service - Business Logic
"""

from sqlalchemy.orm import Session
from app.repositories.lesson_repository import LessonRepository
from app.repositories.user_repository import UserRepository
from app.models.lesson import Lesson, LessonProgress
from typing import Optional, Dict


class LessonService:
    """Lesson service"""
    
    @staticmethod
    def can_access_lesson(db: Session, user_id: int, lesson: Lesson) -> tuple[bool, Optional[str]]:
        """
        Kiểm tra user có thể truy cập lesson không
        Returns: (can_access, error_message)
        """
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return False, "User not found"
        
        if not lesson.is_active:
            return False, "Lesson is not active"
        
        if user.experience_points < lesson.required_points:
            return False, f"Required {lesson.required_points} experience points. You have {user.experience_points}"
        
        return True, None
    
    @staticmethod
    def get_or_create_progress(db: Session, user_id: int, lesson_id: int) -> LessonProgress:
        """Lấy hoặc tạo progress cho user"""
        progress = LessonRepository.get_progress(db, user_id, lesson_id)
        if not progress:
            progress = LessonRepository.create_progress(db, user_id, lesson_id)
        return progress
    
    @staticmethod
    def start_lesson(db: Session, user_id: int, lesson_id: int) -> tuple[Optional[LessonProgress], Optional[str]]:
        """
        Bắt đầu lesson
        Returns: (progress, error_message)
        """
        lesson = LessonRepository.get_by_id(db, lesson_id)
        if not lesson:
            return None, "Lesson not found"
        
        can_access, error = LessonService.can_access_lesson(db, user_id, lesson)
        if not can_access:
            return None, error
        
        progress = LessonService.get_or_create_progress(db, user_id, lesson_id)
        
        if progress.status == "COMPLETED":
            return progress, None  # Đã hoàn thành, có thể xem lại
        
        if progress.status == "NOT_STARTED":
            progress = LessonRepository.start_lesson(db, progress)
        
        return progress, None
    
    @staticmethod
    def complete_lesson(
        db: Session,
        user_id: int,
        lesson_id: int,
        score: int
    ) -> tuple[Optional[LessonProgress], Optional[str]]:
        """
        Hoàn thành lesson và cập nhật experience points
        Returns: (progress, error_message)
        """
        lesson = LessonRepository.get_by_id(db, lesson_id)
        if not lesson:
            return None, "Lesson not found"
        
        progress = LessonRepository.get_progress(db, user_id, lesson_id)
        if not progress:
            return None, "Progress not found. Please start the lesson first"
        
        if progress.status == "COMPLETED":
            return progress, "Lesson already completed"
        
        # Validate score
        score = max(0, min(100, score))  # Clamp between 0-100
        
        # Complete lesson
        progress = LessonRepository.complete_lesson(db, progress, score)
        
        # Calculate experience points (score * 10)
        points_earned = score * 10
        UserRepository.update_experience_points(db, user_id, points_earned)
        
        return progress, None
    
    @staticmethod
    def get_lesson_with_progress(
        db: Session,
        user_id: int,
        lesson_id: int
    ) -> Optional[Dict]:
        """Lấy lesson kèm progress của user"""
        lesson = LessonRepository.get_by_id(db, lesson_id)
        if not lesson:
            return None
        
        progress = LessonRepository.get_progress(db, user_id, lesson_id)
        
        can_access, error = LessonService.can_access_lesson(db, user_id, lesson)
        
        return {
            "lesson": lesson,
            "progress": progress,
            "can_access": can_access,
            "access_error": error
        }
    
    @staticmethod
    def get_lesson_chart_data(
        db: Session,
        lesson_id: int,
        symbol: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Lấy thông tin chart data cho lesson
        Returns: {
            "symbol": str,
            "start_time": datetime,
            "end_time": datetime,
            "interval": str
        }
        """
        lesson = LessonRepository.get_by_id(db, lesson_id)
        if not lesson:
            return None
        
        # Sử dụng symbol từ parameter hoặc lesson config
        chart_symbol = symbol or lesson.chart_default_symbol
        if not chart_symbol:
            # Fallback: dùng symbol đầu tiên trong sample_symbols
            if lesson.sample_symbols and len(lesson.sample_symbols) > 0:
                chart_symbol = lesson.sample_symbols[0]
            else:
                return None  # Không có symbol để vẽ chart
        
        # Sử dụng thời gian từ lesson config
        if not lesson.chart_start_time or not lesson.chart_end_time:
            return None  # Lesson chưa có chart config
        
        return {
            "symbol": chart_symbol,
            "start_time": lesson.chart_start_time,
            "end_time": lesson.chart_end_time,
            "interval": lesson.chart_interval or "1m"
        }

