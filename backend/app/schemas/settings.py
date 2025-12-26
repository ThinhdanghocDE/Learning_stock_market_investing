from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class HomepageSettingsBase(BaseModel):
    hero_headline: Optional[str] = None
    hero_subheadline: Optional[str] = None
    hero_cta_text: Optional[str] = None
    hero_banners: Optional[List[str]] = None
    about_title: Optional[str] = None
    about_mission: Optional[str] = None
    about_description_1: Optional[str] = None
    about_description_2: Optional[str] = None
    about_image_url: Optional[str] = None
    stat_1_value: Optional[str] = None
    stat_1_label: Optional[str] = None
    stat_2_value: Optional[str] = None
    stat_2_label: Optional[str] = None
    stat_3_value: Optional[str] = None
    stat_3_label: Optional[str] = None


class HomepageSettingsUpdate(HomepageSettingsBase):
    pass


class HomepageSettingsResponse(HomepageSettingsBase):
    id: int
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
