from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.settings import HomepageSettings
from app.schemas.settings import HomepageSettingsResponse, HomepageSettingsUpdate
from app.controllers.auth import get_current_user

router = APIRouter(prefix="/api/homepage", tags=["Homepage"])

import json

@router.get("", response_model=HomepageSettingsResponse)
async def get_homepage_settings(db: Session = Depends(get_db)):
    """Public endpoint to get homepage settings"""
    settings = db.query(HomepageSettings).first()
    
    if not settings:
        return HomepageSettingsResponse(
            id=0,
            hero_headline="Học đầu tư thông minh<br />cùng AI Mentor",
            hero_subheadline="Thực hành giao dịch với tiền ảo, dữ liệu thật...",
            hero_cta_text="Vào Dashboard",
            hero_banners=[],
            about_title="Về Mindvest Learn",
            about_mission="Sứ mệnh của chúng tôi...",
            about_description_1="Mô tả 1...",
            about_description_2="Mô tả 2...",
            about_image_url=None,
            stat_1_value="10M+",
            stat_1_label="Tiền ảo",
            stat_2_value="1000+",
            stat_2_label="Mã cổ phiếu",
            stat_3_value="24/7",
            stat_3_label="AI hỗ trợ",
            updated_at=None
        )

    # Safely parse hero_banners
    banners = []
    if settings.hero_banners:
        if isinstance(settings.hero_banners, list):
            banners = settings.hero_banners
        elif isinstance(settings.hero_banners, str):
            try:
                banners = json.loads(settings.hero_banners)
            except:
                banners = []
    
    return HomepageSettingsResponse(
        id=settings.id,
        hero_headline=settings.hero_headline,
        hero_subheadline=settings.hero_subheadline,
        hero_cta_text=settings.hero_cta_text,
        hero_banners=banners,
        about_title=settings.about_title,
        about_mission=settings.about_mission,
        about_description_1=settings.about_description_1,
        about_description_2=settings.about_description_2,
        about_image_url=settings.about_image_url,
        stat_1_value=settings.stat_1_value,
        stat_1_label=settings.stat_1_label,
        stat_2_value=settings.stat_2_value,
        stat_2_label=settings.stat_2_label,
        stat_3_value=settings.stat_3_value,
        stat_3_label=settings.stat_3_label,
        updated_at=settings.updated_at
    )

@router.put("/admin", response_model=HomepageSettingsResponse)
async def update_homepage_settings(
    settings_update: HomepageSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin endpoint to update homepage settings"""
    # Check for admin role
    if current_user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền này")

    settings = db.query(HomepageSettings).first()
    
    # Prepare update data, converting list to JSON string
    update_data = settings_update.dict(exclude_unset=True)
    
    if 'hero_banners' in update_data:
        update_data['hero_banners'] = json.dumps(update_data['hero_banners'])

    if not settings:
        settings = HomepageSettings(**update_data)
        db.add(settings)
    else:
        for key, value in update_data.items():
            setattr(settings, key, value)
    
    try:
        db.commit()
        db.refresh(settings)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database commit error: {str(e)}")
    
    # Safely parse banners for response
    banners = []
    if settings.hero_banners:
        if isinstance(settings.hero_banners, list):
             banners = settings.hero_banners
        else:
            try:
                banners = json.loads(settings.hero_banners)
            except:
                banners = []

    return HomepageSettingsResponse(
        id=settings.id,
        hero_headline=settings.hero_headline,
        hero_subheadline=settings.hero_subheadline,
        hero_cta_text=settings.hero_cta_text,
        hero_banners=banners,
        about_title=settings.about_title,
        about_mission=settings.about_mission,
        about_description_1=settings.about_description_1,
        about_description_2=settings.about_description_2,
        about_image_url=settings.about_image_url,
        stat_1_value=settings.stat_1_value,
        stat_1_label=settings.stat_1_label,
        stat_2_value=settings.stat_2_value,
        stat_2_label=settings.stat_2_label,
        stat_3_value=settings.stat_3_value,
        stat_3_label=settings.stat_3_label,
        updated_at=settings.updated_at
    )
