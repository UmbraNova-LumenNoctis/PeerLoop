import { useState, useContext, JSX } from 'react';
import { LuTrash2, LuCheck, LuLaugh } from 'react-icons/lu';
import { HStack, Dialog, Text } from '@chakra-ui/react';
import { AlertContext } from "@/context/alertContext";
import { NotificationContext } from "@/context/notificationContext";
import { CustomButton } from '@/components/CustomButton';
import { PostFields } from '@/components/PostFields';
import { Icon } from "@/components/Icon";
import useApi from "@/hooks/useAPI";

export const PostBuilder = (
    { isOpen=false, onClose, onChanges }
    : { isOpen: boolean, onClose: (value: void) => void, onChanges: (value: void) => void }
): JSX.Element => {
    const { isLoading, execute } = useApi();
    const [files, setFiles] = useState<File[]>([]);
    const [description, setDescription] = useState<string>("");
    const { refreshNotifications } = useContext(NotificationContext);
    const { showAlert } = useContext(AlertContext);

    const resetPost = (): void => {
        setDescription("");
        setFiles([]);
        onClose();
    }

    const handlePostSubmit = async (e: React.FormEvent): Promise<void> => {
        e.preventDefault();

        try {
            let mediaId: string | null = null;
            if (files.length > 0) {
                const FileData = new FormData();
                FileData.append("file", files[0]);

                const uploadedFile: any = await execute({
                    url: import.meta.env.VITE_API_UPLOAD_FILE_ENDPOINT,
                    method: "POST",
                    body: FileData,
                    useToken: true
                });
                mediaId = uploadedFile.media_id;
            }

            let content: string = description.trim();

            await execute({
                url: import.meta.env.VITE_API_CREATE_POST_ENDPOINT,
                method: "POST",
                body: { content, media_id: mediaId },
                useToken: true
            });

            resetPost();
            showAlert(true, "Post created successfully");
            refreshNotifications();
            onChanges();
        } catch(err: any) {
            console.error("Error creating post:", err.message);
            showAlert(false, "Failed to create Post. Try Again!");
        }
    }

    return (
        <Dialog.Root 
            open={isOpen} 
            onOpenChange={(e) => !e.open && resetPost()}
            placement="center"
        >   
            <Dialog.Positioner w="100vw" h="100vh">
                <Dialog.Content w="100%" minH={{ base: "100vh", md: "auto" }} bg="variantSecondary" p={2}>
                    <Dialog.Header>
                        <HStack w="100%" h="50px" justifyContent="space-between">
                            <Dialog.Title>
                                <Text className="title-styles">Create a New Post</Text>
                            </Dialog.Title>
                            <Icon label="Cancel Post Creation" onClick={resetPost}>
                                <LuTrash2 />
                            </Icon>
                        </HStack>
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
                        />
                    </Dialog.Body>

                    <Dialog.Footer>
                        <CustomButton
                            label="Publish Post"
                            disabled={isLoading || description.trim() === "" }
                            onClick={handlePostSubmit}
                        >
                            <LuCheck /> Publish
                        </CustomButton>

                        <CustomButton 
                            label="Cancel Changes"
                            onClick={resetPost}
                            isNeutral={true}
                        >
                            Cancel
                        </CustomButton>
                    </Dialog.Footer>
                </Dialog.Content>
            </Dialog.Positioner>
        </Dialog.Root>
    );
}
