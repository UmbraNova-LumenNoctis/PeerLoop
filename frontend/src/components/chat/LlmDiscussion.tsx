import { useEffect, useRef, useState } from "react";
import { Box, Button, Flex, IconButton, Input, Spinner, Text, VStack } from "@chakra-ui/react";
import { LuArrowLeft, LuBot, LuSend, LuTrash2 } from "react-icons/lu";
import { clearLlmHistory, fetchLlmHistory, sendLlmPrompt } from "@/services/chatService";

interface LlmMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface LlmDiscussionProps {
  showBackButton?: boolean;
  onBack?: () => void;
}

const WELCOME_MESSAGE: LlmMessage = {
  id: "assistant-welcome",
  role: "assistant",
  content: "Hi, I am your LLM assistant. Ask me anything about your project.",
};

const LLM_PROMPT_MAX_LENGTH = 8000;

function LlmDiscussion({ showBackButton = false, onBack }: LlmDiscussionProps) {
  const [input, setInput] = useState<string>("");
  const [isHistoryLoading, setIsHistoryLoading] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isClearingHistory, setIsClearingHistory] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [messages, setMessages] = useState<LlmMessage[]>([]);
  const threadRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadHistory = async () => {
      setIsHistoryLoading(true);
      setError("");

      try {
        const history = await fetchLlmHistory(300, 0);
        if (cancelled) {
          return;
        }

        const mappedHistory = history.map((item) => ({
          id: item.id,
          role: item.role,
          content: item.content,
        }));
        setMessages(mappedHistory.length > 0 ? mappedHistory : [WELCOME_MESSAGE]);
      } catch {
        if (!cancelled) {
          setMessages([WELCOME_MESSAGE]);
          setError("Unable to load LLM history.");
        }
      } finally {
        if (!cancelled) {
          setIsHistoryLoading(false);
        }
      }
    };

    void loadHistory();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const node = threadRef.current;
    if (!node) {
      return;
    }

    node.scrollTo({
      top: node.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  const submitPrompt = async () => {
    const prompt = input.trim();
    if (!prompt || isLoading || isHistoryLoading) {
      return;
    }
    if (prompt.length > LLM_PROMPT_MAX_LENGTH) {
      setError(`Prompt is too long (max ${LLM_PROMPT_MAX_LENGTH} characters).`);
      return;
    }

    const userMessage: LlmMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: prompt,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setError("");
    setIsLoading(true);

    try {
      const response = await sendLlmPrompt(prompt);
      const assistantMessage: LlmMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.text,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      setError("LLM is currently unavailable.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = async () => {
    if (isLoading || isHistoryLoading || isClearingHistory) {
      return;
    }

    const previousMessages = [...messages];

    // Optimistic clear: hide messages immediately.
    setMessages([WELCOME_MESSAGE]);
    setIsClearingHistory(true);
    setError("");
    try {
      await clearLlmHistory();
    } catch {
      setMessages(previousMessages);
      setError("Unable to clear LLM history.");
    } finally {
      setIsClearingHistory(false);
    }
  };

  return (
    <Flex direction="column" h="100%" w="100%" bg="secondary">
      <Flex
        alignItems="center"
        gap={2}
        px={{ base: 4, md: 6 }}
        py={3}
        borderBottom="1px solid"
        borderColor="rgba(229,231,235,0.2)"
        bg="variantSecondary"
      >
        {showBackButton && (
          <IconButton
            aria-label="Back to chats"
            variant="ghost"
            borderRadius="full"
            size="sm"
            color="text"
            onClick={onBack}
          >
            <LuArrowLeft />
          </IconButton>
        )}
        <LuBot color="#70cd4b" />
        <Text className="title-styles" fontWeight="900" fontSize="md">
          LLM Discussion
        </Text>
        <Button
          ml="auto"
          size="xs"
          borderRadius="full"
          bg="rgba(255,153,102,0.2)"
          _hover={{ bg: "rgba(255,153,102,0.28)" }}
          color="error"
          disabled={isLoading || isHistoryLoading || isClearingHistory}
          onClick={() => {
            void handleClearHistory();
          }}
        >
          {isClearingHistory ? <Spinner size="xs" /> : <><LuTrash2 /> Clear</>}
        </Button>
      </Flex>

      <VStack
        ref={threadRef}
        align="stretch"
        gap={3}
        flex={1}
        overflowY="auto"
        px={{ base: 3, md: 6 }}
        py={4}
        bg="linear-gradient(180deg, rgba(61,71,74,0.72) 0%, rgba(38,39,45,0.9) 100%)"
      >
        {isHistoryLoading && (
          <Flex alignItems="center" justifyContent="center" py={8}>
            <Spinner color="primary" />
          </Flex>
        )}

        {messages.map((message) => (
          <Box
            key={message.id}
            alignSelf={message.role === "user" ? "flex-end" : "flex-start"}
            maxW={{ base: "90%", md: "75%" }}
            bg={message.role === "user" ? "primary" : "rgba(255,255,255,0.1)"}
            color={message.role === "user" ? "secondary" : "text"}
            borderRadius="2xl"
            px={4}
            py={3}
          >
            <Text className="text-styles" fontWeight="900" fontSize="xs" mb={1} color={message.role === "user" ? "secondary" : "primary"}>
              {message.role === "user" ? "You" : "Assistant"}
            </Text>
            <Text className="text-styles" fontWeight="800" whiteSpace="pre-wrap">
              {message.content}
            </Text>
          </Box>
        ))}
      </VStack>

      <Box px={{ base: 3, md: 6 }} py={3} bg="variantSecondary" borderTop="1px solid" borderColor="rgba(229,231,235,0.2)">
        {error && (
          <Text className="text-styles" fontWeight="800" color="error" fontSize="xs" mb={2}>
            {error}
          </Text>
        )}

        <Flex as="form" onSubmit={(event) => {
          event.preventDefault();
          void submitPrompt();
        }} gap={2}>
          <Input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask the LLM assistant"
            maxLength={LLM_PROMPT_MAX_LENGTH}
            className="text-styles"
            fontWeight="800"
            borderRadius="full"
            bg="rgba(255,255,255,0.08)"
            border="1px solid"
            borderColor="rgba(229,231,235,0.28)"
            px={4}
            _placeholder={{ color: "rgba(229,231,235,0.62)", fontWeight: "700" }}
            _focus={{ borderColor: "primary" }}
            disabled={isLoading || isHistoryLoading}
          />

          <Button
            type="submit"
            borderRadius="full"
            bg="primary"
            color="secondary"
            fontWeight="900"
            minW="96px"
            disabled={isLoading || isHistoryLoading || !input.trim()}
          >
            {isLoading ? <Spinner size="sm" /> : <><LuSend /> Send</>}
          </Button>
        </Flex>
      </Box>
    </Flex>
  );
}

export default LlmDiscussion;
