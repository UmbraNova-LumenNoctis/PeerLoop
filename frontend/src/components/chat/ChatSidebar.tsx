import { useState } from "react";
import {
  Box,
  Button,
  Flex,
  IconButton,
  Input,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { LuBot, LuMessageCircle, LuPlus, LuRefreshCcw } from "react-icons/lu";
import type { ConversationPreview } from "@/types/chat";
import ConversationItem from "@/components/chat/ConversationItem";

interface ChatSidebarProps {
  conversations: ConversationPreview[];
  selectedConversationId: string | null;
  isLoading: boolean;
  deletingConversationIds?: Set<string>;
  activeSection: "chats" | "llm";
  onSectionChange: (section: "chats" | "llm") => void;
  onSelectConversation: (conversationId: string) => void;
  onRefresh: () => Promise<void>;
  onStartConversation: (targetPseudo: string) => Promise<void>;
  onDeleteConversation: (conversationId: string) => Promise<void>;
}

function ChatSidebar({
  conversations,
  selectedConversationId,
  isLoading,
  deletingConversationIds,
  activeSection,
  onSectionChange,
  onSelectConversation,
  onRefresh,
  onStartConversation,
  onDeleteConversation,
}: ChatSidebarProps) {
  const [targetPseudo, setTargetPseudo] = useState<string>("");
  const [isCreatingConversation, setIsCreatingConversation] = useState<boolean>(false);
  const [deletingConversationId, setDeletingConversationId] = useState<string | null>(null);

  const handleCreateConversation = async () => {
    const normalizedPseudo = targetPseudo.trim();
    if (!normalizedPseudo) {
      return;
    }

    setIsCreatingConversation(true);
    try {
      await onStartConversation(normalizedPseudo);
      setTargetPseudo("");
      onSectionChange("chats");
    } catch {
      // Keep value for quick correction.
    } finally {
      setIsCreatingConversation(false);
    }
  };

  const handleDeleteConversation = async (conversationId: string) => {
    setDeletingConversationId(conversationId);
    try {
      await onDeleteConversation(conversationId);
    } finally {
      setDeletingConversationId(null);
    }
  };

  return (
    <Flex
      direction="column"
      h="100%"
      bg="variantSecondary"
      borderRight="1px solid"
      borderColor="rgba(229,231,235,0.2)"
      px={3}
      py={4}
      gap={3}
    >
      <Flex alignItems="center" justifyContent="space-between" px={1}>
        <Text className="title-styles" fontSize="xl" fontWeight="900">
          Messages
        </Text>

        <IconButton
          aria-label="Refresh conversations"
          size="sm"
          borderRadius="full"
          variant="ghost"
          color="text"
          _hover={{ bg: "rgba(112,205,75,0.2)" }}
          onClick={() => {
            void onRefresh();
          }}
        >
          <LuRefreshCcw />
        </IconButton>
      </Flex>

      <Flex gap={2}>
        <Button
          flex={1}
          borderRadius="full"
          variant="ghost"
          bg={activeSection === "chats" ? "rgba(112,205,75,0.2)" : "transparent"}
          color={activeSection === "chats" ? "primary" : "text"}
          className="title-styles"
          fontWeight="800"
          onClick={() => onSectionChange("chats")}
          _hover={{ bg: "rgba(112,205,75,0.16)" }}
        >
          <LuMessageCircle /> Chats
        </Button>

        <Button
          flex={1}
          borderRadius="full"
          variant="ghost"
          bg={activeSection === "llm" ? "rgba(112,205,75,0.2)" : "transparent"}
          color={activeSection === "llm" ? "primary" : "text"}
          className="title-styles"
          fontWeight="800"
          onClick={() => onSectionChange("llm")}
          _hover={{ bg: "rgba(112,205,75,0.16)" }}
        >
          <LuBot /> LLM
        </Button>
      </Flex>

      <Flex gap={2}>
        <Input
          value={targetPseudo}
          onChange={(event) => setTargetPseudo(event.target.value)}
          placeholder="Start chat by pseudo"
          bg="rgba(255,255,255,0.04)"
          border="1px solid"
          borderColor="rgba(229,231,235,0.24)"
          borderRadius="full"
          className="text-styles"
          fontWeight="700"
          fontSize="sm"
          _placeholder={{ color: "rgba(229,231,235,0.58)" }}
          _focus={{ borderColor: "primary" }}
          disabled={isCreatingConversation}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              void handleCreateConversation();
            }
          }}
        />
        <Button
          borderRadius="full"
          bg="primary"
          color="secondary"
          onClick={() => {
            void handleCreateConversation();
          }}
          disabled={!targetPseudo.trim() || isCreatingConversation}
          px={4}
          _hover={{ opacity: 0.9 }}
        >
          {isCreatingConversation ? <Spinner size="sm" /> : <LuPlus />}
        </Button>
      </Flex>

      {activeSection === "llm" && (
        <Box
          px={3}
          py={5}
          borderRadius="xl"
          bg="rgba(255,255,255,0.03)"
          borderTop="1px solid"
          borderColor="rgba(229,231,235,0.18)"
          mt={1}
        >
          <Text className="title-styles" fontSize="sm" fontWeight="900" color="primary" mb={1}>
            AI Discussion
          </Text>
          <Text className="text-styles" fontSize="xs" fontWeight="700" color="rgba(229,231,235,0.72)">
            Open the LLM panel to brainstorm, summarize, and draft messages.
          </Text>
        </Box>
      )}

      {activeSection === "chats" && (
        <VStack
          align="stretch"
          gap={1}
          flex={1}
          overflowY="auto"
          pr={1}
          borderTop="1px solid"
          borderColor="rgba(229,231,235,0.18)"
          mt={1}
          pt={2}
        >
          {isLoading && (
            <Flex alignItems="center" justifyContent="center" py={8}>
              <Spinner color="primary" />
            </Flex>
          )}

          {!isLoading && conversations.length === 0 && (
            <Box py={8} px={3} textAlign="center">
              <Text className="title-styles" fontWeight="900" fontSize="sm" color="variantText">
                No conversations yet
              </Text>
              <Text className="text-styles" fontWeight="700" fontSize="xs" color="rgba(229,231,235,0.65)">
                Start a conversation by entering a user pseudo.
              </Text>
            </Box>
          )}

          {!isLoading && conversations.map((conversation) => {
            const isPendingConversation = conversation.id.startsWith("pending:");
            const isDeletingConversation = Boolean(deletingConversationIds?.has(conversation.id));
            return (
            <ConversationItem
              key={conversation.id}
              title={conversation.title}
              avatarUrl={conversation.avatarUrl}
              lastMessageText={conversation.lastMessageText}
              lastMessageAt={conversation.lastMessageAt}
              unreadCount={conversation.unreadCount}
              isActive={conversation.id === selectedConversationId}
              onSelect={() => {
                if (isPendingConversation) {
                  return;
                }
                onSelectConversation(conversation.id);
              }}
              onDelete={() => {
                if (isPendingConversation) {
                  return;
                }
                if (isDeletingConversation) {
                  return;
                }
                if (deletingConversationId === conversation.id) {
                  return;
                }
                void handleDeleteConversation(conversation.id);
              }}
              canDelete={!isPendingConversation}
              isDeleting={isDeletingConversation}
            />
            );
          })}
        </VStack>
      )}
    </Flex>
  );
}

export default ChatSidebar;
