"""
Lesson Service - Business Logic
"""

from sqlalchemy.orm import Session
from app.repositories.lesson_repository import LessonRepository
from app.repositories.user_repository import UserRepository
from app.models.lesson import Lesson, LessonProgress
from app.schemas.lesson import LessonCreate, LessonUpdate, QuizSubmission, QuizResult
from typing import Optional, Dict, List, Any


class LessonService:
    """Lesson service"""
    
    @staticmethod
    def can_access_lesson(db: Session, user_id: int, lesson: Lesson) -> tuple[bool, Optional[str]]:
        """
        Kiểm tra user có thể truy cập lesson không
        Logic:
        - BEGINNER: Luôn mở khóa
        - INTERMEDIATE: Cần hoàn thành TẤT CẢ bài học BEGINNER
        - ADVANCED: Cần hoàn thành TẤT CẢ bài học INTERMEDIATE
        Returns: (can_access, error_message)
        """
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return False, "User not found"
        
        if not lesson.is_active:
            return False, "Lesson is not active"
        
        difficulty = lesson.difficulty_level
        
        # BEGINNER: Luôn có thể truy cập
        if difficulty == "BEGINNER":
            return True, None
        
        # INTERMEDIATE: Cần hoàn thành tất cả BEGINNER
        if difficulty == "INTERMEDIATE":
            # Lấy tất cả bài học BEGINNER đang active
            beginner_lessons = LessonRepository.get_by_difficulty(db, "BEGINNER")
            if beginner_lessons:
                # Kiểm tra user đã hoàn thành tất cả chưa
                for bl in beginner_lessons:
                    progress = LessonRepository.get_progress(db, user_id, bl.id)
                    if not progress or progress.status != "COMPLETED":
                        return False, f"Bạn cần hoàn thành tất cả bài học Cơ bản trước. Hãy hoàn thành bài '{bl.title}'."
            return True, None
        
        # ADVANCED: Cần hoàn thành tất cả INTERMEDIATE
        if difficulty == "ADVANCED":
            # Lấy tất cả bài học INTERMEDIATE đang active
            intermediate_lessons = LessonRepository.get_by_difficulty(db, "INTERMEDIATE")
            if intermediate_lessons:
                # Kiểm tra user đã hoàn thành tất cả chưa
                for il in intermediate_lessons:
                    progress = LessonRepository.get_progress(db, user_id, il.id)
                    if not progress or progress.status != "COMPLETED":
                        return False, f"Bạn cần hoàn thành tất cả bài học Trung bình trước. Hãy hoàn thành bài '{il.title}'."
            return True, None
        
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
    def submit_quiz(
        db: Session,
        user_id: int,
        lesson_id: int,
        submission: QuizSubmission
    ) -> tuple[Optional[QuizResult], Optional[str]]:
        """
        Nộp quiz và tính điểm
        Returns: (quiz_result, error_message)
        """
        lesson = LessonRepository.get_by_id(db, lesson_id)
        if not lesson:
            return None, "Lesson not found"
        
        if not lesson.quiz_data:
            return None, "This lesson has no quiz"
        
        quiz_data = lesson.quiz_data
        questions = quiz_data.get("questions", [])
        passing_score = quiz_data.get("passing_score", 8)
        
        if not questions:
            return None, "Quiz has no questions"
        
        # Tính điểm
        correct_count = 0
        correct_answers = []
        explanations = []
        
        for i, question in enumerate(questions):
            correct_answer = question.get("correct_answer", 0)
            correct_answers.append(correct_answer)
            explanations.append(question.get("explanation"))
            
            # Kiểm tra đáp án của user
            if i < len(submission.answers):
                if submission.answers[i] == correct_answer:
                    correct_count += 1
        
        # Kiểm tra pass/fail
        passed = correct_count >= passing_score
        
        # Tính sao thưởng - chỉ cộng nếu pass lần đầu (chưa từng pass)
        progress = LessonService.get_or_create_progress(db, user_id, lesson_id)
        is_first_pass = passed and not progress.quiz_passed and progress.stars_earned == 0
        stars_earned = lesson.stars_reward if is_first_pass else 0
        
        # Cập nhật progress
        progress = LessonRepository.update_quiz_progress(
            db, progress, correct_count, passed, lesson.stars_reward if is_first_pass else 0
        )
        
        # Cộng experience points nếu pass lần đầu
        if is_first_pass:
            UserRepository.update_experience_points(db, user_id, stars_earned)
        
        return QuizResult(
            score=correct_count,
            total=len(questions),
            passed=passed,
            stars_earned=stars_earned,
            correct_answers=correct_answers,
            explanations=explanations
        ), None
    
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
    
    # === Admin Methods ===
    
    @staticmethod
    def create_lesson(db: Session, lesson_data: LessonCreate) -> Lesson:
        """Tạo lesson mới (Admin)"""
        return LessonRepository.create(db, lesson_data)
    
    @staticmethod
    def update_lesson(
        db: Session,
        lesson_id: int,
        lesson_data: LessonUpdate
    ) -> tuple[Optional[Lesson], Optional[str]]:
        """Cập nhật lesson (Admin)"""
        lesson = LessonRepository.get_by_id(db, lesson_id)
        if not lesson:
            return None, "Lesson not found"
        
        lesson = LessonRepository.update(db, lesson, lesson_data)
        return lesson, None
    
    @staticmethod
    def delete_lesson(db: Session, lesson_id: int) -> tuple[bool, Optional[str]]:
        """Xóa lesson (Admin)"""
        lesson = LessonRepository.get_by_id(db, lesson_id)
        if not lesson:
            return False, "Lesson not found"
        
        LessonRepository.delete(db, lesson)
        return True, None
