import { 
    HStack, 
    Dialog,
    Text,
    Stack
} from '@chakra-ui/react';
import { CommentData } from "@/types/Post";
import { LuCheck, LuX } from 'react-icons/lu';
import { useState, useContext, JSX } from 'react';
import { timeFormat } from "@/utils/PostUtils";
import { AlertContext } from "@/context/alertContext";
import { NotificationContext } from "@/context/notificationContext";
import { CustomButton } from '@/components/CustomButton';
import { PostFields } from '@/components/PostFields';
import { Icon } from "@/components/Icon";
import { User } from '@/components/User';
import useApi from "@/hooks/useAPI";

interface CommentEditorProps
{
    comment: CommentData;
    isOpen: boolean;
    onClose: (value: void) => void;
    onChanges: (value: void) => void;
}

export const CommentEditor = (
    { comment, isOpen=false, onClose, onChanges }: CommentEditorProps
): JSX.Element => {
    const { isLoading, execute } = useApi();
    const { showAlert } = useContext(AlertContext);
    const { refreshNotifications } = useContext(NotificationContext);
    const [newComment, setNewComment] = useState<string>(comment.content);

    const cancelChanges = (): void => {
        setNewComment(comment.content);
        onClose();
    }

    const updateComment = async (): Promise<void> => {
        try {
            await execute({
                url: import.meta.env.VITE_API_INTERACT_COMMENT_ENDPOINT.replace("{comment_id}", comment.id),
                method: "PATCH",
                body: { content: newComment },
                useToken: true
            });

            showAlert(true, "Comment updated successfully.");
            refreshNotifications();
            onChanges();
            onClose();
        } catch(err: any) {
            console.error("Failed to update comment:", err.message);
            showAlert(false, "Failed to update comment. Try Again!");
            onClose();
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
                    <Dialog.Header justifyContent="space-between">
                        <HStack gap="3">
                            <User name={comment.authorPseudo} picture={comment.authorAvatar} />
                            
                            <Stack gap="0">
                                <Text className="title-styles" fontSize="sm" fontWeight="medium">{comment.authorPseudo}</Text>
                                <Text className="text-styles" fontSize="xs">{timeFormat(comment.createdAt)}</Text>
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
                    >
                        <PostFields 
                            description={newComment} 
                            setDescription={setNewComment}
                            isComment={true}
                            maxLength={250}
                        />
                    </Dialog.Body>

                    <Dialog.Footer>
                        <CustomButton
                            label="Save Changes"
                            disabled={
                                isLoading 
                                || newComment.trim() === "" 
                                || newComment.trim() === comment.content}
                            onClick={updateComment}
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
                </Dialog.Content>
            </Dialog.Positioner>
        </Dialog.Root>
    );
};
