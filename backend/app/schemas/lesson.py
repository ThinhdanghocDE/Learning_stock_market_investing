"""
Lesson Schemas (Pydantic)
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# === Content Section Types ===

class TextSection(BaseModel):
    """Text/Markdown section"""
    type: str = "text"
    content: str


class VideoSection(BaseModel):
    """YouTube video section"""
    type: str = "video"
    url: str
    title: Optional[str] = None


class ImageSection(BaseModel):
    """Image section"""
    type: str = "image"
    url: str
    caption: Optional[str] = None


class ChartPracticeSection(BaseModel):
    """Chart practice section"""
    type: str = "chart_practice"
    symbol: str
    start_date: str  # YYYY-MM-DD
    duration_days: int = 7
    instructions: Optional[str] = None


# === Quiz Types ===

class QuizQuestion(BaseModel):
    """Single quiz question"""
    question: str
    options: List[str]  # 4 options A, B, C, D
    correct_answer: int  # Index of correct answer (0-3)
    explanation: Optional[str] = None


class QuizData(BaseModel):
    """Quiz data structure"""
    questions: List[QuizQuestion]
    passing_score: int = 8  # Minimum score to pass (out of total questions)
    total_questions: int = 10


class QuizSubmission(BaseModel):
    """Quiz submission from user"""
    answers: List[int]  # List of selected answer indices


class QuizResult(BaseModel):
    """Quiz result"""
    score: int
    total: int
    passed: bool
    stars_earned: int
    correct_answers: List[int]  # Correct answer indices
    explanations: List[Optional[str]]  # Explanations for each question


# === Lesson Schemas ===

class LessonBase(BaseModel):
    """Base lesson schema"""
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    content: Optional[Dict[str, Any]] = None  # JSONB content
    quiz_data: Optional[Dict[str, Any]] = None  # JSONB quiz
    sample_symbols: Optional[List[str]] = None
    difficulty_level: str = Field(default="BEGINNER", pattern="^(BEGINNER|INTERMEDIATE|ADVANCED)$")
    required_points: int = Field(default=0, ge=0)
    order_index: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)
    stars_reward: int = Field(default=1000, description="BEGINNER=1000, INTERMEDIATE=2000, ADVANCED=3000")
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
    content: Optional[Dict[str, Any]] = None
    quiz_data: Optional[Dict[str, Any]] = None
    sample_symbols: Optional[List[str]] = None
    difficulty_level: Optional[str] = Field(None, pattern="^(BEGINNER|INTERMEDIATE|ADVANCED)$")
    required_points: Optional[int] = Field(None, ge=0)
    order_index: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    stars_reward: Optional[int] = None
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


# === Lesson Progress Schemas ===

class LessonProgressBase(BaseModel):
    """Base lesson progress schema"""
    status: str = Field(default="NOT_STARTED", pattern="^(NOT_STARTED|IN_PROGRESS|COMPLETED|LOCKED)$")
    score: int = Field(default=0, ge=0, le=100)
    progress_data: Optional[str] = None  # JSON string
    quiz_score: Optional[int] = None
    quiz_attempts: int = 0
    quiz_passed: bool = False
    stars_earned: int = 0


class LessonProgressCreate(BaseModel):
    """Schema để tạo lesson progress"""
    lesson_id: int


class LessonProgressUpdate(BaseModel):
    """Schema để update lesson progress"""
    status: Optional[str] = Field(None, pattern="^(NOT_STARTED|IN_PROGRESS|COMPLETED|LOCKED)$")
    score: Optional[int] = Field(None, ge=0, le=100)
    progress_data: Optional[str] = None
    quiz_score: Optional[int] = None
    quiz_attempts: Optional[int] = None
    quiz_passed: Optional[bool] = None
    stars_earned: Optional[int] = None


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


# === Combined Response ===

class LessonWithProgressResponse(BaseModel):
    """Lesson kèm theo progress của user"""
    lesson: LessonResponse
    progress: Optional[LessonProgressResponse] = None
    can_access: bool = True
    access_error: Optional[str] = None
