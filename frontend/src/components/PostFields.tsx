import {
    Textarea,
    FileUpload,
    HStack,
    Text,
    Menu,
    ProgressCircle
} from "@chakra-ui/react";
import { LuFileImage, LuLaugh } from "react-icons/lu";
import { useRef, useEffect, JSX, useState } from "react";
import { FileViewer } from "@/components/FileViewer";
import { Icon } from "@/components/Icon";

const COMMON_EMOJIS = ["😀", "😂", "😍", "🔥", "🎉", "👍", "❤️"];

interface PostFieldsProps
{
    description: string;
    setDescription: (value: string) => void;
    files?: File[];
    setFiles?: (files: File[]) => void;
    imageUrl?: string | null;
    maxLength?: number;
    isComment?: boolean;
};

export const PostFields = ({
    description,
    setDescription,
    files,
    setFiles,
    imageUrl,
    maxLength = 500,
    isComment = false
}: PostFieldsProps): JSX.Element => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const [emojiPicker, setEmojiPicker] = useState<boolean>(false);
    const [isUploading, setIsUploading] = useState<boolean>(false);
    const [uploadProgress, setUploadProgress] = useState<number>(0);

    useEffect(() => {
        const textarea = textareaRef.current;
        if (!textarea) return;

        textarea.style.height = "auto";
        textarea.style.height = textarea.scrollHeight + "px";
    }, [description]);

    const handleFileAccept = (files: File[]) => {
        if (!files.length) return;

        setIsUploading(true);
        const reader = new FileReader();

        reader.onprogress = (event) => {
            if (event.lengthComputable) {
                const progress = Math.round((event.loaded / event.total) * 100);
                setUploadProgress(progress);
            }
        };

        reader.onloadend = () => {
            setFiles(files);
            setUploadProgress(100);
            setTimeout(() => {
                setIsUploading(false);
                setUploadProgress(0);
            }, 1000);
        };

        reader.readAsDataURL(files[0]);
    };

    return (
        <>
            <Textarea
                ref={textareaRef}
                value={description}
                placeholder="What's on your mind?"
                className="text-styles"
                border="none"
                onChange={(e) => setDescription(e.target.value)}
                _placeholder={{ fontFamily: "Montserrat", color: "text" }}
                _focus={{ focusRing: "none" }}
                minH="100px"
                p={0}
                scrollbar="hidden"
                maxLength={maxLength}
                resize="none"
            />

            <FileUpload.Root
                acceptedFiles={files}
                accept="image/*, video/*"
                onFileAccept={(e) => handleFileAccept(e.files)}
                position="relative"
                maxFiles={1}
            >
                <FileUpload.HiddenInput />
                <FileViewer files={files} setFiles={setFiles} previewUrl={imageUrl} />

                <HStack
                    w="100%"
                    className="title-styles"
                    justifyContent="space-between"
                >
                    <HStack w="100%" gap={2}>
                        {
                            !isComment && (
                                <FileUpload.Trigger asChild>
                                    <Icon label="Change Image" disabled={isUploading || files.length > 0}>
                                        {isUploading ? (
                                            <ProgressCircle.Root value={uploadProgress}>
                                                <ProgressCircle.Circle>
                                                    <ProgressCircle.Track />
                                                    <ProgressCircle.Range strokeLinecap="round" stroke="primary" />
                                                </ProgressCircle.Circle>
                                            </ProgressCircle.Root>
                                        ) : (
                                            <LuFileImage />
                                        )}
                                    </Icon>
                                </FileUpload.Trigger>
                            )
                        }

                        <Menu.Root onOpenChange={(isOpen) => setEmojiPicker(isOpen.open)}>
                            <Menu.Trigger asChild>
                                <Icon 
                                    label="add emoji" 
                                    bgColor={emojiPicker ? "primary" : "transparent"}
                                    color={emojiPicker ? "secondary" : "text"}
                                >
                                    <LuLaugh />
                                </Icon>
                            </Menu.Trigger>
                            <Menu.Positioner>
                                <Menu.Content
                                    bg="secondary"
                                    borderRadius="full"
                                    overflow="hidden"
                                    p={2} gap={2}
                                >
                                    {COMMON_EMOJIS.map((emoji) => (
                                        <Icon
                                            label="Emoji"
                                            key={emoji} size="xs"
                                            onClick={() => setDescription(`${description}${emoji}`)}
                                        >
                                            {emoji}
                                        </Icon>
                                    ))}
                                </Menu.Content>
                            </Menu.Positioner>
                        </Menu.Root>
                    </HStack>

                    <Text
                        textAlign="right"
                        className="text-styles" 
                        fontWeight="medium" 
                        minW="150px"
                    >
                        {description.length}/{maxLength} characters
                    </Text>
                </HStack>
            </FileUpload.Root>
        </>
    );
};
