import { Avatar, Badge, Box, Flex, IconButton, Spinner, Text } from "@chakra-ui/react";
import { LuTrash2 } from "react-icons/lu";

interface ConversationItemProps {
  title: string;
  avatarUrl: string | null;
  lastMessageText: string;
  lastMessageAt: string | null;
  unreadCount: number;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  canDelete?: boolean;
  isDeleting?: boolean;
}

const formatLastMessageDate = (value: string | null): string => {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const now = new Date();
  const isSameDay =
    date.getDate() === now.getDate()
    && date.getMonth() === now.getMonth()
    && date.getFullYear() === now.getFullYear();

  if (isSameDay) {
    return new Intl.DateTimeFormat("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(date);
};

function ConversationItem({
  title,
  avatarUrl,
  lastMessageText,
  lastMessageAt,
  unreadCount,
  isActive,
  onSelect,
  onDelete,
  canDelete = true,
  isDeleting = false,
}: ConversationItemProps) {
  return (
    <Flex
      alignItems="center"
      gap={2}
      borderRadius="xl"
      bg={isActive ? "rgba(112,205,75,0.2)" : "transparent"}
      _hover={{ bg: "rgba(112,205,75,0.16)" }}
      px={2}
      py={1.5}
    >
      <Flex
        role="button"
        tabIndex={0}
        onClick={onSelect}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onSelect();
          }
        }}
        w="100%"
        alignItems="center"
        gap={3}
        minW={0}
        pointerEvents={isDeleting ? "none" : "auto"}
        opacity={isDeleting ? 0.55 : 1}
      >
        <Avatar.Root size="md" flexShrink={0}>
          <Avatar.Fallback name={title || ""} />
          {avatarUrl && <Avatar.Image src={avatarUrl} />}
        </Avatar.Root>

        <Box flex={1} minW={0} textAlign="left">
          <Flex w="100%" alignItems="center" justifyContent="space-between" gap={2}>
            <Text className="title-styles" fontWeight="800" fontSize="sm" lineClamp={1}>
              {title}
            </Text>
            <Text className="text-styles" fontWeight="700" fontSize="xs" color="variantText" flexShrink={0}>
              {formatLastMessageDate(lastMessageAt)}
            </Text>
          </Flex>

          <Flex w="100%" alignItems="center" justifyContent="space-between" gap={2}>
            <Text className="text-styles" fontWeight="700" fontSize="xs" color="variantText" lineClamp={1}>
              {lastMessageText}
            </Text>
            {unreadCount > 0 && (
              <Badge
                minW="22px"
                h="22px"
                borderRadius="full"
                display="flex"
                alignItems="center"
                justifyContent="center"
                bg="primary"
                color="secondary"
                fontSize="xs"
                fontWeight="bold"
                px={2}
                flexShrink={0}
              >
                {unreadCount > 99 ? "99+" : unreadCount}
              </Badge>
            )}
          </Flex>
        </Box>
      </Flex>

      {canDelete && (
        <IconButton
          aria-label="Delete conversation"
          size="xs"
          borderRadius="full"
          variant="ghost"
          color="rgba(229,231,235,0.75)"
          _hover={{ bg: "rgba(255,153,102,0.24)", color: "error" }}
          disabled={isDeleting}
          onClick={(event) => {
            event.stopPropagation();
            onDelete();
          }}
        >
          {isDeleting ? <Spinner size="xs" /> : <LuTrash2 />}
        </IconButton>
      )}
    </Flex>
  );
}

export default ConversationItem;
