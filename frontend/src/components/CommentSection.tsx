import { JSX, useEffect, useContext, useState } from "react";
import {
	Box,
	HStack,
	Input,
	Spinner,
	Text,
	VStack,
} from "@chakra-ui/react";
import { LuSend } from "react-icons/lu";
import { CommentData } from "@/types/Post";
import { NotificationContext } from "@/context/notificationContext";
import { AlertContext } from "@/context/alertContext";
import { UserContext } from "@/context/userContext";
import { timeFormat } from "@/utils/PostUtils";
import { CommentMenu } from "@/components/Menu";
import { User } from "@/components/User";
import { Icon } from "@/components/Icon";
import useApi from "@/hooks/useAPI";

export const PostComments = (
	{ postId, isActive=false, onChanges }
	: { postId: string, isActive: boolean, onChanges: (value: number) => void })
: JSX.Element => {
	const { isLoading, execute } = useApi();
	const [newComment, setNewComment] = useState<string>("");
	const [comments, setComments] = useState<CommentData[]>([]);
	const { refreshNotifications } = useContext(NotificationContext);
	const { showAlert } = useContext(AlertContext);
	const { user } = useContext(UserContext);

	useEffect(() => {
		retrieveComments();
	}, [postId]);

	useEffect(() => {
		onChanges(comments.length);
	}, [comments]);

	const refreshComments = async () => await retrieveComments();

	const retrieveComments = async (): Promise<void> => {
		try {
			const data: any = await execute({
				url: import.meta.env.VITE_API_COMMENT_LIST_ENDPOINT.replace("{post_id}", postId),
				useToken: true
			});
			if (!data) return;

			const comments: CommentData[] = data.map((comment: any) => {
				const userComment: CommentData = {
					id: comment.id,
					content: comment.content,
					authorId: comment.user_id,
					authorAvatar: comment.author_avatar_url,
					authorPseudo: comment.author_pseudo,
					createdAt: comment.created_at
				}

				return (userComment);
			});

			setComments(comments);
		} catch(err: any) {
			console.error(`Failed to load comments for ${postId}:`, err.message);
		}
	};

	const submitComment = async () => {
        try {
            await execute({
                url: import.meta.env.VITE_API_COMMENT_LIST_ENDPOINT.replace("{post_id}", postId),
                method: "POST",
                body: { content: newComment.trim() },
                useToken: true
            });

            showAlert(true, "Comment sent successfully.");
			refreshNotifications();
			refreshComments();
        } catch(err: any) {
            console.error(`Failed to retrieve comments for ${postId}: `, err.message);
            showAlert(false, "Failed to send your comment. Try Again!");
        } finally {
            setNewComment("");
        }
    };

  	return (
		<VStack 
			w="100%"
            px={3} py={2} gap={5}
            borderTop="1px solid" borderColor="text"
			display={isActive ? "flex" : "none"}
			align="flex-start"
        >
			{/* Add comment */}
			<HStack
				border="1px solid"
				borderColor="text"
				borderRadius="full"
				_hover={{ borderColor: "primary" }}
				p={2} mt={2} w="100%"
			>
				<Input 
					value={newComment} 
					size="sm"
					border="none"
					className="text-styles"
					_focus={{ focusRing: "none" }}
					_placeholder={{ fontFamily: "Montserrat", color: "text" }}
					onChange={(e) => setNewComment(e.target.value)}
					placeholder="Write a comment..." 
					maxLength={100}
				/>

				<Icon 
					maxH="24px"
					label="Send my comment"
					onClick={submitComment}
					disabled={isLoading || newComment === ""}
				>
					<LuSend />
				</Icon>
			</HStack>

			{/* Comments */}
			{
				isLoading
				? (
					<Box w="100%" display="flex" justifyContent="center">
						<Spinner color="primary" size="sm" />
					</Box>
				) : comments.map((comment) => {
					return (
						<Box
							key={comment.id}
							borderRadius="xl"
							bg="secondary"
							p={3}
						>
							<HStack align="center" justify="space-between" gap={2} mb={2}>
								<HStack minW={0}>
									<User name={comment.authorPseudo} picture={comment.authorAvatar} />
									<Box>
										<Text className="title-styles" fontSize="xs" fontWeight="900">
											{comment.authorPseudo}
										</Text>
										<Text className="text-styles" fontSize="xs" color="rgba(229,231,235,0.72)">
											{timeFormat(comment.createdAt)}
										</Text>
									</Box>
								</HStack>

								<CommentMenu 
									comment={comment} 
									isAuthor={user?.id === comment.authorId}
									onChanges={refreshComments}
								/>
							</HStack>

							<Text className="text-styles" fontSize="sm" whiteSpace="pre-wrap">
								{comment.content}
							</Text>
						</Box>
					);
				})}
		</VStack>
  	);
};
