import axios, { AxiosProgressEvent } from "axios";
import type {
  ChatConversation,
  ChatConversationPresence,
  ChatPresenceSocketUrl,
  LlmHistoryMessage,
  ChatMessage,
  ChatNotificationUnreadCount,
  ChatSearchUsersResponse,
  ChatSocketUrl,
  ChatUploadedFile,
  ChatUserProfile,
  LlmChatResponse,
} from "@/types/chat";
import { attachAuthInterceptors, getStoredToken, resolveApiBaseUrl } from "@/utils/authSession";

const chatApi = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 10000,
  withCredentials: true,
});
attachAuthInterceptors(chatApi);

const authHeaders = (): Record<string, string> => {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const fetchCurrentUserProfile = async (): Promise<ChatUserProfile> => {
  const response = await chatApi.get<ChatUserProfile>("/api/user/me", {
    headers: authHeaders(),
  });

  return response.data;
};

export const fetchUserProfileById = async (userId: string): Promise<ChatUserProfile> => {
  const response = await chatApi.get<ChatUserProfile>(`/api/user/${userId}`, {
    headers: authHeaders(),
  });

  return response.data;
};

export const searchUsers = async (query: string, limit = 20): Promise<ChatSearchUsersResponse> => {
  const response = await chatApi.get<ChatSearchUsersResponse>("/api/search/users", {
    headers: authHeaders(),
    params: {
      q: query,
      limit,
    },
  });

  return response.data;
};

export const fetchConversations = async (limit = 50, offset = 0): Promise<ChatConversation[]> => {
  const response = await chatApi.get<ChatConversation[]>("/api/chat/conversations", {
    headers: authHeaders(),
    params: {
      limit,
      offset,
    },
  });

  return response.data;
};

export const fetchUnreadNotificationCount = async (): Promise<number> => {
  const response = await chatApi.get<ChatNotificationUnreadCount>("/api/notifications/unread-count", {
    headers: authHeaders(),
  });

  const unreadCount = Number(response.data?.unread_count || 0);
  return Number.isFinite(unreadCount) ? Math.max(0, unreadCount) : 0;
};

export const fetchConversationMessages = async (
  conversationId: string,
  limit = 200,
  offset = 0,
): Promise<ChatMessage[]> => {
  const response = await chatApi.get<ChatMessage[]>(`/api/chat/conversations/${conversationId}/messages`, {
    headers: authHeaders(),
    params: {
      limit,
      offset,
      order: "asc",
    },
  });

  return response.data;
};

export const fetchConversationPresence = async (
  conversationId: string,
): Promise<ChatConversationPresence> => {
  const response = await chatApi.get<ChatConversationPresence>(`/api/chat/conversations/${conversationId}/presence`, {
    headers: authHeaders(),
  });

  return response.data;
};

export const sendConversationMessage = async (
  conversationId: string,
  content: string,
): Promise<ChatMessage> => {
  const response = await chatApi.post<ChatMessage>(
    `/api/chat/conversations/${conversationId}/messages`,
    { content },
    {
      headers: authHeaders(),
    },
  );

  return response.data;
};

export const uploadChatFile = async (
  file: File,
  onProgress?: (progress: number) => void,
): Promise<ChatUploadedFile> => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await chatApi.post<ChatUploadedFile>("/api/files/upload", formData, {
    headers: {
      ...authHeaders(),
    },
    onUploadProgress: (event: AxiosProgressEvent) => {
      if (!onProgress) {
        return;
      }

      const total = event.total || file.size;
      if (!total) {
        return;
      }

      const progress = Math.min(100, Math.round((event.loaded / total) * 100));
      onProgress(progress);
    },
  });

  return response.data;
};

export const markConversationAsRead = async (conversationId: string): Promise<void> => {
  await chatApi.patch(
    `/api/chat/conversations/${conversationId}/read`,
    {},
    {
      headers: authHeaders(),
    },
  );
};

export const fetchConversationWsUrl = async (conversationId: string): Promise<ChatSocketUrl> => {
  const response = await chatApi.get<ChatSocketUrl>(`/api/chat/ws-url/${conversationId}`, {
    headers: authHeaders(),
  });

  return response.data;
};

export const fetchPresenceWsUrl = async (): Promise<ChatPresenceSocketUrl> => {
  const response = await chatApi.get<ChatPresenceSocketUrl>("/api/chat/presence-ws-url", {
    headers: authHeaders(),
  });

  return response.data;
};

export const createConversation = async (
  participantIds: string[],
): Promise<ChatConversation> => {
  const response = await chatApi.post<ChatConversation>(
    "/api/chat/conversations",
    {
      participant_ids: participantIds,
    },
    {
      headers: authHeaders(),
    },
  );

  return response.data;
};

export const deleteConversation = async (conversationId: string): Promise<void> => {
  await chatApi.delete(`/api/chat/conversations/${conversationId}`, {
    headers: authHeaders(),
  });
};

export const sendLlmPrompt = async (prompt: string): Promise<LlmChatResponse> => {
  const response = await chatApi.post<LlmChatResponse>(
    "/api/llm/chat",
    { prompt },
    {
      headers: authHeaders(),
    },
  );

  return response.data;
};

export const fetchLlmHistory = async (limit = 200, offset = 0): Promise<LlmHistoryMessage[]> => {
  const response = await chatApi.get<LlmHistoryMessage[]>("/api/llm/history", {
    headers: authHeaders(),
    params: {
      limit,
      offset,
    },
  });

  return response.data;
};

export const clearLlmHistory = async (): Promise<number> => {
  const response = await chatApi.delete<{ deleted_count?: number }>("/api/llm/history", {
    headers: authHeaders(),
  });

  const deleted = Number(response.data?.deleted_count || 0);
  return Number.isFinite(deleted) ? Math.max(0, deleted) : 0;
};
