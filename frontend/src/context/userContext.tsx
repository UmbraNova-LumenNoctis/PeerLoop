import { createContext, useState, useEffect, useContext, useCallback, useRef } from "react";
import { AuthContext } from "@/context/authContext";
import { UserData } from "@/types/User";
import useApi from "@/hooks/useAPI";
import { AUTH_LOGOUT_EVENT, AUTH_TOKEN_UPDATED_EVENT, getStoredToken } from "@/utils/authSession";

const GET_ME_ENDPOINT = import.meta.env.VITE_API_GET_USER_ENDPOINT || "/api/user/me";

export const UserContext = createContext(null);

export const UserProvider = ({ children }) => {
    const { execute } = useApi();
    const { isLoggedIn, isLoading } = useContext(AuthContext);
    const isFetchingRef = useRef<boolean>(false);
    const [user, setUser] = useState<UserData | null>(() => {
        const user: string = localStorage.getItem("user");
        return (user ? JSON.parse(user) : null);
    });

    const retrieveUser = useCallback(async (): Promise<void> => {
        if (isFetchingRef.current) {
            return;
        }

        isFetchingRef.current = true;
        try {
            const userPayload: any = await execute({
                url: GET_ME_ENDPOINT,
                useToken: true
            });

            if (!userPayload || typeof userPayload !== "object") {
                return;
            }

            const resolvedId = userPayload.id || userPayload.user_id;
            const resolvedEmail = userPayload.email || null;
            const resolvedPseudo =
                userPayload.pseudo
                || (typeof resolvedEmail === "string" && resolvedEmail.includes("@")
                    ? resolvedEmail.split("@")[0]
                    : null);
            const resolvedAvatar = userPayload.avatar_url || userPayload.avatar || null;
            if (!resolvedId) {
                return;
            }

            setUser({
                id: resolvedId,
                pseudo: resolvedPseudo,
                avatar: resolvedAvatar,
                email: resolvedEmail
            });
        } catch(err: any) {
            const message = String(err?.message || "").toLowerCase();
            if (message.includes("canceled") || message.includes("aborted")) {
                return;
            }
            console.error("Failed to retrieve user data:", err?.message || err);
            setUser(null);
        } finally {
            isFetchingRef.current = false;
        }
    }, [execute]);

    useEffect(() => {
        if (isLoading) return;

        isLoggedIn ? void retrieveUser() : setUser(null);
    }, [isLoading, isLoggedIn, retrieveUser]);

    useEffect(() => {
        if (user)
            localStorage.setItem("user", JSON.stringify(user));
        else
            localStorage.removeItem("user");
    }, [user]);

    useEffect(() => {
        const onTokenUpdated = (): void => {
            if (getStoredToken())
                void retrieveUser();
        };

        const onLogout = (): void => {
            setUser(null);
        };

        window.addEventListener(AUTH_TOKEN_UPDATED_EVENT, onTokenUpdated);
        window.addEventListener(AUTH_LOGOUT_EVENT, onLogout);
        return () => {
            window.removeEventListener(AUTH_TOKEN_UPDATED_EVENT, onTokenUpdated);
            window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
        };
    }, [retrieveUser]);

    return (
        <UserContext.Provider value={{ user, setUser }}>
            {children}
        </UserContext.Provider>
    );
};
