import {
	HStack,
	VStack,
	Text,
	Badge,
	Icon,
	Spinner,
	Button,
	Stack,
	ButtonProps,
	Flex,
	Box
} from "@chakra-ui/react";
import { LuBellRing, LuFlag, LuCheck, LuTrash2, LuBookmark, LuRefreshCcw, LuBellOff } from "react-icons/lu";
import { useState, useEffect, JSX, useContext, useMemo } from "react";
import { NotificationContext } from "@/context/notificationContext";
import { AlertContext } from "@/context/alertContext";
import { UserContext } from "@/context/userContext";
import { timeFormat } from "@/utils/PostUtils";
import { User } from "@/components/User";
import useApi from "@/hooks/useAPI";

const Action = (
	{children, onClick, color, ...props}
	: { onClick: () => void, color: string } & ButtonProps
): JSX.Element => {

	return (
		<Button
			onClick={onClick} 
			borderRadius="full"
			bg={color} opacity={0.9}
			color={color === "primary" ? "secondary" : "text"}
			_disabled={{ opacity: 0.6 }}
			_hover={{ opacity: 1.0 }}
			{...props}
		>
			{children}
		</Button>
	);
}

interface NotificationData
{
	id: string;
	userId: string;
	userName?: string;
	userAvatar?: string;
	content: string;
	isUnread: boolean;
	type: string;
	category: "news" | "savings";
	createdAt: string;
}

interface NotificationApiRow
{
	id: string;
	user_id: string;
	source_id?: string;
	actor_id?: string;
	content: string;
	is_read: boolean;
	type: string;
	created_at: string;
}

const legacyActorFromSourceNotificationTypes = new Set<string>([
	"post_comment",
	"post_like",
	"post_comment_updated",
	"post_comment_deleted",
	"comment_deleted_by_post_owner",
]);

