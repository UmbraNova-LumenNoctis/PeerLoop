"""Friendship response serialization helpers."""

from schemas.models import FriendshipResponse
from services.presence import get_online_user_ids
from stores.user_store import get_avatar_url_map, get_users_map


def get_friend_user_id(friendship_row: dict, current_user_id: str) -> str:
    """Return counterpart user id relative to current user.
    
    Args:
        friendship_row (dict): Parameter friendship_row.
        current_user_id (str): Identifier for current user.
    
    Returns:
        str: Counterpart user id relative to current user.
    """
    user_a_id = str(friendship_row.get("user_a_id"))
    user_b_id = str(friendship_row.get("user_b_id"))
    return user_b_id if user_a_id == current_user_id else user_a_id


def to_friendship_response(
    friendship_row: dict,
    current_user_id: str,
    users_map: dict[str, dict],
    avatar_urls: dict[str, str],
    online_user_ids: set[str],
) -> FriendshipResponse:
    """Convert one friendship row into API response model.
    
    Args:
        friendship_row (dict): Parameter friendship_row.
        current_user_id (str): Identifier for current user.
        users_map (dict[str, dict]): Parameter users_map.
        avatar_urls (dict[str, str]): URLs for avatar.
        online_user_ids (set[str]): Identifiers for online user.
    
    Returns:
        FriendshipResponse: One friendship row into API response model.
    """
    friend_user_id = get_friend_user_id(friendship_row, current_user_id)
    direction = "outgoing" if str(friendship_row.get("user_a_id")) == current_user_id else "incoming"

    friend = users_map.get(friend_user_id, {})
    friend_avatar_id = friend.get("avatar_id")
    friend_avatar_url = avatar_urls.get(str(friend_avatar_id)) if friend_avatar_id else None

    return FriendshipResponse(
        id=friendship_row.get("id"),
        user_a_id=friendship_row.get("user_a_id"),
        user_b_id=friendship_row.get("user_b_id"),
        status=friendship_row.get("status"),
        created_at=friendship_row.get("created_at"),
        direction=direction,
        friend_user_id=friend_user_id,
        friend_pseudo=friend.get("pseudo"),
        friend_avatar_id=friend_avatar_id,
        friend_avatar_url=friend_avatar_url,
        friend_online=friend_user_id in online_user_ids,
    )


def serialize_friendship_for_user(friendship_row: dict, current_user_id: str) -> FriendshipResponse:
    """Serialize one friendship row for a given authenticated user.
    
    Args:
        friendship_row (dict): Parameter friendship_row.
        current_user_id (str): Identifier for current user.
    
    Returns:
        FriendshipResponse: One friendship row for a given authenticated user.
    """
    friend_user_id = get_friend_user_id(friendship_row, current_user_id)
    users_map = get_users_map([friend_user_id])
    avatar_ids = [str(user.get("avatar_id")) for user in users_map.values() if user.get("avatar_id")]
    avatar_urls = get_avatar_url_map(avatar_ids)
    online_user_ids = get_online_user_ids([friend_user_id])
    return to_friendship_response(friendship_row, current_user_id, users_map, avatar_urls, online_user_ids)


def serialize_friendship_rows(friendship_rows: list[dict], current_user_id: str) -> list[FriendshipResponse]:
    """Serialize friendship rows list for one authenticated user.
    
    Args:
        friendship_rows (list[dict]): Parameter friendship_rows.
        current_user_id (str): Identifier for current user.
    
    Returns:
        list[FriendshipResponse]: Friendship rows list for one authenticated user.
    """
    if not friendship_rows:
        return []

    friend_ids = [get_friend_user_id(row, current_user_id) for row in friendship_rows]
    users_map = get_users_map(friend_ids)
    avatar_ids = [str(user.get("avatar_id")) for user in users_map.values() if user.get("avatar_id")]
    avatar_urls = get_avatar_url_map(avatar_ids)
    online_user_ids = get_online_user_ids(friend_ids)

    return [
        to_friendship_response(row, current_user_id, users_map, avatar_urls, online_user_ids)
        for row in friendship_rows
    ]
