from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConversationCreateRequest(BaseModel):
    participant_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_participants(self):
        """Validate that at least one participant id is provided.
        
        Returns:
            Self: That at least one participant id is provided.
        """
        if not self.participant_ids:
            raise ValueError("participant_ids cannot be empty")
        return self


class MessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)

    @model_validator(mode="after")
    def validate_content(self):
        """Validate that message content is not empty after trimming.
        
        Returns:
            Self: That message content is not empty after trimming.
        """
        if not self.content.strip():
            raise ValueError("Message content cannot be empty")
        return self


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    content: str
    created_at: datetime | None = None
    sender_pseudo: str | None = None
    sender_avatar_id: UUID | None = None
    sender_avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: UUID
    created_at: datetime | None = None
    participant_ids: list[str] = Field(default_factory=list)
    unread_count: int = 0
    last_message: MessageResponse | None = None

    model_config = ConfigDict(from_attributes=True)
