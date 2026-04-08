import { useState, useContext, JSX } from 'react';
import {
    Flex,
    HStack,
    Image as ChakraImage,
    Stack,
    Text,
    Box
} from "@chakra-ui/react";
import { LuHeart, LuMessageSquare } from "react-icons/lu";
import { NotificationContext } from "@/context/notificationContext";
import { UserContext } from "@/context/userContext";
import { timeFormat } from "@/utils/PostUtils";
import { InteractionButton } from "@/components/InteractionButton";
import { PostComments } from '@/components/CommentSection';
import { PostMenu } from "@/components/Menu";
import { User } from '@/components/User';
import { PostData } from '@/types/Post';
import useApi from "@/hooks/useAPI";

export const PostCard = ({ post }: { post: PostData }): JSX.Element => {
    const [isLiked, setIsLiked] = useState<boolean>(post.likedByMe);
    const [isCommenting, setIsCommenting] = useState<boolean>(false);
    const [showDescription, setShowDescription] = useState<boolean>(false);
    const [commentsCount, setCommentsCount] = useState<number>(post.comments);
    const { refreshNotifications } = useContext(NotificationContext);
    const { user } = useContext(UserContext);
    const { execute } = useApi<PostData>();

    const handleLikeToggle = async (): Promise<void> => {
        try {
            setIsLiked(!isLiked);

            isLiked
            ? await execute({
                url: import.meta.env.VITE_API_DELETE_LIKE_POST_ENDPOINT.replace("{post_id}", post.id),
                method: "DELETE",
                useToken: true
            })
            : await execute({
                url: import.meta.env.VITE_API_LIKE_POST_ENDPOINT.replace("{post_id}", post.id),
                method: "POST",
                useToken: true
            });

            refreshNotifications();
        } catch(err: any) {
            console.error("Failed to toggle like:", err.message);
            setIsLiked(!isLiked);
        }
    }

    return (
        post
        ? (
            <Flex 
                as="article"
                alignItems="center"
                justifyContent="center"
                flexDirection="column"
                minH="250px" w="100%"
                bg="variantSecondary" borderRadius="md"
                gap={3} py={3}
            >
                {/* About the author */}
                <HStack justifyContent="space-between" w="100%" px={3}>
                    <HStack gap="3">
                        <User name={post.authorPseudonym} picture={post.authorAvatar} userId={post.authorId} />
                        <Stack gap="0">
                            <Text className="title-styles" fontSize="sm" fontWeight="medium">
                                {(post.authorPseudonym?.length ?? 0) > 20 ? post.authorPseudonym.substring(0, 20) + "..." : (post.authorPseudonym || "")}
                            </Text>
                            <Text className="text-styles" fontSize="xs">{timeFormat(post.createdAt)}</Text>
                        </Stack>
                    </HStack>

					<PostMenu postId={post.id} isAuthor={user?.id === post.authorId} />
                </HStack>

                {/* Post content */}
                <Stack w="100%" gap={3}>
                    <Text 
                        className="text-styles" px={3}
                        onClick={() => (post.content?.length ?? 0) > 100 && setShowDescription(!showDescription)}
                        cursor="pointer"
                    >
                        {(post.content?.length ?? 0) > 100 && !showDescription ? post.content.substring(0, 100) + "..." : (post.content || "")}
                    </Text>
                    {
                        post.image 
                        && (
                            post.image.endsWith('.mp4')
                            ? <video src={post.image} width="100%" height="auto" controls />
                            : <ChakraImage src={post.image} alt={post.id} w="100%" h="auto" />
                        )
                    }
                    <HStack 
                        className="text-styles"
                        justifyContent="space-between" 
                        px={3}
                    >
                        <Text fontSize="xs" fontWeight="medium">{post.likes + (isLiked ? (post.likedByMe ? 0 : 1) : (post.likedByMe ? -1 : 0))} Likes</Text>
                        <Text fontSize="xs" fontWeight="medium">{commentsCount} Comments</Text>
                    </HStack>
                </Stack>

                {/* Post interactions */}
                <HStack 
                    w="100%" gap={0} pt={3}
                    justifyContent="space-evenly"
                    borderTop="1px solid" borderColor="text"
                >
                    <InteractionButton
                        label="Like Post" isActive={isLiked}
                        onClick={handleLikeToggle}
                    >
                        <LuHeart /> Like
                    </InteractionButton>

                    <InteractionButton
                        label="Comment on Post" isActive={isCommenting}
                        onClick={() => setIsCommenting(!isCommenting)}
                    >
                        <LuMessageSquare /> Comment
                    </InteractionButton>
                </HStack>

                <PostComments 
                    postId={post.id} 
                    isActive={isCommenting}
                    onChanges={(newValue) => setCommentsCount(newValue)}
                />
            </Flex>
        )
        : (
            <Flex
                as="article"
                alignItems="center"
                justifyContent="center"
                flexDirection="column"
                minH="250px" w="100%"
                bg="variantSecondary"
                borderRadius="md"
                gap={3} py={3}
                boxShadow="md"
                opacity={0.5}
            >
                <Stack w="100%" gap={3} px={3}>
                    <HStack h="50px" w="100%">
                        <Box minW="50px" minH="50px" bg="gray.300" borderRadius="full" />
                        <Stack gap="2" w="100%">
                            <Box h="12px" bg="gray.300" borderRadius="sm" w="40%" />
                            <Box h="12px" bg="gray.300" borderRadius="sm" w="30%" />
                        </Stack>
                    </HStack>
                    <Box h="12px" bg="gray.300" borderRadius="sm" w="60%" />
                    <Box h="12px" bg="gray.300" borderRadius="sm" w="80%" />
                    <Box h="150px" bg="gray.300" borderRadius="md" w="100%" />
                    <HStack justifyContent="space-between">
                        <Box h="24px" bg="gray.300" borderRadius="sm" w="50%" />
                        <Box h="24px" bg="gray.300" borderRadius="sm" w="50%" />
                    </HStack>
                </Stack>
            </Flex>
        )
    );
};
