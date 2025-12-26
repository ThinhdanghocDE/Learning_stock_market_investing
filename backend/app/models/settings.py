from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base

class HomepageSettings(Base):
    __tablename__ = "homepage_settings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Hero Section
    hero_headline = Column(Text, nullable=False, default="Học đầu tư thông minh<br />cùng AI Mentor")
    hero_subheadline = Column(Text, nullable=False, default="Thực hành giao dịch với tiền ảo, dữ liệu thật. AI phân tích mỗi quyết định và hướng dẫn bạn trở thành nhà đầu tư bài bản.")
    hero_cta_text = Column(String(100), nullable=False, default="Vào Dashboard")
    hero_banners = Column(Text, nullable=True, default="[]") # JSON list of URLs
    
    # About Section
    about_title = Column(String(200), nullable=False, default="Về Mindvest Learn")
    about_mission = Column(String(200), nullable=False, default="Sứ mệnh của chúng tôi là dân chủ hóa kiến thức đầu tư")
    about_description_1 = Column(Text, nullable=False, default="Chúng tôi nhận thấy rào cản lớn nhất của người mới bắt đầu đầu tư chứng khoán không phải là thiếu vốn, mà là thiếu kiến thức và kinh nghiệm thực chiến.")
    about_description_2 = Column(Text, nullable=False, default="Mindvest Learn được xây dựng để giải quyết vấn đề đó. Chúng tôi cung cấp môi trường giả lập an toàn, dữ liệu thực tế và đặc biệt là sự đồng hành của AI.")
    about_image_url = Column(String(500), nullable=True)
    
    # Stats (JSON or separate columns? keeping it simple for now)
    stat_1_value = Column(String(50), default="10M+")
    stat_1_label = Column(String(100), default="Tiền ảo để thực hành")
    stat_2_value = Column(String(50), default="1000+")
    stat_2_label = Column(String(100), default="Mã cổ phiếu VN")
    stat_3_value = Column(String(50), default="24/7")
    stat_3_label = Column(String(100), default="AI hỗ trợ")

    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
