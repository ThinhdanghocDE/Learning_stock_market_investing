"""
Trading Hours Service - Kiểm tra giờ giao dịch
"""

from datetime import datetime, time, timedelta
from typing import Tuple, Optional
try:
    import pytz
except ImportError:
    pytz = None


class TradingHoursService:
    """Service để kiểm tra giờ giao dịch chứng khoán Việt Nam"""
    
    # Giờ giao dịch: 9:00-11:30 và 13:00-15:00 (GMT+7)
    MORNING_START = time(9, 0)
    MORNING_END = time(11, 30)
    AFTERNOON_START = time(13, 0)
    AFTERNOON_END = time(15, 0)
    
    @staticmethod
    def _get_vn_timezone():
        """Lấy timezone Việt Nam"""
        if pytz:
            return pytz.timezone('Asia/Ho_Chi_Minh')
        # Fallback: UTC+7 offset
        from datetime import timezone, timedelta
        return timezone(timedelta(hours=7))
    
    @staticmethod
    def is_trading_day(dt: datetime) -> bool:
        """
        Kiểm tra có phải ngày giao dịch không (Thứ 2-6)
        Returns: True nếu là Thứ 2-6
        """
        weekday = dt.weekday()  # 0=Monday, 6=Sunday
        return weekday < 5  # Monday to Friday
    
    @staticmethod
    def is_trading_hours(dt: datetime) -> bool:
        """
        Kiểm tra có trong giờ giao dịch không
        Returns: True nếu trong giờ giao dịch (9:00-11:30 hoặc 13:00-15:00)
        """
        if not TradingHoursService.is_trading_day(dt):
            return False
        
        current_time = dt.time()
        
        # Check morning session: 9:00-11:30
        if TradingHoursService.MORNING_START <= current_time <= TradingHoursService.MORNING_END:
            return True
        
        # Check afternoon session: 13:00-15:00
        if TradingHoursService.AFTERNOON_START <= current_time <= TradingHoursService.AFTERNOON_END:
            return True
        
        return False
    
    @staticmethod
    def get_current_vn_time() -> datetime:
        """Lấy thời gian hiện tại theo múi giờ Việt Nam (GMT+7)"""
        vn_tz = TradingHoursService._get_vn_timezone()
        return datetime.now(vn_tz)
    
    @staticmethod
    def can_trade_now(trading_mode: str = "REALTIME") -> Tuple[bool, Optional[str]]:
        """
        Kiểm tra có thể đặt lệnh ngay không
        Returns: (can_trade, reason)
        """
        if trading_mode == "PRACTICE":
            # Practice mode: không cần kiểm tra giờ giao dịch
            return True, None
        
        # Real-time mode: kiểm tra giờ giao dịch
        current_time = TradingHoursService.get_current_vn_time()
        
        if not TradingHoursService.is_trading_day(current_time):
            return False, "Chỉ giao dịch từ Thứ 2 đến Thứ 6"
        
        if not TradingHoursService.is_trading_hours(current_time):
            return False, "Ngoài giờ giao dịch. Giờ giao dịch: 9:00-11:30 và 13:00-15:00"
        
        return True, None
    
    @staticmethod
    def get_next_trading_session() -> Optional[datetime]:
        """Lấy thời gian bắt đầu phiên giao dịch tiếp theo"""
        current_time = TradingHoursService.get_current_vn_time()
        current_date = current_time.date()
        current_time_only = current_time.time()
        
        # Nếu đang trong giờ giao dịch, return None
        if TradingHoursService.is_trading_hours(current_time):
            return None
        
        vn_tz = TradingHoursService._get_vn_timezone()
        
        # Nếu trước 9:00, return 9:00 hôm nay (nếu là ngày giao dịch)
        if current_time_only < TradingHoursService.MORNING_START:
            if TradingHoursService.is_trading_day(current_time):
                return datetime.combine(current_date, TradingHoursService.MORNING_START).replace(tzinfo=vn_tz)
        
        # Nếu giữa 11:30-13:00, return 13:00 hôm nay
        if TradingHoursService.MORNING_END < current_time_only < TradingHoursService.AFTERNOON_START:
            if TradingHoursService.is_trading_day(current_time):
                return datetime.combine(current_date, TradingHoursService.AFTERNOON_START).replace(tzinfo=vn_tz)
        
        # Nếu sau 15:00 hoặc cuối tuần, tìm ngày giao dịch tiếp theo
        next_date = current_date
        for _ in range(7):  # Tối đa 7 ngày
            next_date = next_date + timedelta(days=1)
            next_dt = datetime.combine(next_date, TradingHoursService.MORNING_START).replace(tzinfo=vn_tz)
            if TradingHoursService.is_trading_day(next_dt):
                return next_dt
        
        return None

