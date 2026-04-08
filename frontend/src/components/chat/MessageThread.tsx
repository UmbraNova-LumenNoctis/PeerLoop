import { useEffect, useRef } from "react";
import { Box, Flex, Spinner, Text, VStack } from "@chakra-ui/react";
import type { ChatMessage } from "@/types/chat";
import MessageBubble from "@/components/chat/MessageBubble";

interface MessageThreadProps {
  messages: ChatMessage[];
  currentUserId: string | null;
  isLoading: boolean;
}

function MessageThread({ messages, currentUserId, isLoading }: MessageThreadProps) {
  const threadRef = useRef<HTMLDivElement | null>(null);
  const hasMessages = messages.length > 0;

  useEffect(() => {
    const node = threadRef.current;
    if (!node) {
      return;
    }

    node.scrollTo({
      top: node.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  return (
    <Flex
      flex={1}
      direction="column"
      minH={0}
      bg="linear-gradient(180deg, rgba(61,71,74,0.72) 0%, rgba(38,39,45,0.9) 100%)"
    >
      {isLoading && !hasMessages ? (
        <Flex flex={1} alignItems="center" justifyContent="center">
          <Spinner size="lg" color="primary" />
        </Flex>
      ) : !hasMessages ? (
        <Flex flex={1} alignItems="center" justifyContent="center" px={6}>
          <Box textAlign="center" maxW="380px">
            <Text className="title-styles" fontSize="lg" fontWeight="900" mb={1}>
              Start the conversation
            </Text>
            <Text className="text-styles" fontSize="sm" fontWeight="700" color="rgba(229,231,235,0.8)">
              Messages, images, and videos will appear here in real time.
            </Text>
          </Box>
        </Flex>
      ) : (
        <>
          {isLoading && (
            <Flex px={{ base: 3, md: 6 }} py={2}>
              <Spinner size="sm" color="primary" />
            </Flex>
          )}
          <VStack
            ref={threadRef}
            align="stretch"
            gap={3}
            flex={1}
            overflowY="auto"
            px={{ base: 3, md: 6 }}
            py={4}
          >
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                isMine={message.sender_id === currentUserId}
              />
            ))}
          </VStack>
        </>
      )}
    </Flex>
  );
}

export default MessageThread;
