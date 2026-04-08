import useApi from '@/hooks/useAPI';
import { PostData } from '@/types/Post';
import { User } from "@/components/User";
import { PostCard } from '@/components/PostCard';
import { PostBuilder } from '@/components/PostBuilder';
import { CustomButton } from '@/components/CustomButton';
import { InteractionButton } from "@/components/InteractionButton";
import { Box, Flex, HStack, Spinner, Stack } from "@chakra-ui/react";
import { JSX, useEffect, useContext, useState } from 'react';
import { UserContext } from '@/context/userContext';
import { cachePost } from "@/utils/postCache";
import { LuImagePlus, LuRefreshCw } from 'react-icons/lu';

function Home(): JSX.Element {
    const { isLoading, execute } = useApi();
    const [isUploading, setIsUploading] = useState<boolean>(false);
    const [posts, setPosts] = useState<PostData[]>([]);
    const { user } = useContext(UserContext);

    useEffect(() => {
        if (!user?.id) {
            return;
        }
        getCachedPosts();
        void loadFeed();
    }, [user?.id]);

    const getCachedPosts = () => {
        const raw = sessionStorage.getItem("post:cache:v1");

        if (raw) {
            const cachedObject = JSON.parse(raw);

            const cachedPosts: PostData[] = Object.values(cachedObject)
                .map((entry: any) => entry.data)
                .sort((a: PostData, b: PostData) =>
                    new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
                );
            setPosts(cachedPosts);
        }
    }

    const refreshFeed = async () => {
        setPosts([]);
        await loadFeed();
    }

    const loadFeed = async (): Promise<void> => {
        if (!user?.id) {
            return;
        }
        try {
            const feedPosts: any = await execute({
                url: import.meta.env.VITE_API_GET_FEED_ENDPOINT,
                useToken: true,
                body: {
                    user_id: user.id,
                    friend_only: false,
                    include_self: true,
                    sort_by: "popularity",
                    order: "desc",
                    limit: 50,
                    offset: 0
                }
            });

            const postsData: PostData[] = (Array.isArray(feedPosts) ? feedPosts : []).map((post: any) => {
                const newPostData: PostData = {
                    id: post.id,
                    image: post.media_url,
                    content: post.content,
                    createdAt: post.created_at,
                    authorId: post.user_id,
                    authorPseudonym: post.author_pseudo,
                    authorAvatar: post.author_avatar_url,
                    comments: post.comment_count || 0,
                    likes: post.like_count || 0,
                    likedByMe: post.liked_by_me || false
                };

                cachePost(newPostData);
                return (newPostData);
            });

            setPosts(postsData);
        } catch (err: any) {
            console.error("Failed to refresh feed:", err.message);
        }
    };

    if (!user) {
        return (
            <Flex
                flexDirection="column"
                justifyContent="center"
                alignItems="center"
                px={{ base: 4, md: 8 }}
                py={6}
                w="100%"
                minH="240px"
            >
                <Spinner color="primary" size="xl" />
            </Flex>
        );
    }

    return (
        <Flex
            flexDirection="column"
            justifyContent="flex-end"
            alignItems={{ base: "center", md: "flex-start" }}
            px={{ base: 4, md: 8 }} py={6}
            w="100%"
        >
            <Box w="100%" maxW="500px" gap={5}>
                <HStack 
                    w="100%"
                    bg="variantSecondary"
                    borderRadius="md"
                    gap={5} p={5}
                    mb={5}
                >
                    <User name={user.pseudo} picture={user.avatar} isOnline={true} />

                    <CustomButton 
                        flex={1} 
                        label="Create a new post"
                        onClick={() => setIsUploading(true)}
                    >
                        <LuImagePlus /> Create a new post
                    </CustomButton>
                </HStack>

                <Stack 
                    w="100%"
                    borderTop="1px solid" borderColor="text"
                    alignItems="center"
                    gap={5} py={5}
                > 
                    {
                        posts.map(post => {
                            return <PostCard key={post.id} post={post} />;
                        })
                    }
                    { 
                        isLoading
                        ? <Spinner color="primary" size="xl" /> 
                        : (<>
                            <InteractionButton 
                                label="Refresh feed"
                                bg="rgba(255,255,255,0.08)"
                                _hover={{ bg: "primary", color: "secondary" }}
                                onClick={refreshFeed}
                                borderRadius="full"
                            >
                                <LuRefreshCw /> See More
                            </InteractionButton>
                        </>)
                    }
                </Stack>

                <PostBuilder 
                    isOpen={isUploading} 
                    onClose={() => setIsUploading(false)} 
                    onChanges={refreshFeed}
                />
            </Box>
        </Flex>
    );
}

export default Home;
