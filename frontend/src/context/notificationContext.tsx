import useApi from "@/hooks/useAPI";
import { createContext, useCallback, useRef, useState } from "react";

interface NotificationCounts
{
    Home: number;
    Message: number;
    Notification: number;
}

export const NotificationContext = createContext(null);

export const NotificationProvider = ({ children }) => {
    const { execute } = useApi();
    const isRefreshingRef = useRef<boolean>(false);
    const [counts, setCounts] = useState<NotificationCounts>({
        Home: 0,
        Message: 0,
        Notification: 0
    });

    const isAbortLikeError = (err: any): boolean => {
        const message = String(err?.message || "").toLowerCase();
        return (
            message.includes("aborted")
            || message.includes("canceled")
            || message.includes("cancelled")
        );
    };

    const refreshNotifications = useCallback(async () => {
        if (isRefreshingRef.current) {
            return;
        }
        isRefreshingRef.current = true;

        try {
            const [unreadNotificationsResult, unreadChatNotificationsResult] = await Promise.allSettled([
                execute({
                    url: import.meta.env.VITE_API_CHECKOUT_NOTIFICATIONS_ENDPOINT,
                    useToken: true
                }),
                execute({
                    url: import.meta.env.VITE_API_GET_CHAT_NOTIFICATIONS_ENDPOINT,
                    params: { limit: 20, offset: 0 },
                    useToken: true
                })
            ]);

            if (
                unreadNotificationsResult.status === "rejected"
                && !isAbortLikeError(unreadNotificationsResult.reason)
            ) {
                console.error("Error refreshing notification unread count:", unreadNotificationsResult.reason?.message || unreadNotificationsResult.reason);
            }

            if (
                unreadChatNotificationsResult.status === "rejected"
                && !isAbortLikeError(unreadChatNotificationsResult.reason)
            ) {
                console.error("Error refreshing chat unread count:", unreadChatNotificationsResult.reason?.message || unreadChatNotificationsResult.reason);
            }

            const nextNotificationCount = unreadNotificationsResult.status === "fulfilled"
                ? Number(unreadNotificationsResult.value?.unread_count || 0)
                : null;

            const chatList: any[] = unreadChatNotificationsResult.status === "fulfilled" && Array.isArray(unreadChatNotificationsResult.value)
                ? unreadChatNotificationsResult.value
                : [];
            const nextMessageCount = unreadChatNotificationsResult.status === "fulfilled"
                ? chatList.reduce((total: number, conversation: any) => {
                    const unreadCount = Number(conversation.unread_count || 0);
                    return total + (Number.isFinite(unreadCount) ? Math.max(0, unreadCount) : 0);
                }, 0)
                : null;

            setCounts((prev: NotificationCounts) => ({
                Home: prev.Home,
                Message: nextMessageCount ?? prev.Message,
                Notification: (nextNotificationCount !== null && Number.isFinite(nextNotificationCount))
                    ? Math.max(0, nextNotificationCount)
                    : prev.Notification
            }));
        } catch (err: any) {
            if (!isAbortLikeError(err)) {
                console.error("Error refreshing notifications:", err?.message || err);
            }
        } finally {
            isRefreshingRef.current = false;
        }
    }, [execute]);

    return (
        <NotificationContext.Provider value={{ counts, setCounts, refreshNotifications }}>
            {children}
        </NotificationContext.Provider>
    );
};
