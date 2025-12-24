"""
User Repository - Data Access Layer
"""

import hashlib
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRepository:
    """User repository"""
    
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        """Lấy user theo ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_by_username(db: Session, username: str) -> User | None:
        """Lấy user theo username"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        """Lấy user theo email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def _preprocess_password(password: str) -> str:
        """
        Preprocess password trước khi hash bằng bcrypt.
        Hash bằng SHA256 trước để tránh giới hạn 72 bytes của bcrypt.
        Đây là cách phổ biến để xử lý password dài.
        """
        # Hash password bằng SHA256 trước (32 bytes binary)
        # Dùng digest() thay vì hexdigest() để có 32 bytes thay vì 64 bytes hex
        # Sau đó encode base64 để có string an toàn cho bcrypt
        import base64
        sha256_hash_bytes = hashlib.sha256(password.encode('utf-8')).digest()
        # Encode base64 để có string (44 ký tự, ~44 bytes)
        sha256_hash = base64.b64encode(sha256_hash_bytes).decode('utf-8')
        return sha256_hash
    
    @staticmethod
    def create(db: Session, user_data: UserCreate) -> User:
        """Tạo user mới"""
        # Hash password bằng SHA256 trước, rồi mới bcrypt
        # Điều này cho phép password dài bao nhiêu cũng được
        preprocessed_password = UserRepository._preprocess_password(user_data.password)
        hashed_password = pwd_context.hash(preprocessed_password)
        
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password,
            experience_points=0
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        # Hash password bằng SHA256 trước, giống như khi tạo
        preprocessed_password = UserRepository._preprocess_password(plain_password)
        return pwd_context.verify(preprocessed_password, hashed_password)
    
    @staticmethod
    def update_experience_points(db: Session, user_id: int, points: int) -> User | None:
        """Cập nhật experience points"""
        user = UserRepository.get_by_id(db, user_id)
        if user:
            user.experience_points += points
            db.commit()
            db.refresh(user)
        return user

