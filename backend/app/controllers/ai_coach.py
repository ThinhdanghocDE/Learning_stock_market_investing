"""
AI Coach Controller - API endpoints cho AI Coach
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.ai_coach import (
    ChatRequest, ChatResponse,
    AnalyzeStockRequest, TradingAdviceRequest
)
from app.services.ai_coach_service import AICoachService
from app.database import get_db, get_clickhouse
from app.controllers.auth import get_current_user
from app.models.user import User
from typing import Optional

router = APIRouter(prefix="/api/ai", tags=["AI Coach"])

# Khởi tạo AI Coach service (singleton)
_ai_coach_service: Optional[AICoachService] = None

def get_ai_coach_service() -> AICoachService:
    """Get AI Coach service instance (singleton)"""
    global _ai_coach_service
    if _ai_coach_service is None:
        try:
            _ai_coach_service = AICoachService()
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Không thể khởi tạo AI Coach: {str(e)}"
            )
    return _ai_coach_service


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ch_client = Depends(get_clickhouse)
):
    """
    Chat với AI Coach
    
    - Có thể hỏi về phân tích kỹ thuật, lời khuyên đầu tư, giải thích khái niệm
    - Nếu có symbol, AI sẽ lấy OHLC data để phân tích
    - AI sẽ tự động lấy portfolio context của user để đưa ra lời khuyên phù hợp
    """
    try:
        ai_service = get_ai_coach_service()
        result = await ai_service.chat(
            question=request.question,
            user_id=current_user.id,
            symbol=request.symbol,
            ch_client=ch_client,
            db=db
        )
        return ChatResponse(**result)
    except Exception as e:
        import traceback
        error_detail = str(e) if str(e) else repr(e)
        error_traceback = traceback.format_exc()
        print(f"Error in chat_with_ai: {error_detail}")
        print(f"Traceback: {error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi chat với AI Coach: {error_detail}" if error_detail else "Lỗi không xác định"
        )


@router.post("/analyze", response_model=ChatResponse)
async def analyze_stock(
    request: AnalyzeStockRequest,
    current_user: User = Depends(get_current_user),
    ch_client = Depends(get_clickhouse),
    db: Session = Depends(get_db)
):
    """
    Phân tích stock tự động
    
    - AI sẽ tự động phân tích kỹ thuật cho symbol
    - Đánh giá xu hướng, hỗ trợ/kháng cự
    - Đưa ra khuyến nghị mua/bán
    """
    try:
        ai_service = get_ai_coach_service()
        result = await ai_service.analyze_stock(
            symbol=request.symbol,
            ch_client=ch_client,
            user_id=current_user.id,
            db=db
        )
        return ChatResponse(**result)
    except Exception as e:
        import traceback
        error_detail = str(e) if str(e) else repr(e)
        error_traceback = traceback.format_exc()
        print(f"Error in analyze_stock: {error_detail}")
        print(f"Traceback: {error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi phân tích stock: {error_detail}" if error_detail else "Lỗi không xác định"
        )


@router.post("/advice", response_model=ChatResponse)
async def get_trading_advice(
    request: TradingAdviceRequest,
    current_user: User = Depends(get_current_user),
    ch_client = Depends(get_clickhouse),
    db: Session = Depends(get_db)
):
    """
    Lấy lời khuyên trading cho một lệnh cụ thể
    
    - Phân tích lệnh BUY/SELL với số lượng và giá cụ thể
    - Đánh giá rủi ro và cơ hội
    - Đưa ra khuyến nghị
    """
    try:
        ai_service = get_ai_coach_service()
        result = await ai_service.get_trading_advice(
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            price=request.price,
            ch_client=ch_client,
            user_id=current_user.id,
            db=db
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy lời khuyên trading: {str(e)}"
        )

