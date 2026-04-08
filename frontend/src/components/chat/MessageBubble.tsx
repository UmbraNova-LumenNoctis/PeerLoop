import { useState } from "react";
import { Avatar, Box, Flex, Link, Text } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";
import type { ChatMessage } from "@/types/chat";
import { isImageAttachment, isVideoAttachment, parseChatContent } from "@/utils/chatContent";

interface MessageBubbleProps {
  message: ChatMessage;
  isMine: boolean;
}

const formatMessageTimestamp = (value: string | null): string => {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};

function MessageBubble({ message, isMine }: MessageBubbleProps) {
  const [isImagePreviewOpen, setIsImagePreviewOpen] = useState<boolean>(false);
  const parsedContent = parseChatContent(message.content || "");
  const attachment = parsedContent.attachment;
  const imageUrl = attachment?.preview_url || attachment?.url || null;
  const profilePath = !isMine ? `/profile/${message.sender_id}` : null;

  return (
    <>
      <Flex
        direction="column"
        alignItems={isMine ? "flex-end" : "flex-start"}
        maxW={{ base: "92%", md: "76%" }}
        alignSelf={isMine ? "flex-end" : "flex-start"}
        gap={1.5}
      >
        {!isMine && (
          <Flex alignItems="center" gap={2}>
            <Link asChild _hover={{ opacity: 0.9 }}>
              <RouterLink to={profilePath || "/profile"}>
                <Avatar.Root size="2xs" flexShrink={0}>
                  <Avatar.Fallback name={message.sender_pseudo || "User"} />
                  {message.sender_avatar_url && <Avatar.Image src={message.sender_avatar_url} />}
                </Avatar.Root>
              </RouterLink>
            </Link>

            <Link asChild _hover={{ textDecoration: "underline" }} color="primary">
              <RouterLink to={profilePath || "/profile"}>
                <Text className="text-styles" fontSize="xs" fontWeight="900">
                  {message.sender_pseudo || "User"}
                </Text>
              </RouterLink>
            </Link>
          </Flex>
        )}

        <Box
          bg={isMine ? "primary" : "rgba(255,255,255,0.1)"}
          color={isMine ? "secondary" : "text"}
          borderRadius="2xl"
          px={4}
          py={3}
          boxShadow={isMine ? "0 8px 20px rgba(112,205,75,0.35)" : "none"}
        >
          {parsedContent.text && (
            <Text
              className="text-styles"
              fontSize="sm"
              fontWeight="800"
              whiteSpace="pre-wrap"
              wordBreak="break-word"
              mb={attachment ? 2 : 0}
            >
              {parsedContent.text}
            </Text>
          )}

          {attachment && (
            <>
              {isImageAttachment(attachment.detected_type) && (
                <Box
                  as="button"
                  type="button"
                  display="block"
                  w="100%"
                  onClick={() => setIsImagePreviewOpen(true)}
                  cursor="zoom-in"
                >
                  <Box
                    as="img"
                    src={imageUrl || ""}
                    alt={attachment.original_name || "Shared image"}
                    maxH="280px"
                    w="100%"
                    objectFit="cover"
                    borderRadius="xl"
                  />
                </Box>
              )}

              {isVideoAttachment(attachment.detected_type) && (
                <Box
                  as="video"
                  src={attachment.url}
                  controls
                  maxH="300px"
                  w="100%"
                  borderRadius="xl"
                  bg="black"
                />
              )}

              {!isImageAttachment(attachment.detected_type) && !isVideoAttachment(attachment.detected_type) && (
                <Link href={attachment.url} target="_blank" color={isMine ? "secondary" : "primary"}>
                  <Text className="text-styles" fontSize="sm" fontWeight="900">
                    Open attachment
                  </Text>
                </Link>
              )}
            </>
          )}

          <Text
            className="text-styles"
            fontSize="10px"
            fontWeight="800"
            mt={2}
            textAlign="right"
            color={isMine ? "rgba(38,39,45,0.8)" : "rgba(229,231,235,0.7)"}
          >
            {formatMessageTimestamp(message.created_at)}
          </Text>
        </Box>
      </Flex>

      {isImagePreviewOpen && imageUrl && (
        <Box
          position="fixed"
          inset={0}
          zIndex={1400}
          bg="rgba(0,0,0,0.86)"
          display="flex"
          alignItems="center"
          justifyContent="center"
          p={4}
          onClick={() => setIsImagePreviewOpen(false)}
          role="dialog"
          aria-modal="true"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setIsImagePreviewOpen(false);
            }
          }}
        >
          <Box
            as="img"
            src={imageUrl}
            alt={attachment?.original_name || "Shared image"}
            maxH="92vh"
            maxW="92vw"
            objectFit="contain"
            borderRadius="xl"
            boxShadow="0 18px 45px rgba(0,0,0,0.5)"
            onClick={(event) => event.stopPropagation()}
          />
        </Box>
      )}
    </>
  );
}

export default MessageBubble;
