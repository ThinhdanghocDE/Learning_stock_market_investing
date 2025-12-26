"""
Authentication Controllers
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, Token, UserLogin
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from datetime import timedelta
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Dependency để lấy current user từ JWT token"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login first at /api/auth/login",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = AuthService.verify_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again at /api/auth/login",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = UserRepository.get_by_username(db, username=token_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Đăng ký user mới"""
    try:
        # Check username đã tồn tại chưa
        existing_user = UserRepository.get_by_username(db, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check email đã tồn tại chưa (nếu có)
        if user_data.email:
            existing_email = UserRepository.get_by_email(db, user_data.email)
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Tạo user mới
        user = UserRepository.create(db, user_data)
        return user
    except HTTPException:
        raise
    except Exception as e:
        # Log lỗi chi tiết để debug
        import traceback
        error_detail = str(e)
        traceback_str = traceback.format_exc()
        print(f"❌ Error in register endpoint: {error_detail}")
        print(f"Traceback: {traceback_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {error_detail}"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Đăng nhập và nhận JWT token"""
    login_data = UserLogin(username=form_data.username, password=form_data.password)
    user_info = AuthService.authenticate_user(db, login_data)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Tạo access token
    access_token = AuthService.create_access_token(
        data={"sub": user_info["username"]},
        expires_delta=timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Lấy thông tin user hiện tại"""
    return current_user


# Tỷ lệ quy đổi: 1 sao = 10,000 VND
STAR_TO_VND_RATE = 10000


@router.post("/exchange-stars")
async def exchange_stars_to_money(
    stars: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Quy đổi sao ra tiền"""
    from app.models.portfolio import Portfolio
    
    if stars <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số sao phải lớn hơn 0"
        )
    
    if stars > current_user.experience_points:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bạn chỉ có {current_user.experience_points} sao"
        )
    
    # Tính tiền quy đổi
    money = stars * STAR_TO_VND_RATE
    
    # Trừ sao
    current_user.experience_points -= stars
    
    # Cộng tiền vào portfolio
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).first()
    if portfolio:
        portfolio.cash_balance += money
    
    db.commit()
    
    return {
        "success": True,
        "stars_exchanged": stars,
        "money_received": money,
        "remaining_stars": current_user.experience_points,
        "new_balance": float(portfolio.cash_balance) if portfolio else 0,
        "message": f"Đã quy đổi {stars} sao thành {money:,.0f} VND"
    }
