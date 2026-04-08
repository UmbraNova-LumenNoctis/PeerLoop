import { useState, JSX } from "react";
import {
	Menu,
	Flex,
	HStack,
	Input,
	InputGroup,
	Spinner,
	Text,
	VStack,
	Box,
	IconButton,
	InputProps
} from "@chakra-ui/react";
import { PostData } from "@/types/Post";
import { UserData } from "@/types/User";
import { LuSearch } from "react-icons/lu";
import { useNavigate } from "react-router-dom";
import { timeFormat } from "@/utils/PostUtils";
import { User } from "@/components/User";
import useApi from "@/hooks/useAPI";

export const SearchBar = (
	{ onChanges, ...props }
	: { onChanges?: () => void } & InputProps
): JSX.Element => {
	const [query, setQuery] = useState<string>("");
	const [users, setUsers] = useState<UserData[]>([]);
	const [posts, setPosts] = useState<PostData[]>([]);
	const [open, setOpen] = useState<boolean>(false);
	const { isLoading, error, execute } = useApi();
	const navigate = useNavigate();

	const hasResults = users.length > 0 || posts.length > 0;

	const submitSearchQuery = async (
		e: React.MouseEvent<HTMLButtonElement>
	): Promise<void> => {
		e.preventDefault();

		setOpen(true);

		try {
			const [usersResponse, postsResponse] = await Promise.all([
				execute({
					url: import.meta.env.VITE_API_SEARCH_USER,
					params: { q: query, limit: 5 },
					useToken: true
				}),
				execute({
					url: import.meta.env.VITE_API_SEARCH_POST,
					params: { q: query, limit: 5, offset: 0 },
					useToken: true
				})
			]);

			const usersList: UserData[] = usersResponse.items
				.map((user: any) => {
					return ({
						id: user.id,
						pseudo: user.pseudo,
						avatar: user.avatar_url,
						email: user.email
					});
				});

			const postsList: PostData[] = postsResponse.items
				.map((post: any) => {
					return ({
						id: post.id,
						image: post.media_url,
						content: post.content,
						createdAt: post.created_at,
						authorId: post.user_id,
						authorPseudonym: post.author_pseudo,
						authorAvatar: post.author_avatar_url,
						comments: post.comment_count,
						likes: post.like_count,
						likedByMe: post.liked_by_me
					});
				});

			setUsers(usersList);
			setPosts(postsList);
		} catch(err: any) {
			console.error("Failed to search query:", err.message);
			setOpen(false);
		}
	}

	return (
		<Menu.Root 
			open={open}
  			onOpenChange={(e) => setOpen(e.open)}
		>
			<Flex 
				w="100%" justifyContent="center" alignItems="center"
				maxW={{ base: "100%", md: "250px", lg: "300px" }}
			>
				<InputGroup w="90%" endElement={
					<Menu.Trigger asChild>
						<IconButton 
							borderRadius="full"
							color="secondary" bg="primary"
							onClick={submitSearchQuery}
							disabled={!query.trim().length || isLoading}
							size="2xs" w="50px"
						>
							<LuSearch />
						</IconButton>
					</Menu.Trigger>
				}>
					<Input
						value={query}
						className="title-styles"
						bg="secondary" maxLength={250}
						placeholder="Search users and posts"
						borderRadius="full" borderColor="text"
						_placeholder={{ fontFamily: "Poppins", color: "text" }}
						_focus={{ focusRing: "none", borderColor: "primary" }}
						_hover={{ borderColor: "primary" }}
						onChange={(e) => setQuery(e.target.value)}
						{...props}
					/>
				</InputGroup>

				<Menu.Positioner mt={5}>
					<Menu.Content
						w={{ base: "calc(100vw - 1rem)", md: "400px", lg: "600px" }}
						bg="variantSecondary"
						border="1px solid"
						borderColor="rgba(229,231,235,0.15)"
						borderRadius="2xl"
						boxShadow="0 20px 45px rgba(0,0,0,0.28)"
						maxH="70vh"
						overflowY="auto"
						p={3}
					>
						{isLoading && (
							<Flex align="center" justify="center" py={6} gap={2}>
								<Spinner size="sm" color="primary" />
								<Text className="title-styles" fontSize="sm" fontWeight="800">
									Searching...
								</Text>
							</Flex>
						)}

						{!isLoading && error && (
							<Text className="title-styles" color="error" fontSize="sm" px={2} py={2}>
								{error}
							</Text>
						)}

						{!isLoading && !error && (
							hasResults 
							? (
								<VStack align="stretch" gap={3}>
									{users.length > 0 && (
										<VStack align="flex-start" justifyContent="flex-start">
											<Text className="title-styles" fontSize="sm" fontWeight="900" px={2} mb={1}>
												Users
											</Text>

											{users.map((user) => (
												<Menu.Item value={`user-${user.id}`} key={user.id} asChild>
													<HStack onClick={() => {
														navigate(`/profile/${user.id}`);
														onChanges();
													}}>
														<User name={user.pseudo} picture={user.avatar} />

														<Box>
															<Text className="text-styles" fontSize="sm" fontWeight="900">
																{user.pseudo}
															</Text>

															<Text className="text-styles" fontSize="xs">
																{user.email}
															</Text>
														</Box>
													</HStack>
												</Menu.Item>
											))}
										</VStack>
									)}

									{posts.length > 0 && (
										<Box w="100%">
											<Text className="title-styles" fontSize="sm" fontWeight="900" px={2} mb={1}>
												Posts
											</Text>

											{posts.map((post) => (
												<Menu.Item value={`post-${post.id}`} key={post.id} w="100%" asChild>
													<HStack 
														px={2} py={2}
														align="flex-start" 
														onClick={() => {
															navigate(`/profile/${post.authorId}`);
															onChanges();
														}}
													>
														<User name={post.authorPseudonym} picture={post.authorAvatar} />

														<Box flex={1}>
															<Flex justify="space-between">
																<Text className="text-styles" fontWeight="900">
																	{post.authorPseudonym}
																</Text>

																<Text className="text-styles" fontSize="10px">
																	{timeFormat(post.createdAt)}
																</Text>
															</Flex>

															<Text className="text-styles" fontSize="xs" lineClamp={2}>
																{post.content}
															</Text>

															<Text className="text-styles" fontSize="10px">
																{post.likes} likes • {post.comments} comments
															</Text>
														</Box>
													</HStack>
												</Menu.Item>
											))}
										</Box>
									)}
								</VStack>
							) : (
								<Text className="title-styles" fontWeight="bold" fontSize="sm" px={2} py={4}>
									No results found.
								</Text>
							)
						)}
					</Menu.Content>
				</Menu.Positioner>
			</Flex>
		</Menu.Root>
	);
};