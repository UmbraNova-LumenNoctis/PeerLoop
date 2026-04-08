from pydantic import BaseModel, EmailStr, Field, constr, model_validator
from typing import Optional
from uuid import UUID


class SignupRequest(BaseModel):
    username: constr(min_length=3, max_length=30)
    email: EmailStr
    password: constr(min_length=8)


class LoginRequest(BaseModel):
    email: constr(min_length=1, max_length=320)
    password: constr(min_length=1)


class UserProfileUpdateRequest(BaseModel):
    pseudo: Optional[constr(min_length=3, max_length=30)] = None
    address: Optional[str] = None
    bio: Optional[constr(max_length=500)] = None
    avatar_id: Optional[UUID] = None
    cover_id: Optional[UUID] = None


class FriendshipCreateRequest(BaseModel):
    target_user_id: Optional[UUID] = None
    target_pseudo: Optional[constr(min_length=3, max_length=30)] = None

    @model_validator(mode="after")
    def validate_target(self):
        """Ensure exactly one friendship target identifier is provided.
        
        Returns:
            Self: Exactly one friendship target identifier is provided.
        """
        if bool(self.target_user_id) == bool(self.target_pseudo):
            raise ValueError("Provide exactly one of target_user_id or target_pseudo")
        return self


class PostCreateRequest(BaseModel):
    content: Optional[constr(max_length=2000)] = None
    media_id: Optional[UUID] = None

    @model_validator(mode="after")
    def validate_post_create(self):
        """Ensure post creation includes content or a media reference.
        
        Returns:
            Self: Post creation includes content or a media reference.
        """
        content = (self.content or "").strip()
        if not content and not self.media_id:
            raise ValueError("Post must include content or media_id")
        return self


class PostUpdateRequest(BaseModel):
    content: Optional[constr(max_length=2000)] = None
    media_id: Optional[UUID] = None
    clear_media: bool = False

    @model_validator(mode="after")
    def validate_post_update(self):
        """Ensure media update fields are not contradictory.
        
        Returns:
            Self: Media update fields are not contradictory.
        """
        if self.media_id and self.clear_media:
            raise ValueError("Provide media_id or clear_media, not both")
        return self


class CommentCreateRequest(BaseModel):
    content: constr(min_length=1, max_length=1200) = Field(...)
    parent_comment_id: Optional[UUID] = None


class CommentUpdateRequest(BaseModel):
    content: constr(min_length=1, max_length=1200) = Field(...)


class NotificationCreateRequest(BaseModel):
    type: constr(min_length=1, max_length=64)
    content: Optional[constr(max_length=2000)] = None
    source_id: Optional[UUID] = None


class ConversationCreateRequest(BaseModel):
    participant_ids: list[UUID] = Field(..., min_length=1, max_length=50)


class ChatMessageCreateRequest(BaseModel):
    content: constr(min_length=1, max_length=8000) = Field(...)


class LLMPromptRequest(BaseModel):
    prompt: constr(min_length=1, max_length=8000)

    @model_validator(mode="after")
    def validate_prompt(self):
        """Validate that prompt content is not empty after trimming.
        
        Returns:
            Self: That prompt content is not empty after trimming.
        """
        if not self.prompt.strip():
            raise ValueError("Prompt cannot be empty")
        return self
