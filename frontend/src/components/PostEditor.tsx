import { 
    HStack, 
    Dialog,
    Text,
    Stack,
    Spinner,
    Flex
} from '@chakra-ui/react';
import { LuCheck, LuX } from 'react-icons/lu';
import { useState, useEffect, useCallback, useContext, JSX } from 'react';
import { timeFormat } from "@/utils/PostUtils";
import { AlertContext } from "@/context/alertContext";
import { NotificationContext } from "@/context/notificationContext";
import { CustomButton } from '@/components/CustomButton';
import { PostFields } from "@/components/PostFields";
import { Icon } from "@/components/Icon";
import { User } from '@/components/User';
import { PostData } from '@/types/Post';
import useApi from "@/hooks/useAPI";

export const PostEditor = (
    { postId, isOpen=false, onClose }
    : { postId: string, isOpen: boolean, onClose: (value: void) => void }
): JSX.Element => {
    const { isLoading, execute } = useApi();
    const { showAlert } = useContext(AlertContext);
    const { refreshNotifications } = useContext(NotificationContext);
    const [post, setPost] = useState<PostData | null>(null);
    const [description, setDescription] = useState<string>("");
    const [files, setFiles] = useState<File[]>([]);

    useEffect(() => {
       if (isOpen) retrievePost();
    }, [isOpen]);

    const cancelChanges = (): void => {
        if (description !== post.content)
            setDescription(post.content || "");
        setFiles([]);
        onClose();
    }

    const retrievePost = useCallback(async (): Promise<void> => {
        try {
            const post: any = await execute({
                url: import.meta.env.VITE_API_GET_POST_ENDPOINT.replace("{post_id}", postId),
                useToken: true
            });
            if (!post) return;

            const newPostData: PostData = {
                id: post.id,
                image: post.media_url,
                content: post.content,
                createdAt: post.created_at,
                authorId: post.user_id,
                authorPseudonym: post.author_pseudo,
                authorAvatar: post.author_avatar_url,
                comments: post.comments_count || 0,
                likes: post.like_count || 0,
                likedByMe: post.liked_by_me || false
            };

            setPost(newPostData);
            setDescription(newPostData.content || "");
        } catch(err: any) {
            console.error("Failed to retrieve post:", err.message);
            onClose();
        }
    }, [postId]);

    const handleUpdate = async (e: React.FormEvent) => {
        e.preventDefault();

        try {
            let media_id: string | null = null;

            if (files.length > 0) {
                const FileData = new FormData();
                FileData.append("file", files[0]);

                const uploadedFile: any = await execute({
                    url: import.meta.env.VITE_API_UPLOAD_FILE_ENDPOINT,
                    method: "POST",
                    body: FileData,
                    useToken: true
                });
                media_id = uploadedFile.media_id || null;
            }

            await execute({
                url: import.meta.env.VITE_API_UPDATE_POST_ENDPOINT.replace("{post_id}", postId),
                method: "PATCH",
                body: {
                    content: description.trim(),
                    ...(media_id && { media_id })
                },
                useToken: true
            });

            onClose();
            refreshNotifications();
            showAlert(true, "Post updated successfully");
            setTimeout(() => window.location.reload(), 3000);
        } catch (err) {
            console.error("Update failed:", err.message);
            showAlert(false, "Update failed. Try Again!");
        }
    };

    return (
        <Dialog.Root 
            open={isOpen}
            onOpenChange={(e) => !e.open && cancelChanges()}
            placement="center"
        >
            <Dialog.Positioner w="100vw" h="100vh">
                <Dialog.Content w="100%" minH={{ base: "100vh", md: "auto" }} bg="variantSecondary" p={2}>
                    {
                        !post
                        ? (
                            <Flex w="100%" h="100%" justifyContent="center" alignItems="center">
                                <Spinner color="primary" size="md"/>
                            </Flex>
                        ) : (<>
                            <Dialog.Header justifyContent="space-between">
                                <HStack gap="3">
                                    <User name={post.authorPseudonym} picture={post.authorAvatar} />
                                    
                                    <Stack gap="0">
                                        <Text className="title-styles" fontSize="sm" fontWeight="medium">{post.authorPseudonym}</Text>
                                        <Text className="text-styles" fontSize="xs">{timeFormat(post.createdAt)}</Text>
                                    </Stack>
                                </HStack>
                                
                                <Icon label="Close Update Menu" onClick={cancelChanges}>
                                    <LuX />
                                </Icon>
                            </Dialog.Header>

                            <Dialog.Body 
                                display="flex" 
                                justifyContent="space-between" 
                                alignItems="center"
                                flexDirection="column"
                                gap={5}
                            >
                                <PostFields
                                    description={description}
                                    setDescription={setDescription}
                                    files={files}
                                    setFiles={setFiles}
                                    imageUrl={post.image}
                                />
                            </Dialog.Body>

                            <Dialog.Footer>
                                <CustomButton
                                    label="Save Changes"
                                    disabled={
                                        isLoading 
                                        || description.trim() === "" 
                                        || (description.trim() === post.content && files.length === 0)}
                                    onClick={handleUpdate}
                                >
                                    <LuCheck /> Save
                                </CustomButton>

                                <CustomButton 
                                    label="Cancel Changes"
                                    onClick={cancelChanges}
                                    isNeutral={true}
                                >
                                    Cancel
                                </CustomButton>
                            </Dialog.Footer>
                        </>)
                    }
                </Dialog.Content>
            </Dialog.Positioner>
        </Dialog.Root>
    );
};
