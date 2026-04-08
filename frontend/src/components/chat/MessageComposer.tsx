import { useRef, useState } from "react";
import { Box, Button, Flex, IconButton, Input, Spinner, Text } from "@chakra-ui/react";
import { LuImagePlus, LuSendHorizontal, LuSmile } from "react-icons/lu";

interface MessageComposerProps {
  disabled?: boolean;
  isSending: boolean;
  isUploadingFile: boolean;
  uploadProgress: number;
  onSend: (content: string) => Promise<void>;
  onSendFile: (file: File, caption?: string) => Promise<void>;
}

function MessageComposer({
  disabled = false,
  isSending,
  isUploadingFile,
  uploadProgress,
  onSend,
  onSendFile,
}: MessageComposerProps) {
  const commonEmojis = ["😀", "😂", "😍", "🔥", "🎉", "👍", "🙏", "❤️"];
  const [content, setContent] = useState<string>("");
  const [showEmojiPicker, setShowEmojiPicker] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const submitMessage = async () => {
    const normalizedContent = content.trim();
    if (!normalizedContent || disabled || isUploadingFile) {
      return;
    }

    try {
      await onSend(normalizedContent);
      setContent("");
    } catch {
      // Keep text if send fails.
    }
  };

  const submitFile = async (file: File) => {
    if (disabled || isUploadingFile) {
      return;
    }

    try {
      await onSendFile(file, content.trim());
      setContent("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch {
      // Keep content for retry if upload fails.
    }
  };

  return (
    <Flex
      as="form"
      onSubmit={(event) => {
        event.preventDefault();
        void submitMessage();
      }}
      direction="column"
      gap={2}
      px={{ base: 3, md: 6 }}
      py={3}
      bg="variantSecondary"
      borderTop="1px solid"
      borderColor="rgba(229,231,235,0.2)"
    >
      <Flex alignItems="center" gap={2}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,video/*"
          style={{ display: "none" }}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              void submitFile(file);
            }
          }}
        />

        <IconButton
          type="button"
          aria-label="Insert emoji"
          borderRadius="full"
          bg="rgba(255,255,255,0.14)"
          color="text"
          onClick={() => setShowEmojiPicker((previous) => !previous)}
          disabled={disabled || isUploadingFile}
          _hover={{ bg: "rgba(255,255,255,0.22)" }}
        >
          <LuSmile />
        </IconButton>

        <IconButton
          type="button"
          aria-label="Upload image or video"
          borderRadius="full"
          bg="rgba(112,205,75,0.18)"
          color="primary"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || isUploadingFile}
          _hover={{ bg: "rgba(112,205,75,0.28)" }}
        >
          {isUploadingFile ? <Spinner size="sm" /> : <LuImagePlus />}
        </IconButton>

        <Input
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="Write a message"
          className="text-styles"
          fontWeight="800"
          borderRadius="full"
          bg="rgba(255,255,255,0.08)"
          border="1px solid"
          borderColor="rgba(229,231,235,0.28)"
          px={4}
          _placeholder={{ color: "rgba(229,231,235,0.62)", fontWeight: "700" }}
          _focus={{ borderColor: "primary" }}
          disabled={disabled || isUploadingFile}
        />

        <Button
          type="submit"
          display={{ base: "none", md: "inline-flex" }}
          borderRadius="full"
          bg="primary"
          color="secondary"
          px={5}
          minW="90px"
          fontWeight="900"
          disabled={disabled || isUploadingFile || !content.trim()}
          _hover={{ opacity: 0.9 }}
        >
          {isSending ? <Spinner size="sm" /> : "Send"}
        </Button>

        <IconButton
          type="submit"
          aria-label="Send message"
          display={{ base: "inline-flex", md: "none" }}
          borderRadius="full"
          bg="primary"
          color="secondary"
          disabled={disabled || isUploadingFile || !content.trim()}
        >
          {isSending ? <Spinner size="sm" /> : <LuSendHorizontal />}
        </IconButton>
      </Flex>

      {showEmojiPicker && !disabled && (
        <Flex
          gap={1}
          p={1}
          borderRadius="full"
          border="1px solid rgba(229,231,235,0.25)"
          bg="rgba(20,24,31,0.8)"
          overflowX="auto"
        >
          {commonEmojis.map((emoji) => (
            <Button
              key={emoji}
              type="button"
              size="xs"
              minW="30px"
              h="30px"
              p={0}
              borderRadius="full"
              bg="transparent"
              _hover={{ bg: "rgba(255,255,255,0.14)" }}
              onClick={() => setContent((previous) => `${previous}${emoji}`)}
            >
              {emoji}
            </Button>
          ))}
        </Flex>
      )}

      {isUploadingFile && (
        <Box>
          <Flex alignItems="center" justifyContent="space-between" mb={1}>
            <Text className="text-styles" fontSize="xs" fontWeight="800" color="rgba(229,231,235,0.76)">
              Uploading media...
            </Text>
            <Text className="text-styles" fontSize="xs" fontWeight="900" color="primary">
              {Math.max(0, Math.min(100, uploadProgress))}%
            </Text>
          </Flex>
          <Box
            w="100%"
            h="6px"
            borderRadius="full"
            bg="rgba(229,231,235,0.18)"
            overflow="hidden"
          >
            <Box
              h="100%"
              bg="primary"
              w={`${Math.max(0, Math.min(100, uploadProgress))}%`}
              transition="width 0.18s ease"
            />
          </Box>
        </Box>
      )}

      {!isUploadingFile && isSending && (
        <Text className="text-styles" fontSize="xs" fontWeight="800" color="rgba(229,231,235,0.76)">
          Sending message...
        </Text>
      )}
    </Flex>
  );
}

export default MessageComposer;
