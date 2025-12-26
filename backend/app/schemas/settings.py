from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import json

class HomepageSettingsBase(BaseModel):
    hero_headline: str
    hero_subheadline: str
    hero_cta_text: str
    hero_banners: List[str] = []
    about_title: str
    about_mission: str
    about_description_1: str
    about_description_2: str
    about_image_url: Optional[str] = None
    stat_1_value: str
    stat_1_label: str
    stat_2_value: str
    stat_2_label: str
    stat_3_value: str
    stat_3_label: str

class HomepageSettingsUpdate(HomepageSettingsBase):
    pass

class HomepageSettingsResponse(HomepageSettingsBase):
    id: int
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
