import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createConversation,
  deleteConversation,
  fetchConversationMessages,
  fetchConversationPresence,
  fetchConversationWsUrl,
  fetchConversations,
  fetchCurrentUserProfile,
  fetchUserProfileById,
  markConversationAsRead,
  searchUsers,
  sendConversationMessage,
  uploadChatFile,
} from "@/services/chatService";
import type {
  ChatAttachmentPayload,
  ChatConversation,
  ChatMessage,
  ChatUserProfile,
  ChatWsEvent,
  ConversationPreview,
} from "@/types/chat";
import { buildAttachmentMessageContent, toConversationPreviewText } from "@/utils/chatContent";

interface UseChatReturn {
  currentUser: ChatUserProfile | null;
  conversations: ChatConversation[];
  conversationPreviews: ConversationPreview[];
  selectedConversationId: string | null;
  selectedConversationPreview: ConversationPreview | null;
  messages: ChatMessage[];
  onlineUserIds: string[];
  isBootstrapping: boolean;
  isMessagesLoading: boolean;
  isSending: boolean;
  isUploadingFile: boolean;
  uploadProgress: number;
  isSocketConnected: boolean;
  error: string | null;
  selectConversation: (conversationId: string) => void;
  sendMessage: (content: string) => Promise<void>;
  sendFileMessage: (file: File, caption?: string) => Promise<void>;
  refreshConversations: () => Promise<void>;
  startConversationByUserId: (userId: string) => Promise<void>;
  startConversationByPseudo: (pseudo: string) => Promise<void>;
  removeConversation: (conversationId: string) => Promise<void>;
}

const OPTIMISTIC_MESSAGE_PREFIX = "optimistic-";
const PENDING_MESSAGE_MAX_AGE_MS = 30000;
const PENDING_MESSAGE_MATCH_WINDOW_MS = 45000;
const CHAT_CACHE_TTL_MS = 60000;
const CHAT_MESSAGES_CACHE_TTL_MS = 45000;
const CHAT_CACHE_STORAGE_KEY = "chat:memory-cache:v1";

interface PendingOutgoingMessage {
  tempId: string;
  content: string;
  sentAt: number;
}

interface ChatMemoryCache {
  initialized: boolean;
  updatedAt: number;
  currentUser: ChatUserProfile | null;
  conversations: ChatConversation[];
  profilesById: Record<string, ChatUserProfile>;
  selectedConversationId: string | null;
  messagesByConversationId: Record<string, ChatMessage[]>;
  messageUpdatedAtByConversationId: Record<string, number>;
  onlineUserIdsByConversationId: Record<string, string[]>;
}

const chatMemoryCache: ChatMemoryCache = {
  initialized: false,
  updatedAt: 0,
  currentUser: null,
  conversations: [],
  profilesById: {},
  selectedConversationId: null,
  messagesByConversationId: {},
  messageUpdatedAtByConversationId: {},
  onlineUserIdsByConversationId: {},
};

const hydrateChatMemoryCacheFromSession = () => {
  if (typeof window === "undefined") {
    return;
  }

  try {
    const raw = window.sessionStorage.getItem(CHAT_CACHE_STORAGE_KEY);
    if (!raw) {
      return;
    }

    const parsed = JSON.parse(raw) as Partial<ChatMemoryCache>;
    if (!parsed || typeof parsed !== "object") {
      return;
    }

    chatMemoryCache.initialized = Boolean(parsed.initialized);
    chatMemoryCache.updatedAt = Number(parsed.updatedAt || 0);
    chatMemoryCache.currentUser = parsed.currentUser || null;
    chatMemoryCache.conversations = Array.isArray(parsed.conversations) ? parsed.conversations : [];
    chatMemoryCache.profilesById = parsed.profilesById || {};
    chatMemoryCache.selectedConversationId = parsed.selectedConversationId || null;
    chatMemoryCache.messagesByConversationId = parsed.messagesByConversationId || {};
    chatMemoryCache.messageUpdatedAtByConversationId = parsed.messageUpdatedAtByConversationId || {};
    chatMemoryCache.onlineUserIdsByConversationId = parsed.onlineUserIdsByConversationId || {};
  } catch {
    // Ignore cache hydration errors and continue with empty in-memory cache.
  }
};

const persistChatMemoryCacheToSession = () => {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.sessionStorage.setItem(
      CHAT_CACHE_STORAGE_KEY,
      JSON.stringify(chatMemoryCache),
    );
  } catch {
    // Ignore session storage write failures (quota/private mode).
  }
};

hydrateChatMemoryCacheFromSession();