function Notification (): JSX.Element {
	const { execute } = useApi();
	const [notificationList, setNotificationList] = useState<NotificationData[]>([]);
	const [activeSession, setActiveSession] = useState<"news" | "savings">("savings");
	const [isRefreshing, setIsRefreshing] = useState<boolean>(true);
	const { setCounts } = useContext(NotificationContext);
	const { refreshNotifications } = useContext(NotificationContext);
	const { showAlert } = useContext(AlertContext);
	const { user } = useContext(UserContext);

	useEffect(() => {
		const cachedNotifications = loadFromCache();
		if (cachedNotifications) {
			setNotificationList(cachedNotifications);
			setIsRefreshing(false);
		}

		if (user?.id) {
			void loadNotificationList();
		}
	}, [user?.id]);

	useEffect(() => {
		if (!user?.id) return;

		const intervalId = setInterval(() => {
			void loadNotificationList();
			void refreshNotifications();
		}, 10000);

		return () => clearInterval(intervalId);
	}, [user?.id]);

	const saveToCache = (notifications: NotificationData[]) => {
		sessionStorage.setItem("notifications", JSON.stringify(notifications));
	};

	const loadFromCache = (): NotificationData[] | null => {
		const data = sessionStorage.getItem("notifications");
		return data ? JSON.parse(data) : null;
	};

	const refreshNotificationList = async () => {
		setNotificationList([]);
		await loadNotificationList(true);
	}

	const newsNotifications = useMemo(() => {
		return notificationList
			.filter(notification => notification.category === "news")
			.filter(notification => !notification.isUnread);
	}, [notificationList]);

	const savingsNotifications = useMemo(() => {
		return notificationList.filter(
			notification => notification.category === "savings"
		);
	}, [notificationList]);

	const displayedNotifications = activeSession === "news" ? newsNotifications : savingsNotifications;

	const loadNotificationList = async (fullRefresh=false) => {
		if (fullRefresh) setIsRefreshing(true);
		if (!user?.id) {
			setIsRefreshing(false);
			return;
		}

		try {
			const data: NotificationApiRow[] = await execute({
				url: import.meta.env.VITE_API_GET_NOTIFICATION_LIST,
				useToken: true
			});

			const newNotifications: NotificationData[] = await Promise.all(
				data.map(async (notification: NotificationApiRow) => {
					const actorId =
						notification.actor_id
						|| (
							legacyActorFromSourceNotificationTypes.has(notification.type)
							&& notification.source_id
								? notification.source_id
								: null
						)
						|| (notification.user_id === user.id ? user.id : null);

					const actorNameFallback = actorId === user.id
						? (user.pseudo || "me")
						: (actorId ? `user_${actorId.slice(0, 8)}` : "Someone");

					const author = 
						actorId && actorId !== user.id
						? await getUserInfo(actorId)
						: user

					return {
						id: notification.id,
						userId: actorId || user.id,
						userName: author?.pseudo || actorNameFallback,
						userAvatar: author?.avatar || undefined,
						content: notification.content || "",
						type: notification.type,
						createdAt: notification.created_at,
						category: !notification.is_read ? "savings" : "news",
						isUnread: !notification.is_read
					};
				})
			);

			setNotificationList(newNotifications);
			saveToCache(newNotifications);
			void refreshNotifications();
		} catch(err: any) {
			console.log("Failed to retrieve notifications:", err.message);
		} finally {
			setIsRefreshing(false);
		}
	}

	const getUserInfo = async (userId: string) => {
		try {
			const user = await execute({
				url: import.meta.env.VITE_API_GET_USER_BY_ID_ENDPOINT.replace("{user_id}", userId),
				useToken: true
			});

			return ({
				pseudo: user.pseudo,
				avatar: user.avatar_url
			})
		} catch(err: any) {
			console.log("Failed to retrieve user's data:", err.message);
			return null;
		}
	}

	const readAllNotification = async () => {
		try {
			await execute({
				url: import.meta.env.VITE_API_MARK_NOTIFICATION_ALL_READ,
				method: "PATCH",
				useToken: true
			});

			setCounts(prev => ({...prev, Notification: 0}));
			showAlert(true, "All notifications marked as read.");
			refreshNotificationList();
		} catch(err: any) {
			console.log("Failed to mark all notifications as read:", err.message);
			showAlert(false, "Failed to mark all notifications as read.");
		}
	}

	const readNotification = async (notificationId: string) => {
		try {
			await execute({
				url: import.meta.env.VITE_API_READ_NOTIFICATION_ENDPOINT.replace("{notification_id}", notificationId),
				method: "PATCH",
				useToken: true
			});

			setCounts(prev => ({...prev, Notification: prev.Notification - 1}));
			showAlert(true, "Notification marked as read.");
			refreshNotificationList();
		} catch(err: any) {
			console.log("Failed to mark notification as read:", err.message);
			showAlert(false, "Failed to mark notification as read.");
		}
	}

	const unreadNotification = async (notificationId: string) => {
		try {
			await execute({
				url: import.meta.env.VITE_API_UNREAD_NOTIFICATION_ENDPOINT.replace("{notification_id}", notificationId),
				method: "PATCH",
				useToken: true
			});

			setCounts(prev => ({...prev, Notification: prev.Notification + 1}));
			showAlert(true, "Notification marked as unread.");
			refreshNotificationList();
		} catch(err: any) {
			console.log("Failed to mark notification as unread:", err.message);
			showAlert(false, "Failed to mark notification as unread.");
		}
	}

	const deleteNotification = async (notificationId: string) => {
		try {
			await execute({
				url: import.meta.env.VITE_API_DELETE_NOTIFICATION_ENDPOINT.replace("{notification_id}", notificationId),
				method: "DELETE",
				useToken: true
			});

			showAlert(true, "Notification deleted successfully!");
			refreshNotificationList();
		} catch(err: any) {
			console.log("Failed to mark notification as unread:", err.message);
			showAlert(false, "Failed to mark notification as unread.");
		}
	}

	return (
		<VStack 
			justifyContent="flex-end"
            alignItems={{ base: "center", md: "flex-start" }}
			px={{ base: 4, md: 8 }} 
			py={6} w="100%"
		>
			<VStack w="100%" maxW="500px" gap={5}>
				<HStack 
					justifyContent="space-between" 
					alignItems="flex-start"
					mb={4} w="100%"
				>
					<Stack gap={1}>
						<HStack gap={2}>
							<Icon color="primary" boxSize={5}>
								<LuBellRing />
							</Icon>
							<Text className="title-styles" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="900">
								Notifications
							</Text>
							<Badge borderRadius="full" bg="rgba(112,205,75,0.18)" color="primary" px={3} py={1}>
								{newsNotifications.length + savingsNotifications.length}
							</Badge>
						</HStack>
						<Text className="text-styles" color="text" fontWeight="700">
							See and manage your notifications.
						</Text>
					</Stack>
		
					<HStack justify="flex-end" wrap="wrap">
						<Action onClick={() => refreshNotificationList()} color="#ffffff14">
							<LuRefreshCcw />
						</Action>

						<Action 
							onClick={readAllNotification} 
							disabled={!notificationList.length || !savingsNotifications.length} 
							color="primary"
						>
							<LuFlag />
						</Action>
					</HStack>
				</HStack>

				<HStack bg="variantSecondary" borderRadius="full" gap={5} p={2}>
					<Button
						className="title-styles"
						size="md" borderRadius="full" color="white"
						bg={activeSession === "savings" ? "primary" : "variantSecondary"}
						onClick={() => setActiveSession("savings")}
					>
						News 
						<Box bg="variantSecondary" color="white" borderRadius="full" px={2}>
							{savingsNotifications.length}
						</Box>
					</Button>

					<Button
						className="title-styles"
						size="md" borderRadius="full" color="white"
						bg={activeSession === "news" ? "primary" : "variantSecondary"}
						onClick={() => setActiveSession("news")}
					>
						History 
						<Box bg="variantSecondary" color="white" borderRadius="full" px={2}>
							{newsNotifications.length}
						</Box>
					</Button>
				</HStack>

				{
					isRefreshing
					? (
						<Flex alignItems="center" justifyContent="center" w="100%" minH="150px">
							<Spinner color="primary" size="xl" />
						</Flex>
					) : (
						!displayedNotifications.length ? (
							<Box 
								display="flex"
								alignItems="center"
								justifyContent="center"
								w="100%" minH="250px"
								bgColor="variantSecondary" 
								borderRadius="xl" 
								p={8}
							>
								<VStack gap={5}>
									<Icon boxSize={50} color="text">
										<LuBellOff />
									</Icon>
									
									<Text className="title-styles" fontSize="lg" fontWeight="bold">
										No notifications
									</Text>
									
									<Text 
										className="text-styles" 
										textAlign="center"  
										fontWeight="medium" 
										fontSize="md"
										color="error"
									>
										You're all caught up!
										{
											activeSession !== "news" 
											? " " + "New notifications will appear here."
											: " " + "Not notification received yet."
										}
									</Text>
								</VStack>
							</Box>
						) : displayedNotifications.map(notification => {
							return (
								<HStack 
									w="100%"
									borderRadius="xl"
									bg="variantSecondary"
									key={notification.id} 
									align="center" justify="space-between"
									gap={5} py={3} px={4}
								>
									<HStack align="center" gap={3}>
										<User name={notification.userName} picture={notification.userAvatar} />

										<VStack align="start" gap={2} flex={1}>
											<HStack gap={2}>
												<Text className="title-styles" fontWeight="semibold">
													{notification.userName === user.pseudo ? "me" : notification.userName}
												</Text>
													
												{
													notification.isUnread && (
														<Badge colorPalette="blue" variant="subtle">
															New
														</Badge>
													)
												}
											</HStack>

											<Text className="text-styles" fontSize="md">
												{notification.content}
											</Text>

											<Text fontSize="sm" color="gray.400">
												{timeFormat(notification.createdAt)}
											</Text>
										</VStack>
									</HStack>

									<HStack 
										justify="flex-end" 
										wrap="wrap"
										gap={2} minW="30%"
									>
										{
											notification.category === "savings" && (
												<Action onClick={() => readNotification(notification.id)} color="primary">
													<LuCheck />
												</Action>
											)
										}

										{
											notification.category === "news" && (
												<Action onClick={() => unreadNotification(notification.id)} color="#ffffff14">
													<LuBookmark />
												</Action>
											)
										}

										<Action onClick={() => deleteNotification(notification.id)} color="danger">
											<LuTrash2 />
										</Action>
									</HStack>
								</HStack>
							);
						})
					)
				}
			</VStack>
		</VStack>
	)
}

export default Notification;
