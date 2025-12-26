"""
Lesson Models
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Lesson(Base):
    """Lesson model"""
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    # JSONB content với cấu trúc linh hoạt
    # Format: {"sections": [{"type": "text|video|image|chart_practice", ...}]}
    content = Column(JSONB, nullable=True)
    # Quiz data
    # Format: {"questions": [...], "passing_score": 8, "total_questions": 10}
    quiz_data = Column(JSONB, nullable=True)
    sample_symbols = Column(ARRAY(String), nullable=True)  # Danh sách mã mẫu
    difficulty_level = Column(String(20), default="BEGINNER", nullable=False)  # BEGINNER, INTERMEDIATE, ADVANCED
    required_points = Column(Integer, default=0, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # Số sao thưởng khi hoàn thành: BEGINNER=1000, INTERMEDIATE=2000, ADVANCED=3000
    stars_reward = Column(Integer, default=1000, nullable=False)
    # Chart configuration cho practice mode
    chart_start_time = Column(DateTime(timezone=True), nullable=True)  # Thời gian bắt đầu để vẽ chart
    chart_end_time = Column(DateTime(timezone=True), nullable=True)  # Thời gian kết thúc để vẽ chart
    chart_interval = Column(String(10), default="1m", nullable=True)  # Interval: 1m, 5m, 1h, 1d
    chart_default_symbol = Column(String(10), nullable=True)  # Symbol mặc định cho chart
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    progress = relationship("LessonProgress", back_populates="lesson", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Lesson(id={self.id}, title={self.title}, stars_reward={self.stars_reward})>"


class LessonProgress(Base):
    """Lesson Progress model"""
    __tablename__ = "lesson_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="NOT_STARTED", nullable=False)  # NOT_STARTED, IN_PROGRESS, COMPLETED, LOCKED
    score = Column(Integer, default=0, nullable=False)  # 0-100
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    progress_data = Column(Text, nullable=True)  # JSON string
    # Quiz tracking
    quiz_score = Column(Integer, nullable=True)  # Điểm quiz (0-10)
    quiz_attempts = Column(Integer, default=0, nullable=False)  # Số lần thử
    quiz_passed = Column(Boolean, default=False, nullable=False)  # Đã qua quiz chưa
    stars_earned = Column(Integer, default=0, nullable=False)  # Sao đã nhận
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="lesson_progress")
    lesson = relationship("Lesson", back_populates="progress")
    
    def __repr__(self):
        return f"<LessonProgress(user_id={self.user_id}, lesson_id={self.lesson_id}, status={self.status}, quiz_passed={self.quiz_passed})>"


