from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationCreateRequest(BaseModel):
    type: str = Field(min_length=1, max_length=64)
    content: str | None = Field(default=None, max_length=2000)
    source_id: UUID | None = None
    user_id: UUID | None = None
    actor_id: UUID | None = None


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    content: str | None = None
    source_id: UUID | None = None
    actor_id: UUID | None = None
    is_read: bool = False
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int
