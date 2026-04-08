import { Avatar, Badge, Flex, IconButton, Link, Text } from "@chakra-ui/react";
import { LuArrowLeft, LuTrash2 } from "react-icons/lu";
import { Link as RouterLink } from "react-router-dom";
import type { ConversationPreview } from "@/types/chat";

interface ChatConversationHeaderProps {
  conversation: ConversationPreview;
  isSocketConnected: boolean;
  isContactOnline: boolean;
  showBackButton: boolean;
  hideDeleteButton?: boolean;
  onBack: () => void;
  onDeleteConversation: () => Promise<void>;
}

function ChatConversationHeader({
  conversation,
  isSocketConnected,
  isContactOnline,
  showBackButton,
  hideDeleteButton = false,
  onBack,
  onDeleteConversation,
}: ChatConversationHeaderProps) {
  const profilePath = conversation.primaryParticipantId ? `/profile/${conversation.primaryParticipantId}` : null;
  const conversationIdentity = (
    <Flex alignItems="center" gap={3} minW={0}>
      <Avatar.Root size="sm" flexShrink={0}>
        <Avatar.Fallback name={conversation.title || ""} />
        {conversation.avatarUrl && <Avatar.Image src={conversation.avatarUrl} />}
      </Avatar.Root>

      <Flex direction="column" minW={0}>
        <Text className="title-styles" fontSize="sm" fontWeight="900" lineClamp={1}>
          {conversation.title}
        </Text>
        <Text className="text-styles" fontSize="xs" fontWeight="700" color="rgba(229,231,235,0.82)" lineClamp={1}>
          {conversation.participantNames.join(", ")}
        </Text>
      </Flex>
    </Flex>
  );

  return (
    <Flex
      alignItems="center"
      justifyContent="space-between"
      w="100%"
      px={{ base: 3, md: 5 }}
      py={3}
      borderBottom="1px solid"
      borderColor="rgba(229,231,235,0.2)"
      bg="variantSecondary"
      gap={3}
    >
      <Flex alignItems="center" gap={3} minW={0}>
        {showBackButton && (
          <IconButton
            aria-label="Back to conversation list"
            variant="ghost"
            borderRadius="full"
            size="sm"
            color="text"
            onClick={onBack}
          >
            <LuArrowLeft />
          </IconButton>
        )}

        {profilePath ? (
          <Link
            asChild
            cursor="pointer"
            textDecoration="none"
            _hover={{ textDecoration: "none", opacity: 0.9 }}
          >
            <RouterLink to={profilePath}>
              {conversationIdentity}
            </RouterLink>
          </Link>
        ) : (
          conversationIdentity
        )}
      </Flex>

      <Flex alignItems="center" gap={2}>
        <Badge
          borderRadius="full"
          px={3}
          py={1}
          bg={isContactOnline ? "rgba(112,205,75,0.24)" : "rgba(229,231,235,0.12)"}
          color={isContactOnline ? "primary" : "variantText"}
          className="text-styles"
          fontSize="xs"
          fontWeight="800"
        >
          {isContactOnline ? "Online" : "Offline"}
        </Badge>

        <Badge
          display={{ base: "none", md: "inline-flex" }}
          borderRadius="full"
          px={3}
          py={1}
          bg={isSocketConnected ? "rgba(112,205,75,0.2)" : "rgba(229,231,235,0.1)"}
          color={isSocketConnected ? "primary" : "variantText"}
          className="text-styles"
          fontSize="xs"
          fontWeight="800"
        >
          {isSocketConnected ? "Realtime on" : "Realtime off"}
        </Badge>

        {!hideDeleteButton && (
          <IconButton
            aria-label="Delete discussion"
            size="sm"
            borderRadius="full"
            variant="ghost"
            color="rgba(229,231,235,0.75)"
            _hover={{ bg: "rgba(255,153,102,0.24)", color: "error" }}
            onClick={() => {
              void onDeleteConversation();
            }}
          >
            <LuTrash2 />
          </IconButton>
        )}
      </Flex>
    </Flex>
  );
}

export default ChatConversationHeader;
