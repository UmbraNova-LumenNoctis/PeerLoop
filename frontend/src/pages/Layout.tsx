import { JSX, useContext, useEffect, useRef } from 'react';
import { Outlet, useLocation } from "react-router-dom";
import { Header } from "@/components/Header";
import { Box, Grid, GridItem } from '@chakra-ui/react';
import { FullScreen } from '@/components/FullScreen';
import { fetchPresenceWsUrl } from "@/services/chatService";
import Friends from "@/pages/Friends";
import { AuthContext } from "@/context/authContext";

function Layout(): JSX.Element {
	const location = useLocation();
	const isFullScreen = location.pathname.startsWith("/chat") 
		|| location.pathname.startsWith("/profile");
	const presenceSocketRef = useRef<WebSocket | null>(null);
	const mainContentRef = useRef<HTMLDivElement | null>(null);
	const { isLoggedIn, isLoading, logout } = useContext(AuthContext);

	useEffect(() => {
		mainContentRef.current?.focus();
	}, [location.pathname]);

	useEffect(() => {
		if (isLoading || !isLoggedIn) {
			if (presenceSocketRef.current) {
				presenceSocketRef.current.close();
				presenceSocketRef.current = null;
			}
			return;
		}

		let cancelled = false;
		let reconnectTimeout: number | null = null;

		const connectPresence = async () => {
			if (cancelled) {
				return;
			}

			try {
				const socketConfig = await fetchPresenceWsUrl();
				if (cancelled) {
					return;
				}

				const socket = new WebSocket(socketConfig.ws_url);
				presenceSocketRef.current = socket;

				socket.onclose = (event) => {
					if (cancelled) {
						return;
					}
					if (event.code === 4401) {
						logout();
						return;
					}
					reconnectTimeout = window.setTimeout(() => {
						void connectPresence();
					}, 2000);
				};
			} catch {
				if (cancelled) {
					return;
				}
				reconnectTimeout = window.setTimeout(() => {
					void connectPresence();
				}, 3000);
			}
		};

		void connectPresence();

		const heartbeatInterval = window.setInterval(() => {
			const socket = presenceSocketRef.current;
			if (socket && socket.readyState === WebSocket.OPEN) {
				socket.send(JSON.stringify({ type: "ping" }));
			}
		}, 25000);

		return () => {
			cancelled = true;
			window.clearInterval(heartbeatInterval);
			if (reconnectTimeout) {
				window.clearTimeout(reconnectTimeout);
			}
			if (presenceSocketRef.current) {
				presenceSocketRef.current.close();
				presenceSocketRef.current = null;
			}
		};
	}, [isLoggedIn, isLoading, logout]);

	return (
		<FullScreen bg="secondary">
			<Grid w="100vw" h="100vh" templateRows="80px 1fr">
				{/* Header */}
				<GridItem rowSpan={1} as="header" aria-label="Navigation principale">
					<Header />
				</GridItem>

				{/* Body */}
				<GridItem rowSpan={1} display="flex" overflow="hidden">
					{/* Sidebar */}
					<Box
						as="aside"
						w={{ base: 0, md: isFullScreen ? 0 : "50%" }}
						display={{ base: "none", md: "flex" }}
						position="sticky" top="80px"
						h="calc(100vh - 80px)"
						overflowY="auto"
					>
						<Friends />
					</Box>

					{/* Main content */}
					<Box
						as="main"
						id="main-content"
						ref={mainContentRef}
						tabIndex={-1}
						role="main"
						aria-label="Contenu principal"
						px={{ base: 2, md: isFullScreen ? 2 : 4 }}
						h="calc(100vh - 80px)" flex="1"
						overflowY="auto"
					>
						<Outlet />
					</Box>
				</GridItem>
			</Grid>
		</FullScreen>
	);
}

export default Layout;
