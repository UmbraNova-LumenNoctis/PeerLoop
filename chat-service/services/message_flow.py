"""Message creation and broadcast workflow helpers."""

from services.connection_manager import connection_manager
from services.conversation_visibility import get_conversation_participants, unhide_conversation_for_all_participants
from stores.message_store import create_message_row, mark_conversation_read, serialize_message_rows
from schemas.models import MessageResponse
from services.notifications import send_notification


def notify_conversation_participants_about_message(
    conversation_id: str,
    sender_id: str,
    source_id: str | None,
) -> None:
    """Send chat_message notifications to all recipients except sender.
    
    Args:
        conversation_id (str): Conversation identifier.
        sender_id (str): Identifier for sender.
        source_id (str | None): Identifier for source.
    
    Returns:
        None: None.
    """
    participant_ids = get_conversation_participants(conversation_id)
    for participant_id in participant_ids:
        if participant_id == sender_id:
            continue
        send_notification(
            target_user_id=participant_id,
            notification_type="chat_message",
            content="You received a new message",
            source_id=source_id or conversation_id,
        )


async def create_and_broadcast_message(
    conversation_id: str,
    sender_id: str,
    content: str,
) -> MessageResponse:
    """Persist message, update conversation state, broadcast and notify participants.
    
    Args:
        conversation_id (str): Conversation identifier.
        sender_id (str): Identifier for sender.
        content (str): Text content.
    
    Returns:
        MessageResponse: Constructed value.
    """
    message_row = create_message_row(conversation_id, sender_id, content)
    unhide_conversation_for_all_participants(conversation_id)
    mark_conversation_read(conversation_id, sender_id)
    message = serialize_message_rows([message_row])[0]

    send_notification(
        target_user_id=sender_id,
        notification_type="chat_message_created",
        content="Your message was sent",
        source_id=str(message_row.get("id")) if message_row.get("id") else conversation_id,
    )
    await connection_manager.broadcast(
        conversation_id,
        {"type": "message", "payload": message.model_dump(mode="json")},
    )
    notify_conversation_participants_about_message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        source_id=str(message_row.get("id")) if message_row.get("id") else conversation_id,
    )
    return message
