import { JSX, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Box, Flex, Icon, Spinner, Text, useBreakpointValue } from "@chakra-ui/react";
import { LuMessageSquareMore } from "react-icons/lu";
import { useSearchParams } from "react-router-dom";
import {
  ChatConversationHeader,
  ChatSidebar,
  LlmDiscussion,
  MessageComposer,
  MessageThread,
} from "@/components/chat";
import useChat from "@/hooks/useChat";
import type { ConversationPreview } from "@/types/chat";

const buildPendingConversationPreview = (params: URLSearchParams): ConversationPreview | null => {
  const requestedUserId = params.get("start_with");
  if (!requestedUserId) {
    return null;
  }

  const requestedName = params.get("start_name")?.trim() || "New conversation";
  const requestedAvatar = params.get("start_avatar")?.trim() || null;

  return {
    id: `pending:${requestedUserId}`,
    title: requestedName,
    avatarUrl: requestedAvatar,
    participantNames: [requestedName],
    participantIds: [requestedUserId],
    primaryParticipantId: requestedUserId,
    lastMessageText: "",
    lastMessageAt: null,
    unreadCount: 0,
  };
};

function Chat(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const isDesktop = useBreakpointValue({ base: false, md: true }) ?? false;
  const [isMobileThreadOpen, setIsMobileThreadOpen] = useState<boolean>(() => Boolean(searchParams.get("start_with")));
  const [activeSection, setActiveSection] = useState<"chats" | "llm">("chats");
  const handledConversationParamRef = useRef<string | null>(null);
  const handledStartWithParamRef = useRef<string | null>(null);
  const [pendingConversationPreview, setPendingConversationPreview] = useState<ConversationPreview | null>(
    () => buildPendingConversationPreview(searchParams),
  );
  const [isPendingConversationConnecting, setIsPendingConversationConnecting] = useState<boolean>(
    () => Boolean(searchParams.get("start_with")),
  );
  const [deletingConversationIds, setDeletingConversationIds] = useState<Set<string>>(new Set());

  const {
    currentUser,
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
  } = useChat();

  const showSidebar = isDesktop || !isMobileThreadOpen;
  const showMainPanel = isDesktop || isMobileThreadOpen;
  const isPendingTargetConversationSelected = Boolean(
    pendingConversationPreview
      && selectedConversationPreview
      && selectedConversationPreview.primaryParticipantId === pendingConversationPreview.primaryParticipantId,
  );
  const shouldRenderPendingConversation = Boolean(
    activeSection === "chats"
      && pendingConversationPreview
      && !isPendingTargetConversationSelected,
  );
  const sidebarConversationPreviews = useMemo(() => {
    if (!pendingConversationPreview || activeSection !== "chats") {
      return conversationPreviews;
    }

    const pendingParticipantId = pendingConversationPreview.primaryParticipantId;
    if (!pendingParticipantId) {
      return conversationPreviews;
    }

    const existingConversation = conversationPreviews.some((preview) =>
      preview.primaryParticipantId === pendingParticipantId
      || preview.participantIds.includes(pendingParticipantId),
    );

    if (existingConversation) {
      return conversationPreviews;
    }

    return [pendingConversationPreview, ...conversationPreviews];
  }, [activeSection, conversationPreviews, pendingConversationPreview]);
  const visibleConversationPreviews = useMemo(
    () => sidebarConversationPreviews.filter((preview) => !deletingConversationIds.has(preview.id)),
    [deletingConversationIds, sidebarConversationPreviews],
  );
  const sidebarSelectedConversationId = shouldRenderPendingConversation
    ? pendingConversationPreview?.id || selectedConversationId
    : selectedConversationId;
  const selectedVisibleConversationPreview = useMemo(() => {
    if (!selectedConversationPreview || deletingConversationIds.has(selectedConversationPreview.id)) {
      return null;
    }
    return selectedConversationPreview;
  }, [deletingConversationIds, selectedConversationPreview]);

  const isSelectedContactOnline = useMemo(() => {
    if (!selectedConversationPreview) {
      return false;
    }

    if (selectedConversationPreview.primaryParticipantId) {
      return onlineUserIds.includes(selectedConversationPreview.primaryParticipantId);
    }

    return selectedConversationPreview.participantIds.some((userId) => onlineUserIds.includes(userId));
  }, [onlineUserIds, selectedConversationPreview]);

  const handleSectionChange = (section: "chats" | "llm") => {
    setActiveSection(section);
    if (!isDesktop) {
      setIsMobileThreadOpen(section === "llm");
    }
  };

  const handleSelectConversation = useCallback((conversationId: string): void => {
    setActiveSection("chats");
    selectConversation(conversationId);
    if (!isDesktop) {
      setIsMobileThreadOpen(true);
    }
  }, [isDesktop, selectConversation]);

  useEffect(() => {
    const requestedConversationId = searchParams.get("conversation");
    if (!requestedConversationId) {
      handledConversationParamRef.current = null;
      return;
    }

    if (handledConversationParamRef.current === requestedConversationId) {
      return;
    }

    const exists = conversationPreviews.some((preview) => preview.id === requestedConversationId);
    if (!exists) {
      return;
    }

    handledConversationParamRef.current = requestedConversationId;
    handleSelectConversation(requestedConversationId);

    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete("conversation");
    setSearchParams(nextParams, { replace: true });
  }, [conversationPreviews, handleSelectConversation, searchParams, setSearchParams]);

  useEffect(() => {
    const requestedUserId = searchParams.get("start_with");
    if (!requestedUserId) {
      handledStartWithParamRef.current = null;
      setPendingConversationPreview(null);
      setIsPendingConversationConnecting(false);
      return;
    }

    setPendingConversationPreview(buildPendingConversationPreview(searchParams));
    setIsPendingConversationConnecting(true);

    if (isBootstrapping || !currentUser?.id) {
      return;
    }

    if (handledStartWithParamRef.current === requestedUserId) {
      return;
    }

    handledStartWithParamRef.current = requestedUserId;
    setActiveSection("chats");
    if (!isDesktop) {
      setIsMobileThreadOpen(true);
    }

    let cancelled = false;
    const openDirectConversation = async (): Promise<void> => {
      try {
        await startConversationByUserId(requestedUserId);
      } catch {
        // useChat already exposes a user-facing error.
      } finally {
        if (cancelled) {
          return;
        }
        setIsPendingConversationConnecting(false);
        const nextParams = new URLSearchParams(searchParams);
        nextParams.delete("start_with");
        nextParams.delete("start_name");
        nextParams.delete("start_avatar");
        setSearchParams(nextParams, { replace: true });
      }
    };

    void openDirectConversation();
    return () => {
      cancelled = true;
    };
  }, [currentUser?.id, isBootstrapping, isDesktop, searchParams, setSearchParams, startConversationByUserId]);

  useEffect(() => {
    if (!pendingConversationPreview || !selectedConversationPreview) {
      return;
    }

    if (selectedConversationPreview.primaryParticipantId !== pendingConversationPreview.primaryParticipantId) {
      return;
    }

    setPendingConversationPreview(null);
    setIsPendingConversationConnecting(false);
  }, [pendingConversationPreview, selectedConversationPreview]);

  const handleStartConversation = async (targetPseudo: string): Promise<void> => {
    await startConversationByPseudo(targetPseudo);
    setActiveSection("chats");
    if (!isDesktop) {
      setIsMobileThreadOpen(true);
    }
  };

  const handleDeleteConversation = async (conversationId: string): Promise<void> => {
    setDeletingConversationIds((previous) => {
      const next = new Set(previous);
      next.add(conversationId);
      return next;
    });

    try {
      await removeConversation(conversationId);
      if (!isDesktop && selectedConversationId === conversationId) {
        setIsMobileThreadOpen(false);
      }
    } finally {
      setDeletingConversationIds((previous) => {
        const next = new Set(previous);
        next.delete(conversationId);
        return next;
      });
    }
  };

  if (isBootstrapping && !pendingConversationPreview) {
    return (
      <Flex w="100%" h="calc(100vh - 80px)" alignItems="center" justifyContent="center">
        <Spinner size="xl" color="primary" />
      </Flex>
    );
  }

  return (
    <Flex w="100%" h="calc(100vh - 80px)" bg="secondary" overflow="hidden">
      {showSidebar && (
        <Box w={{ base: "100%", md: "360px" }} h="100%" flexShrink={0}>
          <ChatSidebar
            conversations={visibleConversationPreviews}
            selectedConversationId={sidebarSelectedConversationId}
            isLoading={isBootstrapping}
            activeSection={activeSection}
            onSectionChange={handleSectionChange}
            onSelectConversation={handleSelectConversation}
            onRefresh={refreshConversations}
            onStartConversation={handleStartConversation}
              onDeleteConversation={handleDeleteConversation}
              deletingConversationIds={deletingConversationIds}
          />
        </Box>
      )}

      {showMainPanel && (
        <Flex direction="column" flex={1} minW={0} h="100%">
          {activeSection === "llm" ? (
            <LlmDiscussion
              showBackButton={!isDesktop}
              onBack={() => {
                setActiveSection("chats");
                setIsMobileThreadOpen(false);
              }}
            />
          ) : shouldRenderPendingConversation && pendingConversationPreview ? (
            <>
              <ChatConversationHeader
                conversation={pendingConversationPreview}
                isSocketConnected={!isPendingConversationConnecting && isSocketConnected}
                isContactOnline={false}
                showBackButton={!isDesktop}
                hideDeleteButton
                onBack={() => setIsMobileThreadOpen(false)}
                onDeleteConversation={async () => {
                  // No-op while pending conversation initialization.
                }}
              />

              <MessageThread
                messages={[]}
                currentUserId={currentUser?.id || null}
                isLoading
              />

              <MessageComposer
                onSend={async () => {
                  // Conversation is still being initialized.
                }}
                onSendFile={async () => {
                  // Conversation is still being initialized.
                }}
                isSending={false}
                isUploadingFile={false}
                uploadProgress={0}
                disabled
              />
            </>
          ) : selectedVisibleConversationPreview ? (
            <>
              <ChatConversationHeader
                conversation={selectedVisibleConversationPreview}
                isSocketConnected={isSocketConnected}
                isContactOnline={isSelectedContactOnline}
                showBackButton={!isDesktop}
                onBack={() => setIsMobileThreadOpen(false)}
                onDeleteConversation={() => handleDeleteConversation(selectedVisibleConversationPreview.id)}
              />

              {error && (
                <Box px={{ base: 4, md: 6 }} py={2} bg="rgba(255,153,102,0.17)">
                  <Text className="text-styles" fontSize="xs" fontWeight="800" color="error">
                    {error}
                  </Text>
                </Box>
              )}

              <MessageThread
                messages={messages}
                currentUserId={currentUser?.id || null}
                isLoading={isMessagesLoading}
              />

              <MessageComposer
                onSend={sendMessage}
                onSendFile={sendFileMessage}
                isSending={isSending}
                isUploadingFile={isUploadingFile}
                uploadProgress={uploadProgress}
                disabled={!selectedConversationId}
              />
            </>
          ) : deletingConversationIds.size > 0 ? (
            <Flex
              flex={1}
              direction="column"
              alignItems="center"
              justifyContent="center"
              gap={3}
              bg="linear-gradient(180deg, rgba(61,71,74,0.8) 0%, rgba(38,39,45,0.9) 100%)"
            >
              <Spinner size="lg" color="primary" />
              <Text className="text-styles" fontWeight="800" color="rgba(229,231,235,0.85)">
                Deleting conversation...
              </Text>
            </Flex>
          ) : (
            <Flex
              flex={1}
              direction="column"
              alignItems="center"
              justifyContent="center"
              gap={2}
              bg="linear-gradient(180deg, rgba(61,71,74,0.8) 0%, rgba(38,39,45,0.9) 100%)"
              px={6}
              textAlign="center"
            >
              <Icon as={LuMessageSquareMore} boxSize={14} color="primary" />
              <Text className="title-styles" fontSize="2xl" fontWeight="900">
                Your conversations
              </Text>
              <Text className="text-styles" fontWeight="700" maxW="380px" color="rgba(229,231,235,0.82)">
                Select a chat from the left or start one with a pseudo.
              </Text>
            </Flex>
          )}
        </Flex>
      )}
    </Flex>
  );
}

export default Chat;
