"""
AI Coach Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class ChatRequest(BaseModel):
    """Request schema cho chat với AI Coach"""
    question: str = Field(..., description="Câu hỏi của người dùng")
    symbol: Optional[str] = Field(None, description="Mã chứng khoán (để lấy OHLC context)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Phân tích xu hướng của ACB",
                "symbol": "ACB"
            }
        }


class ChatResponse(BaseModel):
    """Response schema cho chat với AI Coach"""
    response: str = Field(..., description="Câu trả lời từ AI Coach")
    metadata: Dict[str, Any] = Field(..., description="Metadata về response")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Dựa trên phân tích kỹ thuật...",
                "metadata": {
                    "symbol": "ACB",
                    "has_ohlc_data": True,
                    "ohlc_count": 100,
                    "has_portfolio_context": True,
                    "timestamp": "2025-01-01T10:00:00"
                }
            }
        }


class AnalyzeStockRequest(BaseModel):
    """Request schema cho phân tích stock"""
    symbol: str = Field(..., description="Mã chứng khoán cần phân tích")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "ACB"
            }
        }


class TradingAdviceRequest(BaseModel):
    """Request schema cho lời khuyên trading"""
    symbol: str = Field(..., description="Mã chứng khoán")
    side: str = Field(..., pattern="^(BUY|SELL)$", description="BUY hoặc SELL")
    quantity: int = Field(..., gt=0, description="Số lượng")
    price: Optional[float] = Field(None, description="Giá (cho LIMIT order)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "ACB",
                "side": "BUY",
                "quantity": 100,
                "price": 25000.0
            }
        }

