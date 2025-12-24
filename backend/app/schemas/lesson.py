"""
Lesson Schemas (Pydantic)
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class LessonBase(BaseModel):
    """Base lesson schema"""
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    content: Optional[str] = None
    sample_symbols: Optional[List[str]] = None
    difficulty_level: str = Field(default="BEGINNER", pattern="^(BEGINNER|INTERMEDIATE|ADVANCED)$")
    required_points: int = Field(default=0, ge=0)
    order_index: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)
    # Chart configuration
    chart_start_time: Optional[datetime] = Field(None, description="Thời gian bắt đầu để vẽ chart")
    chart_end_time: Optional[datetime] = Field(None, description="Thời gian kết thúc để vẽ chart")
    chart_interval: Optional[str] = Field("1m", description="Interval cho chart: 1m, 5m, 1h, 1d")
    chart_default_symbol: Optional[str] = Field(None, description="Symbol mặc định cho chart")


class LessonCreate(LessonBase):
    """Schema để tạo lesson mới"""
    pass


class LessonUpdate(BaseModel):
    """Schema để update lesson"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    content: Optional[str] = None
    sample_symbols: Optional[List[str]] = None
    difficulty_level: Optional[str] = Field(None, pattern="^(BEGINNER|INTERMEDIATE|ADVANCED)$")
    required_points: Optional[int] = Field(None, ge=0)
    order_index: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    chart_start_time: Optional[datetime] = None
    chart_end_time: Optional[datetime] = None
    chart_interval: Optional[str] = Field(None, description="Interval: 1m, 5m, 1h, 1d")
    chart_default_symbol: Optional[str] = None


class LessonResponse(LessonBase):
    """Schema để trả về lesson"""
    id: int
    created_at: datetime
    updated_at: datetime
    # Override difficulty_level để không có pattern validation (đã có validator)
    difficulty_level: str = Field(default="BEGINNER")
    
    @field_validator('difficulty_level', mode='before')
    @classmethod
    def validate_difficulty_level(cls, v):
        """Validate và normalize difficulty_level từ database"""
        if v is None:
            return "BEGINNER"
        v_str = str(v).upper()
        # Map các giá trị cũ hoặc không hợp lệ từ database
        mapping = {
            "1": "BEGINNER",
            "2": "INTERMEDIATE",
            "3": "ADVANCED",
            "BEGINNER": "BEGINNER",
            "INTERMEDIATE": "INTERMEDIATE",
            "ADVANCED": "ADVANCED",
        }
        return mapping.get(v_str, "BEGINNER")
    
    class Config:
        from_attributes = True


class LessonProgressBase(BaseModel):
    """Base lesson progress schema"""
    status: str = Field(default="NOT_STARTED", pattern="^(NOT_STARTED|IN_PROGRESS|COMPLETED|LOCKED)$")
    score: int = Field(default=0, ge=0, le=100)
    progress_data: Optional[str] = None  # JSON string


class LessonProgressCreate(BaseModel):
    """Schema để tạo lesson progress"""
    lesson_id: int


class LessonProgressUpdate(BaseModel):
    """Schema để update lesson progress"""
    status: Optional[str] = Field(None, pattern="^(NOT_STARTED|IN_PROGRESS|COMPLETED|LOCKED)$")
    score: Optional[int] = Field(None, ge=0, le=100)
    progress_data: Optional[str] = None


class LessonProgressResponse(LessonProgressBase):
    """Schema để trả về lesson progress"""
    id: int
    user_id: int
    lesson_id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_accessed_at: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

