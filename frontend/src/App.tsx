import { system } from "./theme";
import { ChakraProvider } from "@chakra-ui/react";
import { Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "@/pages/ProtectedRoute";
import { NotificationProvider } from "@/context/notificationContext";
import { AlertProvider } from "@/context/alertContext"
import { UserProvider } from "@/context/userContext";
import { AuthProvider } from "@/context/authContext";
import { Toaster } from "@/components/ui/toaster";
import Notification from '@/pages/Notification';
import Invitations from "@/pages/Invitations";
import Register from "@/pages/Register";
import TermsOfUse from "@/pages/TermsOfUse";
import PrivacyPolicy from "@/pages/PrivacyPolicy";
import Layout from "@/pages/Layout";
import Login from "@/pages/Login";
import Chat from '@/pages/Chat';
import Home from "./pages/Home";
import Profile from "./pages/Profile";
import Friends from "./pages/Friends";

function App() {
	return (
		<ChakraProvider value={system}>
			<a href="#main-content" className="skip-link">Aller au contenu principal</a>
			<AlertProvider>
				<AuthProvider>
					<UserProvider>
						<NotificationProvider>
							<Routes>
								<Route path="/login" element={<Login />} />
								<Route path="/register" element={<Register />} />
								<Route path="/terms-of-use" element={<TermsOfUse />} />
								<Route path="/privacy-policy" element={<PrivacyPolicy />} />
								<Route 
									element={
										<ProtectedRoute>
											<Layout />
										</ProtectedRoute>
									}
								>
									<Route path="/" element={<Home />} />
									<Route path="/chat" element={<Chat />} />
									<Route path="/invitations" element={<Invitations />} />
									<Route path="/friends" element={<Friends />} />
									<Route path="/notification" element={<Notification />} />
									<Route path="/profile" element={<Profile />} />
									<Route path="/profile/:userId" element={<Profile />} />
								</Route>
							</Routes>
							<Toaster />
						</NotificationProvider>
					</UserProvider>
				</AuthProvider>
			</AlertProvider>
		</ChakraProvider>
	);
}

export default App;