const resolveCachedConversationId = (): string | null => {
  if (!chatMemoryCache.selectedConversationId) {
    return chatMemoryCache.conversations[0]?.id || null;
  }

  const exists = chatMemoryCache.conversations.some(
    (conversation) => conversation.id === chatMemoryCache.selectedConversationId,
  );

  return exists ? chatMemoryCache.selectedConversationId : (chatMemoryCache.conversations[0]?.id || null);
};

const isRootCacheFresh = (): boolean => {
  if (!chatMemoryCache.initialized) {
    return false;
  }

  return Date.now() - chatMemoryCache.updatedAt <= CHAT_CACHE_TTL_MS;
};

const isConversationCacheFresh = (conversationId: string): boolean => {
  const updatedAt = chatMemoryCache.messageUpdatedAtByConversationId[conversationId];
  if (!updatedAt) {
    return false;
  }

  return Date.now() - updatedAt <= CHAT_MESSAGES_CACHE_TTL_MS;
};

const sortConversationsByRecentActivity = (items: ChatConversation[]): ChatConversation[] => {
  return [...items].sort((a, b) => {
    const dateA = a.last_message?.created_at || a.created_at || "";
    const dateB = b.last_message?.created_at || b.created_at || "";
    return dateA < dateB ? 1 : -1;
  });
};

const conversationActivityAt = (conversation: ChatConversation): string => {
  return conversation.last_message?.created_at || conversation.created_at || "";
};

const dedupeDirectConversations = (
  items: ChatConversation[],
  currentUserId: string | undefined,
): ChatConversation[] => {
  if (!currentUserId) {
    return sortConversationsByRecentActivity(items);
  }

  const dedupedMap = new Map<string, ChatConversation>();
  items.forEach((conversation) => {
    const otherParticipants = conversation.participant_ids.filter(
      (participantId) => participantId !== currentUserId,
    );
    const dedupeKey = otherParticipants.length === 1
      ? `direct:${otherParticipants[0]}`
      : `conversation:${conversation.id}`;
    const existingConversation = dedupedMap.get(dedupeKey);

    if (!existingConversation || conversationActivityAt(conversation) > conversationActivityAt(existingConversation)) {
      dedupedMap.set(dedupeKey, conversation);
    }
  });

  return sortConversationsByRecentActivity(Array.from(dedupedMap.values()));
};

const upsertMessage = (messages: ChatMessage[], incoming: ChatMessage): ChatMessage[] => {
  if (messages.some((message) => message.id === incoming.id)) {
    return messages;
  }

  return [...messages, incoming];
};

const displayNameFor = (profile: ChatUserProfile | undefined, userId: string): string => {
  if (profile?.pseudo) {
    return profile.pseudo;
  }

  if (profile?.email) {
    return profile.email.split("@")[0];
  }

  return `User ${userId.slice(0, 6)}`;
};

const avatarFor = (profile: ChatUserProfile | undefined): string => {
  if (profile?.avatar_url) {
    return profile.avatar_url;
  }

  return undefined;
};

const normalizePseudo = (value: string): string => value.trim().toLowerCase();

