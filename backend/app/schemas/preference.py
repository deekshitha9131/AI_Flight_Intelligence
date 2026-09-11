from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationInfo
from typing import Optional
from datetime import datetime


class PreferenceBase(BaseModel):
    preferred_cabin: Optional[str] = Field(None, max_length=20)
    preferred_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    preferred_airport: Optional[str] = Field(None, max_length=10)
    preferred_time: Optional[str] = Field(None, max_length=20)
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)

    @field_validator('preferred_currency')
    def currency_uppercase(cls, v):
        if v is not None:
            v = v.upper()
            if len(v) != 3 or not v.isalpha():
                raise ValueError('Currency must be a 3-letter ISO 4217 code')
        return v

    @field_validator('preferred_airport')
    def airport_uppercase(cls, v):
        if v is not None:
            v = v.upper()
            if len(v) not in (3, 4) or not v.isalnum():
                raise ValueError('Airport code must be 3 or 4 alphanumeric characters (IATA/ICAO)')
        return v

    @field_validator('preferred_time')
    def validate_preferred_time(cls, v):
        if v is not None:
            v = v.lower()
            allowed = ['morning', 'afternoon', 'evening', 'night']
            if v not in allowed:
                raise ValueError(f'Preferred time must be one of {allowed}')
        return v

    @field_validator('preferred_cabin')
    def validate_preferred_cabin(cls, v):
        if v is not None:
            v = v.upper()
            allowed = ['ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST']
            if v not in allowed:
                raise ValueError(f'Preferred cabin must be one of {allowed}')
        return v

    @field_validator('max_price')
    def check_price_range(cls, v, info: ValidationInfo):
        min_price = info.data.get('min_price')
        if v is not None and min_price is not None:
            if v < min_price:
                raise ValueError('max_price must be greater than or equal to min_price')
        return v


class PreferenceCreate(PreferenceBase):
    pass


class PreferenceUpdate(PreferenceBase):
    pass


class PreferenceInDB(PreferenceBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {'from_attributes': True}
