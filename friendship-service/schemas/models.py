from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FriendshipCreateRequest(BaseModel):
    target_user_id: UUID | None = None
    target_pseudo: str | None = Field(default=None, min_length=3, max_length=30)

    @model_validator(mode="after")
    def validate_target(self):
        """Ensure exactly one friendship target identifier is provided.
        
        Returns:
            Self: Exactly one friendship target identifier is provided.
        """
        if bool(self.target_user_id) == bool(self.target_pseudo):
            raise ValueError("Provide exactly one of target_user_id or target_pseudo")
        return self


class FriendshipResponse(BaseModel):
    id: UUID
    user_a_id: UUID
    user_b_id: UUID
    status: str
    created_at: datetime | None = None
    direction: str | None = None

    friend_user_id: UUID | None = None
    friend_pseudo: str | None = None
    friend_avatar_id: UUID | None = None
    friend_avatar_url: str | None = None
    friend_online: bool = False

    model_config = ConfigDict(from_attributes=True)
