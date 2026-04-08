from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PostCreateRequest(BaseModel):
    content: str | None = Field(default=None, max_length=2000)
    media_id: UUID | None = None

    @model_validator(mode="after")
    def validate_post_payload(self):
        """Ensure post creation includes content or a media reference.
        
        Returns:
            Self: Post creation includes content or a media reference.
        """
        content = (self.content or "").strip()
        if not content and not self.media_id:
            raise ValueError("Post must include content or media_id")
        return self


class PostUpdateRequest(BaseModel):
    content: str | None = Field(default=None, max_length=2000)
    media_id: UUID | None = None
    clear_media: bool = False

    @model_validator(mode="after")
    def validate_post_update_payload(self):
        """Ensure media update fields are not contradictory.
        
        Returns:
            Self: Media update fields are not contradictory.
        """
        if self.media_id and self.clear_media:
            raise ValueError("Provide media_id or clear_media, not both")
        return self


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1200)
    parent_comment_id: UUID | None = None


class CommentUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1200)


class PostResponse(BaseModel):
    id: UUID
    user_id: UUID
    content: str | None = None
    media_id: UUID | None = None
    media_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    like_count: int = 0
    comment_count: int = 0
    liked_by_me: bool = False
    author_pseudo: str | None = None
    author_avatar_id: UUID | None = None
    author_avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CommentResponse(BaseModel):
    id: UUID
    post_id: UUID
    user_id: UUID
    parent_comment_id: UUID | None = None
    content: str
    created_at: datetime | None = None
    author_pseudo: str | None = None
    author_avatar_id: UUID | None = None
    author_avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PostFeedResponse(BaseModel):
    items: list[PostResponse]
    limit: int
    offset: int
    returned: int
    has_more: bool
    next_offset: int | None = None
