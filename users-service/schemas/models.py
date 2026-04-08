from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserProfileBase(BaseModel):
    pseudo: str | None = Field(default=None, min_length=3, max_length=30)
    email: EmailStr | None = None
    address: str | None = None
    bio: str | None = Field(default=None, max_length=500)
    avatar_id: UUID | None = None
    avatar_url: str | None = None
    cover_id: UUID | None = None
    cover_url: str | None = None


class UserProfileUpdate(BaseModel):
    pseudo: str | None = Field(default=None, min_length=3, max_length=30)
    address: str | None = None
    bio: str | None = Field(default=None, max_length=500)
    avatar_id: UUID | None = None
    cover_id: UUID | None = None


class UserProfileResponse(UserProfileBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
