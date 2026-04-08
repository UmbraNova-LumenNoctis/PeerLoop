"""Response models for search endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchUserResult(BaseModel):
    """Projected user information returned by user search."""

    id: UUID
    pseudo: str | None = None
    email: str | None = None
    bio: str | None = None
    avatar_id: UUID | None = None
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SearchPostResult(BaseModel):
    """Projected post information returned by post search."""

    id: UUID
    user_id: UUID
    content: str | None = None
    media_id: UUID | None = None
    media_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    author_pseudo: str | None = None
    author_avatar_url: str | None = None
    like_count: int = 0
    comment_count: int = 0
    liked_by_me: bool = False

    model_config = ConfigDict(from_attributes=True)


class SearchUsersResponse(BaseModel):
    """Response schema for `/search/users`."""

    query: str
    limit: int
    total: int
    items: list[SearchUserResult] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SearchPostsResponse(BaseModel):
    """Response schema for `/search/posts`."""

    query: str
    limit: int
    offset: int
    total: int
    items: list[SearchPostResult] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
