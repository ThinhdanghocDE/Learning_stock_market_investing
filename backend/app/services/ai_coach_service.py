"""
AI Coach Service - Tích hợp Gemini 1.5 Flash API để tư vấn đầu tư
"""

import os
import time
import re
import google.generativeai as genai
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from app.repositories.portfolio_repository import PortfolioRepository, VirtualPositionRepository

class AICoachService:
    """AI Coach service sử dụng Gemini 1.5 Flash"""
    
    def __init__(self):
        """Khởi tạo Gemini client"""
        # API key hardcoded theo yêu cầu
        self.api_key = "AIzaSyBeylhRNp5cDm38CEniUNoTVWG4fk0i49w"
        
        try:
            genai.configure(api_key=self.api_key)
            # Sử dụng gemini-1.5-flash: Ổn định, tốc độ nhanh và hạn mức cao hơn bản 2.0
            # Việc khai báo model_name giúp tránh lỗi 404 trên một số phiên bản thư viện cũ
            self.model = genai.GenerativeModel(model_name='models/gemini-flash-latest')
            print("--- AI Coach Service: Đã kết nối thành công Gemini 1.5 Flash ---")
        except Exception as e:
            print(f"Lỗi khởi tạo Gemini: {e}")
            raise ValueError(f"Không thể khởi tạo Gemini client: {str(e)}")

    def _format_ohlc_data(self, ohlc_data: List[Dict]) -> str:
        """Format OHLC data thành text dễ đọc cho AI"""
        if not ohlc_data:
            return "Không có dữ liệu OHLC."
        
        # Chỉ lấy 50 nến gần nhất để tối ưu token
        recent_candles = ohlc_data[-50:] if len(ohlc_data) > 50 else ohlc_data
        
        formatted = "Dữ liệu OHLC (Gần nhất):\n"
        formatted += "Thời gian | Mở | Cao | Thấp | Đóng | Khối lượng\n"
        formatted += "-" * 60 + "\n"
        
        for candle in recent_candles:
            time_str = candle.get('time', 'N/A')
            if isinstance(time_str, str):
                time_str = time_str.replace('T', ' ').split('.')[0]
            
            formatted += f"{time_str} | {candle.get('open', 0):.2f} | {candle.get('high', 0):.2f} | {candle.get('low', 0):.2f} | {candle.get('close', 0):.2f} | {candle.get('volume', 0):,.0f}\n"
        
        return formatted

    def _format_portfolio_context(self, portfolio, positions: List) -> str:
        """Format thông tin tài khoản cho AI"""
        context = f"\nThông tin Danh mục đầu tư:\n"
        context += f"- Tiền mặt khả dụng: {float(portfolio.cash_balance):,.0f} VNĐ\n"
        context += f"- Tổng tài sản: {float(portfolio.total_value):,.0f} VNĐ\n"
        
        if positions:
            context += "\nCác cổ phiếu đang nắm giữ:\n"
            for pos in positions:
                context += f"- {pos.symbol}: SL {pos.quantity}, Giá vốn {float(pos.avg_price):,.0f} VNĐ\n"
                if hasattr(pos, 'last_price') and pos.last_price:
                    pnl = (float(pos.last_price) - float(pos.avg_price)) * pos.quantity
                    pnl_pct = ((float(pos.last_price) / float(pos.avg_price)) - 1) * 100
                    context += f"  Lãi/Lỗ: {pnl:+,.0f} VNĐ ({pnl_pct:+.2f}%)\n"
        else:
            context += "- Tài khoản hiện chưa có cổ phiếu nào.\n"
        
        return context

    def _build_prompt(self, question: str, symbol: Optional[str] = None, 
                     ohlc_data: Optional[List[Dict]] = None,
                     portfolio_context: Optional[str] = None) -> str:
        """Xây dựng nội dung yêu cầu gửi cho AI"""
        prompt = """Bạn là một chuyên gia tư vấn đầu tư chứng khoán Việt Nam (AI Coach).
Quy tắc trả lời:
1. Sử dụng tiếng Việt, phong cách chuyên nghiệp, khách quan.
2. Dựa trên dữ liệu OHLC được cung cấp để phân tích xu hướng (Trend), hỗ trợ/kháng cự.
3. Nếu có dữ liệu Portfolio, hãy đưa ra lời khuyên phù hợp với túi tiền và vị thế hiện tại.
4. Cảnh báo rủi ro về thị trường VNI khi cần thiết.

"""
        if symbol:
            prompt += f"\nMã cổ phiếu cần phân tích: {symbol}\n"
        
        if ohlc_data:
            prompt += "\n" + self._format_ohlc_data(ohlc_data) + "\n"
        
        if portfolio_context:
            prompt += portfolio_context + "\n"
        
        prompt += f"\nCÂU HỎI CỦA NGƯỜI DÙNG: {question}\n"
        prompt += "\nPHẢN HỒI CHI TIẾT:"
        
        return prompt

    def _is_stock_analysis_question(self, question: str, symbol: Optional[str] = None) -> bool:
        """Kiểm tra xem câu hỏi có liên quan đến phân tích cổ phiếu không"""
        if not symbol:
            return False
        
        # Các từ khóa cho thấy câu hỏi về phân tích cổ phiếu
        stock_keywords = [
            'phân tích', 'phân tich', 'phân tich', 'phân tích kỹ thuật',
            'xu hướng', 'xu huong', 'trend',
            'hỗ trợ', 'kháng cự', 'support', 'resistance',
            'mua', 'bán', 'buy', 'sell',
            'giá', 'price', 'giá trị',
            'cổ phiếu', 'co phieu', 'stock',
            'đầu tư', 'dau tu', 'invest',
            'nên', 'có nên', 'có nên mua', 'có nên bán',
            'đánh giá', 'danh gia', 'evaluate',
            'dự báo', 'du bao', 'forecast',
            'khuyến nghị', 'khuyen nghi', 'recommend',
            symbol.lower(),  # Tên mã cổ phiếu
        ]
        
        question_lower = question.lower()
        # Kiểm tra xem câu hỏi có chứa từ khóa nào không
        for keyword in stock_keywords:
            if keyword in question_lower:
                return True
        
        return False

    async def chat(
        self,
        question: str,
        user_id: Optional[int] = None,
        symbol: Optional[str] = None,
        ch_client = None,
        db = None
    ) -> Dict[str, Any]:
        """Gửi câu hỏi và nhận phản hồi từ AI"""
        try:
            # 1. Chỉ lấy dữ liệu OHLC nếu câu hỏi thực sự liên quan đến phân tích cổ phiếu
            ohlc_data = None
            should_analyze_stock = self._is_stock_analysis_question(question, symbol)
            
            if should_analyze_stock and symbol and ch_client:
                try:
                    from app.repositories.clickhouse_repository import ClickHouseRepository
                    ch_repo = ClickHouseRepository(ch_client)
                    end_time = datetime.now()
                    start_time = end_time - timedelta(days=14) # Lấy 14 ngày cho dữ liệu đầy đủ hơn
                    ohlc_data = ch_repo.get_ohlc_historical(
                        symbol=symbol,
                        start_time=start_time,
                        end_time=end_time,
                        interval="1m",
                        limit=100
                    )
                    print(f"✅ Lấy OHLC data cho {symbol} vì câu hỏi liên quan đến phân tích cổ phiếu")
                except Exception as e:
                    print(f"Lỗi truy vấn ClickHouse: {e}")
            else:
                if symbol:
                    print(f"⏭️ Bỏ qua OHLC data cho {symbol} vì câu hỏi không liên quan đến phân tích cổ phiếu")

            # 2. Chỉ lấy dữ liệu Portfolio nếu câu hỏi liên quan đến đầu tư/tài chính
            portfolio_context = None
            portfolio_keywords = [
                'danh mục', 'danh muc', 'portfolio',
                'tài khoản', 'tai khoan', 'account',
                'số dư', 'so du', 'balance',
                'vị thế', 'vi the', 'position',
                'lãi lỗ', 'lai lo', 'pnl', 'profit', 'loss',
                'đầu tư', 'dau tu', 'invest',
                'mua', 'bán', 'buy', 'sell',
            ]
            should_include_portfolio = any(keyword in question.lower() for keyword in portfolio_keywords)
            
            if should_include_portfolio and user_id and db:
                try:
                    portfolio = PortfolioRepository.get_or_create_portfolio(db, user_id)
                    positions = VirtualPositionRepository.get_all_by_user(db, user_id)
                    portfolio_context = self._format_portfolio_context(portfolio, positions)
                    print(f"✅ Lấy Portfolio context vì câu hỏi liên quan đến danh mục đầu tư")
                except Exception as e:
                    print(f"Lỗi truy vấn Portfolio: {e}")

            # 3. Tạo Prompt - chỉ thêm symbol nếu thực sự cần phân tích
            prompt_symbol = symbol if should_analyze_stock else None
            prompt = self._build_prompt(question, prompt_symbol, ohlc_data, portfolio_context)

            # 4. Gọi API với cơ chế tự động thử lại (Retry) khi gặp lỗi 429
            max_retries = 3
            response = None
            
            for attempt in range(max_retries):
                try:
                    # Gọi trực tiếp qua generate_content
                    response = self.model.generate_content(prompt)
                    break
                except Exception as api_error:
                    error_msg = str(api_error)
                    if "429" in error_msg or "quota" in error_msg.lower():
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 5
                            print(f"Hết định mức, đang đợi {wait_time}s rồi thử lại lần {attempt+1}...")
                            time.sleep(wait_time)
                            continue
                    raise api_error

            # 5. Xử lý kết quả trả về
            if not response or not response.text:
                return {"response": "AI không thể trả lời lúc này, vui lòng thử lại sau.", "metadata": {}}

            return {
                "response": response.text,
                "metadata": {
                    "symbol": symbol,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": "gemini-1.5-flash"
                }
            }

        except Exception as e:
            print(f"Lỗi nghiêm trọng tại AICoachService: {e}")
            return {
                "response": f"Xin lỗi, hệ thống gặp sự cố: {str(e)}",
                "metadata": {"error": str(e)}
            }

    async def analyze_stock(self, symbol: str, ch_client, user_id: Optional[int] = None, db = None):
        question = f"Phân tích kỹ thuật mã {symbol}. Đưa ra xu hướng và hỗ trợ/kháng cự quan trọng."
        return await self.chat(question, user_id, symbol, ch_client, db)

    async def get_trading_advice(self, symbol: str, side: str, quantity: int, price: float = None, ch_client = None, user_id = None, db = None):
        action = "MUA" if side.upper() == "BUY" else "BÁN"
        price_info = f"giá {price:,.0f} VNĐ" if price else "giá thị trường"
        question = f"Tôi định {action} {quantity} cổ phiếu {symbol} ở {price_info}. Lệnh này có hợp lý không?"
        return await self.chat(question, user_id, symbol, ch_client, db)