const createOptimisticMessage = (
  conversationId: string,
  content: string,
  currentUser: ChatUserProfile,
): ChatMessage => ({
  id: `${OPTIMISTIC_MESSAGE_PREFIX}${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
  conversation_id: conversationId,
  sender_id: currentUser.id,
  content,
  created_at: new Date().toISOString(),
  sender_pseudo: currentUser.pseudo,
  sender_avatar_id: null,
  sender_avatar_url: currentUser.avatar_url,
});

export const useChat = (): UseChatReturn => {
  const cachedConversationId = resolveCachedConversationId();

  const [currentUser, setCurrentUser] = useState<ChatUserProfile | null>(chatMemoryCache.currentUser);
  const [conversations, setConversations] = useState<ChatConversation[]>(chatMemoryCache.conversations);
  const [profilesById, setProfilesById] = useState<Record<string, ChatUserProfile>>(chatMemoryCache.profilesById);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(cachedConversationId);
  const [messages, setMessages] = useState<ChatMessage[]>(
    cachedConversationId ? (chatMemoryCache.messagesByConversationId[cachedConversationId] || []) : [],
  );
  const [onlineUserIds, setOnlineUserIds] = useState<string[]>(
    cachedConversationId ? (chatMemoryCache.onlineUserIdsByConversationId[cachedConversationId] || []) : [],
  );

  const [isBootstrapping, setIsBootstrapping] = useState<boolean>(!chatMemoryCache.initialized);
  const [isMessagesLoading, setIsMessagesLoading] = useState<boolean>(false);
  const [pendingSendCount, setPendingSendCount] = useState<number>(0);
  const [isUploadingFile, setIsUploadingFile] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isSocketConnected, setIsSocketConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const profilesByIdRef = useRef<Record<string, ChatUserProfile>>({});
  const pendingOutgoingRef = useRef<Record<string, PendingOutgoingMessage[]>>({});
  const messagesConversationIdRef = useRef<string | null>(cachedConversationId);
  const conversationsRef = useRef<ChatConversation[]>(chatMemoryCache.conversations);
  const selectedConversationIdRef = useRef<string | null>(cachedConversationId);
  const messagesRef = useRef<ChatMessage[]>(
    cachedConversationId ? (chatMemoryCache.messagesByConversationId[cachedConversationId] || []) : [],
  );
  const onlineUserIdsRef = useRef<string[]>(
    cachedConversationId ? (chatMemoryCache.onlineUserIdsByConversationId[cachedConversationId] || []) : [],
  );

  useEffect(() => {
    profilesByIdRef.current = profilesById;
  }, [profilesById]);

  useEffect(() => {
    conversationsRef.current = conversations;
  }, [conversations]);

  useEffect(() => {
    selectedConversationIdRef.current = selectedConversationId;
  }, [selectedConversationId]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    onlineUserIdsRef.current = onlineUserIds;
  }, [onlineUserIds]);

  useEffect(() => {
    if (isBootstrapping || !currentUser) {
      return;
    }

    chatMemoryCache.initialized = true;
    chatMemoryCache.currentUser = currentUser;
    chatMemoryCache.conversations = conversations;
    chatMemoryCache.profilesById = profilesById;
    chatMemoryCache.selectedConversationId = selectedConversationId;
    chatMemoryCache.updatedAt = Date.now();
    persistChatMemoryCacheToSession();
  }, [conversations, currentUser, isBootstrapping, profilesById, selectedConversationId]);

  useEffect(() => {
    if (!selectedConversationId || isMessagesLoading) {
      return;
    }

    if (messagesConversationIdRef.current !== selectedConversationId) {
      return;
    }

    chatMemoryCache.messagesByConversationId[selectedConversationId] = messages;
    chatMemoryCache.messageUpdatedAtByConversationId[selectedConversationId] = Date.now();
    chatMemoryCache.updatedAt = Date.now();
    persistChatMemoryCacheToSession();
  }, [isMessagesLoading, messages, selectedConversationId]);

  useEffect(() => {
    if (!selectedConversationId) {
      return;
    }

    chatMemoryCache.onlineUserIdsByConversationId[selectedConversationId] = onlineUserIds;
    chatMemoryCache.updatedAt = Date.now();
    persistChatMemoryCacheToSession();
  }, [onlineUserIds, selectedConversationId]);

  const closeSocket = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setIsSocketConnected(false);
  }, []);

  const hydrateParticipantProfiles = useCallback(
    async (items: ChatConversation[], currentUserId: string) => {
      const idsToFetch = [...new Set(items.flatMap((conversation) => conversation.participant_ids))]
        .filter((userId) => userId !== currentUserId)
        .filter((userId) => !profilesByIdRef.current[userId]);

      if (idsToFetch.length === 0) {
        return;
      }

      const settledProfiles = await Promise.allSettled(
        idsToFetch.map((userId) => fetchUserProfileById(userId)),
      );

      const resolvedProfiles: Record<string, ChatUserProfile> = {};
      settledProfiles.forEach((result) => {
        if (result.status === "fulfilled") {
          resolvedProfiles[result.value.id] = result.value;
        }
      });

      if (Object.keys(resolvedProfiles).length > 0) {
        setProfilesById((prev) => ({
          ...prev,
          ...resolvedProfiles,
        }));
      }
    },
    [],
  );

  const registerPendingOutgoing = useCallback(
    (conversationId: string, tempId: string, content: string) => {
      const now = Date.now();
      const currentPending = pendingOutgoingRef.current[conversationId] || [];
      const freshPending = currentPending.filter((item) => now - item.sentAt <= PENDING_MESSAGE_MAX_AGE_MS);

      pendingOutgoingRef.current[conversationId] = [
        ...freshPending,
        {
          tempId,
          content,
          sentAt: now,
        },
      ];
    },
    [],
  );

  const removePendingOutgoing = useCallback((conversationId: string, tempId: string) => {
    const currentPending = pendingOutgoingRef.current[conversationId];
    if (!currentPending || currentPending.length === 0) {
      return;
    }

    const filteredPending = currentPending.filter((item) => item.tempId !== tempId);
    if (filteredPending.length > 0) {
      pendingOutgoingRef.current[conversationId] = filteredPending;
      return;
    }

    delete pendingOutgoingRef.current[conversationId];
  }, []);

  const consumePendingOutgoing = useCallback(
    (incomingMessage: ChatMessage): string | null => {
      if (!currentUser?.id || incomingMessage.sender_id !== currentUser.id) {
        return null;
      }

      const pendingForConversation = pendingOutgoingRef.current[incomingMessage.conversation_id];
      if (!pendingForConversation || pendingForConversation.length === 0) {
        return null;
      }

      const now = Date.now();
      const incomingAt = incomingMessage.created_at
        ? new Date(incomingMessage.created_at).getTime()
        : now;

      const freshPending = pendingForConversation.filter((item) => now - item.sentAt <= PENDING_MESSAGE_MAX_AGE_MS);
      const contentMatchIndex = freshPending.findIndex((item) => item.content === incomingMessage.content);
      const timeMatchIndex = freshPending.findIndex(
        (item) => Math.abs(incomingAt - item.sentAt) <= PENDING_MESSAGE_MATCH_WINDOW_MS,
      );
      const matchIndex = contentMatchIndex >= 0 ? contentMatchIndex : timeMatchIndex;

      if (matchIndex < 0) {
        pendingOutgoingRef.current[incomingMessage.conversation_id] = freshPending;
        return null;
      }

      const matchedPending = freshPending[matchIndex];
      const nextPending = freshPending.filter((_, index) => index !== matchIndex);
      if (nextPending.length > 0) {
        pendingOutgoingRef.current[incomingMessage.conversation_id] = nextPending;
      } else {
        delete pendingOutgoingRef.current[incomingMessage.conversation_id];
      }

      return matchedPending.tempId;
    },
    [currentUser?.id],
  );

  const handleIncomingMessage = useCallback(
    (incomingMessage: ChatMessage, activeConversationId: string) => {
      const matchedOptimisticMessageId = consumePendingOutgoing(incomingMessage);

      setMessages((prevMessages) => {
        if (incomingMessage.conversation_id !== activeConversationId) {
          return prevMessages;
        }

        messagesConversationIdRef.current = activeConversationId;

        const reconciledMessages = matchedOptimisticMessageId
          ? prevMessages.map((message) =>
              message.id === matchedOptimisticMessageId
                ? incomingMessage
                : message
            )
          : prevMessages;

        return upsertMessage(reconciledMessages, incomingMessage);
      });

      setConversations((prevConversations) => {
        const targetConversation = prevConversations.find(
          (conversation) => conversation.id === incomingMessage.conversation_id,
        );

        if (!targetConversation) {
          return prevConversations;
        }

        const senderIsCurrentUser = incomingMessage.sender_id === currentUser?.id;
        const conversationIsActive = activeConversationId === incomingMessage.conversation_id;

        const updatedConversation: ChatConversation = {
          ...targetConversation,
          last_message: incomingMessage,
          unread_count: senderIsCurrentUser || conversationIsActive
            ? 0
            : targetConversation.unread_count + 1,
        };

        return [
          updatedConversation,
          ...prevConversations.filter((conversation) => conversation.id !== updatedConversation.id),
        ];
      });

      if (!profilesByIdRef.current[incomingMessage.sender_id]) {
        void fetchUserProfileById(incomingMessage.sender_id)
          .then((profile) => {
            setProfilesById((prev) => ({
              ...prev,
              [profile.id]: profile,
            }));
          })
          .catch(() => {
            // Ignore profile lookup failures to keep chat flow stable.
          });
      }
    },
    [consumePendingOutgoing, currentUser?.id],
  );

  const refreshConversations = useCallback(async () => {
    if (!currentUser?.id) {
      return;
    }

    try {
      setError(null);

      const fetchedConversations = await fetchConversations();
      const sortedConversations = dedupeDirectConversations(fetchedConversations, currentUser.id);

      setConversations(sortedConversations);
      setSelectedConversationId((previousConversationId) => {
        if (previousConversationId && sortedConversations.some((conversation) => conversation.id === previousConversationId)) {
          return previousConversationId;
        }

        return sortedConversations[0]?.id || null;
      });

      await hydrateParticipantProfiles(sortedConversations, currentUser.id);
    } catch {
      setError("Unable to refresh conversations.");
    }
  }, [currentUser?.id, hydrateParticipantProfiles]);

  useEffect(() => {
    let isMounted = true;

    const bootstrapChat = async () => {
      const shouldShowBootstrapLoader = !chatMemoryCache.initialized;
      if (shouldShowBootstrapLoader) {
        setIsBootstrapping(true);
      }
      setError(null);

      try {
        const myProfile = await fetchCurrentUserProfile();
        if (!isMounted) {
          return;
        }

        setCurrentUser(myProfile);

        const fetchedConversations = await fetchConversations();
        if (!isMounted) {
          return;
        }

        const sortedConversations = dedupeDirectConversations(fetchedConversations, myProfile.id);
        const nextSelectedConversationId = sortedConversations[0]?.id || null;
        setConversations(sortedConversations);
        setSelectedConversationId(nextSelectedConversationId);

        if (nextSelectedConversationId) {
          setMessages(chatMemoryCache.messagesByConversationId[nextSelectedConversationId] || []);
          messagesConversationIdRef.current = nextSelectedConversationId;
          setOnlineUserIds(chatMemoryCache.onlineUserIdsByConversationId[nextSelectedConversationId] || []);
        } else {
          setMessages([]);
          messagesConversationIdRef.current = null;
          setOnlineUserIds([]);
        }

        await hydrateParticipantProfiles(sortedConversations, myProfile.id);
      } catch {
        if (!isMounted) {
          return;
        }

        setError("Unable to load your conversations right now.");
      } finally {
        if (isMounted) {
          setIsBootstrapping(false);
        }
      }
    };

    if (isRootCacheFresh()) {
      setIsBootstrapping(false);
      return () => {
        isMounted = false;
        closeSocket();
      };
    }

    void bootstrapChat();

    return () => {
      isMounted = false;
      closeSocket();
    };
  }, [closeSocket, hydrateParticipantProfiles]);

  useEffect(() => {
    if (!selectedConversationId) {
      setMessages([]);
      messagesConversationIdRef.current = null;
      setOnlineUserIds([]);
      pendingOutgoingRef.current = {};
      closeSocket();
      return;
    }

    let cancelled = false;
    const cachedConversationMessages = chatMemoryCache.messagesByConversationId[selectedConversationId];
    const hasCachedMessages = Array.isArray(cachedConversationMessages);
    const hasCachedNonEmptyMessages = hasCachedMessages && cachedConversationMessages.length > 0;
    const hasFreshConversationData = isConversationCacheFresh(selectedConversationId);
    const shouldFetchFromApi = !hasFreshConversationData || !hasCachedNonEmptyMessages;

    if (hasCachedMessages) {
      setMessages(cachedConversationMessages);
      messagesConversationIdRef.current = selectedConversationId;
      setOnlineUserIds(chatMemoryCache.onlineUserIdsByConversationId[selectedConversationId] || []);
      setConversations((prevConversations) =>
        prevConversations.map((conversation) =>
          conversation.id === selectedConversationId
            ? {
                ...conversation,
                unread_count: 0,
              }
            : conversation,
        ),
      );
    }

    const loadMessagesAndConnectWs = async () => {
      setIsMessagesLoading(!hasCachedNonEmptyMessages);
      setError(null);
      closeSocket();

      if (shouldFetchFromApi) {
        try {
          const [conversationMessages, presence] = await Promise.all([
            fetchConversationMessages(selectedConversationId),
            fetchConversationPresence(selectedConversationId).catch(() => null),
          ]);

          if (cancelled) {
            return;
          }

          chatMemoryCache.messagesByConversationId[selectedConversationId] = conversationMessages;
          chatMemoryCache.messageUpdatedAtByConversationId[selectedConversationId] = Date.now();
          chatMemoryCache.onlineUserIdsByConversationId[selectedConversationId] = presence?.online_user_ids || [];
          chatMemoryCache.updatedAt = Date.now();
          persistChatMemoryCacheToSession();

          setMessages(conversationMessages);
          messagesConversationIdRef.current = selectedConversationId;
          pendingOutgoingRef.current[selectedConversationId] = [];
          setOnlineUserIds(presence?.online_user_ids || []);
          setConversations((prevConversations) =>
            prevConversations.map((conversation) =>
              conversation.id === selectedConversationId
                ? {
                    ...conversation,
                    unread_count: 0,
                  }
                : conversation,
            ),
          );

          void markConversationAsRead(selectedConversationId).catch(() => {
            // Ignore read-sync failures to keep interaction fast.
          });
        } catch {
          if (!cancelled) {
            if (!hasCachedMessages) {
              setMessages([]);
              messagesConversationIdRef.current = selectedConversationId;
              setOnlineUserIds([]);
              setIsSocketConnected(false);
              setError("Unable to load this conversation.");
              return;
            }

            setError("Unable to refresh this conversation.");
          }
        }
      } else {
        pendingOutgoingRef.current[selectedConversationId] = pendingOutgoingRef.current[selectedConversationId] || [];
        void markConversationAsRead(selectedConversationId).catch(() => {
          // Ignore read-sync failures to keep interaction fast.
        });
      }

      try {
        const socketConfig = await fetchConversationWsUrl(selectedConversationId);
        if (cancelled) {
          return;
        }

        const socket = new WebSocket(socketConfig.ws_url);
        socketRef.current = socket;

        socket.onopen = () => {
          if (!cancelled) {
            setIsSocketConnected(true);
          }
        };

        socket.onmessage = (event) => {
          if (cancelled) {
            return;
          }

          try {
            const payload = JSON.parse(event.data) as ChatWsEvent;

            if (payload.type === "message") {
              handleIncomingMessage(payload.payload, selectedConversationId);
              return;
            }

            if (payload.type === "presence") {
              setOnlineUserIds((prev) => {
                if (payload.event === "join") {
                  if (prev.includes(payload.user_id)) {
                    return prev;
                  }
                  return [...prev, payload.user_id];
                }

                return prev.filter((userId) => userId !== payload.user_id);
              });
              return;
            }

            if (payload.type === "error") {
              setError(payload.detail || "WebSocket error.");
            }
          } catch {
            setError("Received an invalid real-time payload.");
          }
        };

        socket.onclose = () => {
          if (!cancelled) {
            setIsSocketConnected(false);
          }
        };

        socket.onerror = () => {
          if (!cancelled) {
            setIsSocketConnected(false);
          }
        };
      } catch {
        if (!cancelled) {
          setIsSocketConnected(false);
          setError("Conversation loaded, but real-time is currently unavailable.");
        }
      } finally {
        if (!cancelled) {
          setIsMessagesLoading(false);
        }
      }
    };

    void loadMessagesAndConnectWs();

    return () => {
      cancelled = true;
      closeSocket();
    };
  }, [closeSocket, handleIncomingMessage, selectedConversationId]);

  useEffect(() => {
    if (!selectedConversationId) {
      return;
    }

    let cancelled = false;

    const syncPresence = async () => {
      try {
        const presence = await fetchConversationPresence(selectedConversationId);
        if (!cancelled) {
          setOnlineUserIds(presence.online_user_ids || []);
        }
      } catch {
        // Ignore background presence polling errors.
      }
    };

    void syncPresence();
    const intervalId = window.setInterval(() => {
      void syncPresence();
    }, 15000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [selectedConversationId]);

  const sendMessage = useCallback(
    async (content: string): Promise<void> => {
      const normalizedContent = content.trim();
      if (!normalizedContent || !selectedConversationId) {
        return;
      }

      const conversationId = selectedConversationId;
      const optimisticMessage = currentUser
        ? createOptimisticMessage(conversationId, normalizedContent, currentUser)
        : null;

      if (optimisticMessage) {
        registerPendingOutgoing(conversationId, optimisticMessage.id, normalizedContent);
        messagesConversationIdRef.current = conversationId;
        setMessages((prevMessages) => {
          if (optimisticMessage.conversation_id !== conversationId) {
            return prevMessages;
          }

          return upsertMessage(prevMessages, optimisticMessage);
        });
      }

      setPendingSendCount((current) => current + 1);
      setError(null);

      try {
        const activeSocket = socketRef.current;
        if (activeSocket && activeSocket.readyState === WebSocket.OPEN) {
          activeSocket.send(
            JSON.stringify({
              type: "message",
              content: normalizedContent,
            }),
          );
        } else {
          const createdMessage = await sendConversationMessage(conversationId, normalizedContent);
          handleIncomingMessage(createdMessage, conversationId);
        }
      } catch (err) {
        if (optimisticMessage) {
          removePendingOutgoing(conversationId, optimisticMessage.id);
          setMessages((prevMessages) => prevMessages.filter((message) => message.id !== optimisticMessage.id));
        }
        setError("Message could not be sent.");
        throw err;
      } finally {
        setPendingSendCount((current) => Math.max(0, current - 1));
      }
    },
    [currentUser, handleIncomingMessage, registerPendingOutgoing, removePendingOutgoing, selectedConversationId],
  );

  const sendFileMessage = useCallback(
    async (file: File, caption = ""): Promise<void> => {
      if (!selectedConversationId) {
        return;
      }

      setIsUploadingFile(true);
      setUploadProgress(0);
      setError(null);

      try {
        const uploaded = await uploadChatFile(file, (progress) => {
          setUploadProgress(progress);
        });
        setUploadProgress(100);

        const attachment: ChatAttachmentPayload = {
          media_id: uploaded.media_id || uploaded.id || uploaded.uuid,
          url: uploaded.url,
          preview_url: uploaded.preview_url || uploaded.url,
          detected_type: uploaded.detected_type || file.type,
          original_name: uploaded.original_name || file.name,
        };

        const messageContent = buildAttachmentMessageContent(attachment, caption);
        await sendMessage(messageContent);
      } catch (err) {
        setError("File could not be uploaded.");
        throw err;
      } finally {
        setIsUploadingFile(false);
        setUploadProgress(0);
      }
    },
    [selectedConversationId, sendMessage],
  );

  const startConversationByUserId = useCallback(
    async (targetUserId: string): Promise<void> => {
      if (!targetUserId || !currentUser?.id) {
        return;
      }

      if (targetUserId === currentUser.id) {
        const selfChatError = new Error("SELF_CHAT");
        setError("You cannot start a conversation with yourself.");
        throw selfChatError;
      }

      setError(null);

      try {
        if (!profilesByIdRef.current[targetUserId]) {
          const profile = await fetchUserProfileById(targetUserId).catch(() => null);
          if (profile?.id) {
            setProfilesById((prev) => ({
              ...prev,
              [profile.id]: profile,
            }));
          }
        }

        const existingDirectConversation = conversations.find((conversation) => {
          const participantSet = new Set(conversation.participant_ids);
          return participantSet.size === 2
            && participantSet.has(currentUser.id)
            && participantSet.has(targetUserId);
        });

        if (existingDirectConversation) {
          setSelectedConversationId(existingDirectConversation.id);
          return;
        }

        const newConversation = await createConversation([targetUserId]);
        setConversations((prevConversations) => {
          const withoutDuplicate = prevConversations.filter((conversation) => conversation.id !== newConversation.id);
          return dedupeDirectConversations([newConversation, ...withoutDuplicate], currentUser.id);
        });
        setSelectedConversationId(newConversation.id);
        await hydrateParticipantProfiles([newConversation], currentUser.id);
      } catch (err: any) {
        if (err?.message === "SELF_CHAT") {
          throw err;
        }

        setError("Unable to start this conversation.");
        throw err;
      }
    },
    [conversations, currentUser?.id, hydrateParticipantProfiles],
  );

  const startConversationByPseudo = useCallback(
    async (pseudo: string): Promise<void> => {
      const normalizedPseudo = normalizePseudo(pseudo);
      if (!normalizedPseudo || !currentUser?.id) {
        return;
      }

      setError(null);

      try {
        const foundUsers = await searchUsers(normalizedPseudo, 20);
        const matchedUser = foundUsers.items.find(
          (item) => normalizePseudo(item.pseudo || "") === normalizedPseudo,
        );

        if (!matchedUser?.id) {
          throw new Error("USER_NOT_FOUND");
        }

        if (matchedUser.id === currentUser.id) {
          throw new Error("SELF_CHAT");
        }

        setProfilesById((prev) => ({
          ...prev,
          [matchedUser.id]: {
            id: matchedUser.id,
            pseudo: matchedUser.pseudo,
            email: matchedUser.email,
            avatar_url: matchedUser.avatar_url,
          },
        }));

        await startConversationByUserId(matchedUser.id);
      } catch (err: any) {
        if (err?.message === "SELF_CHAT") {
          setError("You cannot start a conversation with yourself.");
          throw err;
        }

        if (err?.message === "USER_NOT_FOUND") {
          setError("No user found with this pseudo.");
          throw err;
        }

        setError("Unable to start a conversation with this pseudo.");
        throw err;
      }
    },
    [currentUser?.id, startConversationByUserId],
  );

  const removeConversation = useCallback(
    async (conversationId: string): Promise<void> => {
      if (!conversationId) {
        return;
      }

      setError(null);

      const previousConversations = [...conversationsRef.current];
      const previousSelectedConversationId = selectedConversationIdRef.current;
      const previousMessages = [...messagesRef.current];
      const previousOnlineUserIds = [...onlineUserIdsRef.current];
      const previousConversationMessagesCache = chatMemoryCache.messagesByConversationId[conversationId]
        ? [...chatMemoryCache.messagesByConversationId[conversationId]]
        : null;
      const previousConversationMessageUpdatedAt = chatMemoryCache.messageUpdatedAtByConversationId[conversationId] || null;
      const previousConversationOnlineCache = chatMemoryCache.onlineUserIdsByConversationId[conversationId]
        ? [...chatMemoryCache.onlineUserIdsByConversationId[conversationId]]
        : null;
      const previousCacheUpdatedAt = chatMemoryCache.updatedAt;

      const nextConversations = previousConversations.filter((conversation) => conversation.id !== conversationId);
      const nextSelectedConversationId = previousSelectedConversationId && previousSelectedConversationId !== conversationId
        ? previousSelectedConversationId
        : (nextConversations[0]?.id || null);

      // Optimistic UI update: remove conversation immediately.
      delete chatMemoryCache.messagesByConversationId[conversationId];
      delete chatMemoryCache.messageUpdatedAtByConversationId[conversationId];
      delete chatMemoryCache.onlineUserIdsByConversationId[conversationId];
      chatMemoryCache.updatedAt = Date.now();
      persistChatMemoryCacheToSession();

      setConversations(nextConversations);
      setSelectedConversationId(nextSelectedConversationId);
      if (previousSelectedConversationId === conversationId) {
        setMessages([]);
        messagesConversationIdRef.current = null;
        setOnlineUserIds([]);
        closeSocket();
      }

      try {
        await deleteConversation(conversationId);
      } catch (err) {
        // Rollback optimistic state on failure.
        if (previousConversationMessagesCache) {
          chatMemoryCache.messagesByConversationId[conversationId] = previousConversationMessagesCache;
        }
        if (previousConversationMessageUpdatedAt) {
          chatMemoryCache.messageUpdatedAtByConversationId[conversationId] = previousConversationMessageUpdatedAt;
        }
        if (previousConversationOnlineCache) {
          chatMemoryCache.onlineUserIdsByConversationId[conversationId] = previousConversationOnlineCache;
        }
        chatMemoryCache.updatedAt = previousCacheUpdatedAt;
        persistChatMemoryCacheToSession();

        setConversations(previousConversations);
        setSelectedConversationId(previousSelectedConversationId);
        if (previousSelectedConversationId === conversationId) {
          setMessages(previousMessages);
          messagesConversationIdRef.current = previousSelectedConversationId;
          setOnlineUserIds(previousOnlineUserIds);
        }

        setError("Unable to delete this conversation.");
        throw err;
      }
    },
    [closeSocket],
  );

  const conversationPreviews = useMemo<ConversationPreview[]>(() => {
    return conversations.map((conversation) => {
      const participantIds = conversation.participant_ids.filter((participantId) => participantId !== currentUser?.id);
      const effectiveParticipantIds = participantIds.length > 0
        ? participantIds
        : conversation.participant_ids;

      const participantNames = effectiveParticipantIds.map((participantId) => {
        const profile = profilesById[participantId];
        return displayNameFor(profile, participantId);
      });

      const title = participantNames[0] || "Conversation";

      const firstParticipantId = effectiveParticipantIds[0] || null;
      const firstParticipantProfile = firstParticipantId ? profilesById[firstParticipantId] : undefined;

      return {
        id: conversation.id,
        title,
        avatarUrl: avatarFor(firstParticipantProfile),
        participantNames,
        participantIds: effectiveParticipantIds,
        primaryParticipantId: firstParticipantId,
        lastMessageText: toConversationPreviewText(conversation.last_message?.content || null),
        lastMessageAt: conversation.last_message?.created_at || conversation.created_at,
        unreadCount: conversation.unread_count,
      };
    });
  }, [conversations, currentUser?.id, profilesById]);

  const selectedConversationPreview = useMemo<ConversationPreview | null>(() => {
    if (!selectedConversationId) {
      return null;
    }

    return conversationPreviews.find((preview) => preview.id === selectedConversationId) || null;
  }, [conversationPreviews, selectedConversationId]);

  const selectConversation = useCallback((conversationId: string) => {
    setError(null);
    const cachedMessages = chatMemoryCache.messagesByConversationId[conversationId];
    const cachedOnlineUsers = chatMemoryCache.onlineUserIdsByConversationId[conversationId];

    if (cachedMessages) {
      setMessages(cachedMessages);
      messagesConversationIdRef.current = conversationId;
    } else {
      setMessages([]);
      messagesConversationIdRef.current = conversationId;
    }

    setOnlineUserIds(cachedOnlineUsers || []);
    setSelectedConversationId(conversationId);
  }, []);

  const isSending = pendingSendCount > 0;

  return {
    currentUser,
    conversations,
    conversationPreviews,
    selectedConversationId,
    selectedConversationPreview,
    messages,
    onlineUserIds,
    isBootstrapping,
    isMessagesLoading,
    isSending,
    isUploadingFile,
    uploadProgress,
    isSocketConnected,
    error,
    selectConversation,
    sendMessage,
    sendFileMessage,
    refreshConversations,
    startConversationByUserId,
    startConversationByPseudo,
    removeConversation,
  };
};

export default useChat;
