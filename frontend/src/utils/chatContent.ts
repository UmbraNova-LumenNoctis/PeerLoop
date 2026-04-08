import type { ChatAttachmentPayload, ParsedChatContent } from "@/types/chat";

export const CHAT_ATTACHMENT_PREFIX = "__CHAT_ATTACHMENT__:";

export const buildAttachmentMessageContent = (
  attachment: ChatAttachmentPayload,
  caption?: string,
): string => {
  const normalizedCaption = (caption || "").trim();
  const payload = `${CHAT_ATTACHMENT_PREFIX}${JSON.stringify(attachment)}`;
  return normalizedCaption ? `${normalizedCaption}\n${payload}` : payload;
};

export const parseChatContent = (content: string): ParsedChatContent => {
  const value = content || "";
  const markerIndex = value.indexOf(CHAT_ATTACHMENT_PREFIX);

  if (markerIndex === -1) {
    return {
      text: value,
      attachment: null,
    };
  }

  const text = value.slice(0, markerIndex).trim();
  const rawPayload = value.slice(markerIndex + CHAT_ATTACHMENT_PREFIX.length).trim();

  try {
    const parsed = JSON.parse(rawPayload) as ChatAttachmentPayload;
    if (!parsed || typeof parsed.url !== "string" || !parsed.url) {
      throw new Error("Invalid attachment payload");
    }

    return {
      text,
      attachment: {
        media_id: parsed.media_id,
        url: parsed.url,
        preview_url: parsed.preview_url,
        detected_type: parsed.detected_type,
        original_name: parsed.original_name,
      },
    };
  } catch {
    return {
      text: value,
      attachment: null,
    };
  }
};

export const isImageAttachment = (detectedType: string | null | undefined): boolean => {
  if (!detectedType) {
    return false;
  }

  return detectedType.toLowerCase().startsWith("image/");
};

export const isVideoAttachment = (detectedType: string | null | undefined): boolean => {
  if (!detectedType) {
    return false;
  }

  return detectedType.toLowerCase().startsWith("video/");
};

export const toConversationPreviewText = (content: string | null): string => {
  if (!content) {
    return "No messages yet";
  }

  const parsed = parseChatContent(content);
  if (!parsed.attachment) {
    return parsed.text || "No messages yet";
  }

  if (isImageAttachment(parsed.attachment.detected_type)) {
    return parsed.text ? `${parsed.text} (Photo)` : "Photo";
  }

  if (isVideoAttachment(parsed.attachment.detected_type)) {
    return parsed.text ? `${parsed.text} (Video)` : "Video";
  }

  return parsed.text ? `${parsed.text} (Attachment)` : "Attachment";
};
