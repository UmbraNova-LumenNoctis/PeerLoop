import { createContext, useCallback, useMemo, useState, useEffect } from 'react';
import {
	AUTH_LOGOUT_EVENT,
	AUTH_TOKEN_UPDATED_EVENT,
	clearStoredToken,
	ensureAccessToken,
	getStoredToken,
	setStoredToken
} from "@/utils/authSession";

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
	const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
	const [isLoading, setIsLoading] = useState<boolean>(true);

	useEffect(() => {
		let cancelled = false;

		const initializeSession = async (): Promise<void> => {
			const token = await ensureAccessToken();
			if (cancelled) {
				return;
			}
			setIsLoggedIn(Boolean(token));
			setIsLoading(false);
		};

		const handleTokenUpdated = (): void => {
			if (cancelled) {
				return;
			}
			setIsLoggedIn(Boolean(getStoredToken()));
		};

		const handleLogout = (): void => {
			if (cancelled) {
				return;
			}
			setIsLoggedIn(false);
		};

		void initializeSession();
		window.addEventListener(AUTH_TOKEN_UPDATED_EVENT, handleTokenUpdated);
		window.addEventListener(AUTH_LOGOUT_EVENT, handleLogout);

		return () => {
			cancelled = true;
			window.removeEventListener(AUTH_TOKEN_UPDATED_EVENT, handleTokenUpdated);
			window.removeEventListener(AUTH_LOGOUT_EVENT, handleLogout);
		};
	}, []);

	const getToken = useCallback((): string | null => {
		return getStoredToken();
	}, []);

	const login = useCallback((accessToken: string) => {
		setStoredToken(accessToken);
		setIsLoggedIn(true);
	}, []);

	const logout = useCallback(() => {
		clearStoredToken();
		sessionStorage.clear();
		setIsLoggedIn(false);
	}, []);

	const contextValue = useMemo(
		() => ({ isLoggedIn, isLoading, login, logout, getToken }),
		[getToken, isLoading, isLoggedIn, login, logout],
	);

	return (
		<AuthContext.Provider value={contextValue}>
			{children}
		</AuthContext.Provider>
	);
};
