export interface ChatUserProfile {
  id: string;
  pseudo: string | null;
  email: string | null;
  avatar_url: string | null;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  created_at: string | null;
  sender_pseudo: string | null;
  sender_avatar_id: string | null;
  sender_avatar_url: string | null;
}

export interface ChatConversation {
  id: string;
  created_at: string | null;
  participant_ids: string[];
  unread_count: number;
  last_message: ChatMessage | null;
}

export interface ConversationPreview {
  id: string;
  title: string;
  avatarUrl: string | null;
  participantNames: string[];
  participantIds: string[];
  primaryParticipantId: string | null;
  lastMessageText: string;
  lastMessageAt: string | null;
  unreadCount: number;
}

export interface ChatSocketUrl {
  conversation_id: string;
  ws_url: string;
}

export interface ChatPresenceSocketUrl {
  ws_url: string;
}

export interface ChatConversationPresence {
  conversation_id: string;
  online_user_ids: string[];
}

export interface ChatSearchUserItem {
  id: string;
  pseudo: string | null;
  email: string | null;
  bio: string | null;
  avatar_id: string | null;
  avatar_url: string | null;
}

export interface ChatSearchUsersResponse {
  query: string;
  limit: number;
  total: number;
  items: ChatSearchUserItem[];
}

export interface ChatNotificationUnreadCount {
  unread_count: number;
}

export interface ChatUploadedFile {
  id?: string;
  media_id?: string;
  uuid?: string;
  url: string;
  preview_url?: string | null;
  file_id?: string;
  original_name?: string;
  detected_type?: string | null;
}

export interface ChatAttachmentPayload {
  media_id?: string;
  url: string;
  preview_url?: string | null;
  detected_type?: string | null;
  original_name?: string;
}

export interface ParsedChatContent {
  text: string;
  attachment: ChatAttachmentPayload | null;
}

export interface LlmChatResponse {
  provider: string;
  model: string;
  text: string;
  finish_reason: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
}

export interface LlmHistoryMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  provider: string | null;
  model: string | null;
  finish_reason: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  created_at: string | null;
}

export interface ChatWsMessageEvent {
  type: "message";
  payload: ChatMessage;
}

export interface ChatWsConnectedEvent {
  type: "connected";
  conversation_id: string;
  user_id: string;
}

export interface ChatWsPresenceEvent {
  type: "presence";
  event: "join" | "leave";
  conversation_id: string;
  user_id: string;
}

export interface ChatWsErrorEvent {
  type: "error";
  detail: string;
}

export interface ChatWsPongEvent {
  type: "pong";
}

export type ChatWsEvent =
  | ChatWsMessageEvent
  | ChatWsConnectedEvent
  | ChatWsPresenceEvent
  | ChatWsErrorEvent
  | ChatWsPongEvent;
