from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class UserBase(BaseModel):
    """Base user schema"""

    username: str
    email: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema"""

    pass


class UserResponse(UserBase):
    """User response schema"""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PostBase(BaseModel):
    """Base post schema"""

    title: str
    content: str
    visibility: str = "public"


class PostCreate(PostBase):
    """Post creation schema"""

    author_id: int


class PostResponse(PostBase):
    """Post response schema"""

    id: int
    author_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostWithAuthor(PostResponse):
    """Post with author information"""

    author_name: str
    author_username: str


class SearchRequest(BaseModel):
    """Search request schema"""

    query: str
    filter_visibility: Optional[str] = None
    filter_author_id: Optional[int] = None
    limit: int = 20
    offset: int = 0


class SearchResponse(BaseModel):
    """Search response schema"""

    query: str
    hits: List[PostWithAuthor]
    total_hits: int
    processing_time_ms: int
    limit: int
    offset: int


class SyncResponse(BaseModel):
    """Synchronization response schema"""

    status: str
    message: str
    indexed_count: int


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    service: str
    version: str
    database: str
    meilisearch: str
