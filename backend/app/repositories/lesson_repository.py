"""
Lesson Repository - Data Access Layer
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.lesson import Lesson, LessonProgress
from typing import List, Optional


class LessonRepository:
    """Lesson repository"""
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[Lesson]:
        """Lấy danh sách lessons"""
        query = db.query(Lesson)
        if active_only:
            query = query.filter(Lesson.is_active == True)
        return query.order_by(Lesson.order_index, Lesson.id).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_id(db: Session, lesson_id: int) -> Optional[Lesson]:
        """Lấy lesson theo ID"""
        return db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    @staticmethod
    def get_progress(db: Session, user_id: int, lesson_id: int) -> Optional[LessonProgress]:
        """Lấy progress của user cho lesson"""
        return db.query(LessonProgress).filter(
            and_(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id == lesson_id
            )
        ).first()
    
    @staticmethod
    def get_all_progress(db: Session, user_id: int) -> List[LessonProgress]:
        """Lấy tất cả progress của user"""
        return db.query(LessonProgress).filter(
            LessonProgress.user_id == user_id
        ).all()
    
    @staticmethod
    def create_progress(db: Session, user_id: int, lesson_id: int) -> LessonProgress:
        """Tạo progress mới cho user"""
        progress = LessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            status="NOT_STARTED"
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
        return progress
    
    @staticmethod
    def update_progress(
        db: Session,
        progress: LessonProgress,
        status: Optional[str] = None,
        score: Optional[int] = None
    ) -> LessonProgress:
        """Cập nhật progress"""
        if status:
            progress.status = status
        if score is not None:
            progress.score = score
        
        db.commit()
        db.refresh(progress)
        return progress
    
    @staticmethod
    def start_lesson(db: Session, progress: LessonProgress) -> LessonProgress:
        """Bắt đầu lesson"""
        from datetime import datetime
        progress.status = "IN_PROGRESS"
        progress.started_at = datetime.utcnow()
        progress.last_accessed_at = datetime.utcnow()
        db.commit()
        db.refresh(progress)
        return progress
    
    @staticmethod
    def complete_lesson(db: Session, progress: LessonProgress, score: int) -> LessonProgress:
        """Hoàn thành lesson"""
        from datetime import datetime
        progress.status = "COMPLETED"
        progress.score = score
        progress.completed_at = datetime.utcnow()
        progress.last_accessed_at = datetime.utcnow()
        db.commit()
        db.refresh(progress)
        return progress

