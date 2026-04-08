import { CommentData } from "@/types/Post";
import { JSX, useState, useContext } from "react";
import { Menu as ChakraMenu } from "@chakra-ui/react";
import { AlertContext } from '@/context/alertContext';
import { NotificationContext } from "@/context/notificationContext";
import { LuEllipsis, LuEllipsisVertical, LuPencil, LuTrash2 } from "react-icons/lu";
import { InteractionButton } from "@/components/InteractionButton";
import { CommentEditor } from "@/components/CommentEditor";
import { PostEditor } from '@/components/PostEditor';
import { Icon } from "@/components/Icon";
import useApi from "@/hooks/useAPI";

const MenuBody = (
    { isActive=false, onOpen, handleDelete }
    : { isActive: boolean, onOpen: () => void, handleDelete: () => Promise<void> }
): JSX.Element => {
    return (
        <ChakraMenu.Positioner>
            <ChakraMenu.Content
                className="tile-styles"
                bg="variantSecondary"
                borderColor="text"
                borderWidth="1px"
                borderRadius="md"
                w="100%"
            >
                <ChakraMenu.Item value="edit" bgColor="transparent" onClick={onOpen}>
                    <InteractionButton
                        label="Edit Post"
                        justifyContent="flex-start"
                        _hover={{ bg: "primary", color: "secondary" }}
                        w="100%" px={2}
                        disabled={!isActive}
                    >
                        <LuPencil /> Edit
                    </InteractionButton>
                </ChakraMenu.Item>
                <ChakraMenu.Item value="delete" bgColor="transparent" onClick={handleDelete}>
                    <InteractionButton
                        label="Delete Post"
                        justifyContent="flex-start"
                        w="100%" bg="danger"
                        disabled={!isActive}
                        px={2}
                    >
                        <LuTrash2 /> Delete
                    </InteractionButton>
                </ChakraMenu.Item>
            </ChakraMenu.Content>
        </ChakraMenu.Positioner>
    );
}

export const PostMenu = (
    { postId, isAuthor = false }:
    { postId: string, isAuthor: boolean }
): JSX.Element => {
    const [menuOpen, setMenuOpen] = useState<boolean>(false);
    const [isEditing, setIsEditing] = useState<boolean>(false);
    const { refreshNotifications } = useContext(NotificationContext);
    const { showAlert } = useContext(AlertContext);
    const { execute } = useApi();

    const deletePost = async (): Promise<void> => {
        try {
            await execute({
                url: import.meta.env.VITE_API_DELETE_POST_ENDPOINT.replace("{post_id}", postId),
                method: "DELETE",
                useToken: true
            });

            const cacheKey = "post:cache:v1";
            const cachedPostsRaw = sessionStorage.getItem(cacheKey);
            if (cachedPostsRaw) {
                const cachedPosts = JSON.parse(cachedPostsRaw) as Record<string, any>;
                if (cachedPosts[postId]) {
                    delete cachedPosts[postId];
                    sessionStorage.setItem(cacheKey, JSON.stringify(cachedPosts));
                }
            }
            
            refreshNotifications();
            showAlert(true, "Post deleted successfully!");
            setTimeout(() => window.location.reload(), 3000);
        } catch(err: any) {
            console.error("Failed to delete post:", err.message);
            showAlert(false, "Failed to delete Post. Try Again!");
        }
    }

    return (
        <>
            <ChakraMenu.Root onOpenChange={(isOpen) => setMenuOpen(isOpen.open)}>
                <ChakraMenu.Trigger asChild>
                    <Icon
                        label="More Options"
                        bgColor={menuOpen ? "primary" : "transparent"}
                        color={menuOpen ? "secondary" : "text"}
                    >
                        <LuEllipsis />
                    </Icon>
                </ChakraMenu.Trigger>
                
                <MenuBody 
                    isActive={isAuthor} 
                    onOpen={() => setIsEditing(true)} 
                    handleDelete={deletePost}
                />
            </ChakraMenu.Root>

            <PostEditor 
                postId={postId} 
                isOpen={isEditing} 
                onClose={() => setIsEditing(false)}
            />
        </>
    );
};

export const CommentMenu = (
    { comment, isAuthor = false, onChanges }:
    { comment: CommentData, isAuthor: boolean, onChanges: () => void }
): JSX.Element => {
    const [menuOpen, setMenuOpen] = useState<boolean>(false);
    const [isEditing, setIsEditing] = useState<boolean>(false);
    const { refreshNotifications } = useContext(NotificationContext);
    const { showAlert } = useContext(AlertContext);
    const { execute } = useApi();

    const deleteComment = async (): Promise<void> => {
        try {
            await execute({
                url: import.meta.env.VITE_API_INTERACT_COMMENT_ENDPOINT.replace("{comment_id}", comment.id),
                method: "DELETE",
                useToken: true
            });

            showAlert(true, "Comment deleted successfully!");
            refreshNotifications();
            onChanges();
        } catch(err: any) {
            console.error("Failed to delete comment:", err.message);
            showAlert(false, "Failed to delete comment. Try Again!");
        }
    }

    return (
        <>
            <ChakraMenu.Root onOpenChange={(isOpen) => setMenuOpen(isOpen.open)}>
                <ChakraMenu.Trigger asChild>
                    <Icon
                        label="More Options"
                        bgColor={menuOpen ? "primary" : "transparent"}
                        color={menuOpen ? "secondary" : "text"}
                    >
                        <LuEllipsisVertical />
                    </Icon>
                </ChakraMenu.Trigger>
                
                <MenuBody 
                    isActive={isAuthor} 
                    onOpen={() => setIsEditing(true)} 
                    handleDelete={deleteComment}
                />
            </ChakraMenu.Root>

            <CommentEditor 
                comment={comment}
                isOpen={isEditing} 
                onClose={() => setIsEditing(false)}
                onChanges={onChanges}
            />
        </>
    );
};

