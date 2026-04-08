import useApi from '@/hooks/useAPI';
import logo from '@/assets/lg_dark.png';
import googleLogo from '@/assets/google_lg.svg';
import { useState, useContext, useEffect, JSX } from 'react';
import { AuthContext } from '@/context/authContext';
import { LoginInput } from '@/components/LoginInput';
import { AlertContext } from "@/context/alertContext";
import { SubmitButton } from '@/components/SubmitButton';
import { useNavigate, Link as RouterLink, useLocation } from 'react-router-dom';
import { 
	Box, 
	Button,
	Dialog,
	Field,
	Flex, 
	Heading, 
	IconButton, 
	Image, 
	Input,
	Stack,
	Text,
	Separator,
	Link,
	Spinner
} from "@chakra-ui/react";
import { Formik, Form } from 'formik';
import * as Yup from 'yup';

interface LoginFormData
{
	email: string;
	password: string;
}

const LOGIN_ENDPOINT = import.meta.env.VITE_API_LOGIN_ENDPOINT || "/api/auth/login";
const LOGIN_2FA_VERIFY_ENDPOINT = import.meta.env.VITE_API_LOGIN_2FA_VERIFY_ENDPOINT || "/api/auth/login/2fa/verify";
const GOOGLE_AUTH_ENDPOINT = import.meta.env.VITE_API_GOOGLE_AUTH_ENDPOINT || "/api/auth/google";
const SESSION_EXCHANGE_ENDPOINT = import.meta.env.VITE_API_AUTH_SESSION_EXCHANGE_ENDPOINT || "/api/auth/session/exchange";

const LoginSchema: Yup.ObjectSchema<LoginFormData> = Yup.object().shape({
	email: Yup.string()
		.required('Email or Username is required'),
	password: Yup.string()
		.required('Password is Required')
});

function Login(): JSX.Element {
	const navigate = useNavigate();
	const location = useLocation();
	const [isGoogleAuth, setIsGoogleAuth] = useState<boolean>(false);
	const [pending2FaChallengeId, setPending2FaChallengeId] = useState<string | null>(null);
	const [login2FaCode, setLogin2FaCode] = useState<string>("");
	const [isLogin2FaSubmitting, setIsLogin2FaSubmitting] = useState<boolean>(false);
	const { isLoading, execute } = useApi();
	const { showAlert } = useContext(AlertContext);
	const { login } = useContext(AuthContext);

	useEffect(() => {
		let cancelled = false;

		const hashParams = new URLSearchParams((location.hash || "").replace(/^#/, ""));
		const queryParams = new URLSearchParams(location.search || "");
		const accessToken = hashParams.get("access_token") || queryParams.get("access_token");
		const refreshToken = hashParams.get("refresh_token") || queryParams.get("refresh_token");
		const oauthError = hashParams.get("error") || queryParams.get("error");

		const completeOauthLogin = async (): Promise<void> => {
			if (!accessToken) {
				return;
			}

			let resolvedAccessToken = accessToken;
			if (refreshToken) {
				try {
					const exchangedSession: any = await execute({
						url: SESSION_EXCHANGE_ENDPOINT,
						method: "POST",
						body: {
							access_token: accessToken,
							refresh_token: refreshToken,
						},
					});
					resolvedAccessToken = exchangedSession?.access_token || accessToken;
				} catch (exchangeError: any) {
					console.warn("Session exchange failed, continuing with access token only.", exchangeError?.message || exchangeError);
				}
			}

			if (cancelled) {
				return;
			}

			login(resolvedAccessToken);
			showAlert(true, "Google login successful.");
			navigate("/", { replace: true });
		};

		if (accessToken) {
			void completeOauthLogin();
			return;
		}

		if (oauthError) {
			showAlert(false, oauthError);
			navigate("/login", { replace: true });
		}

		return () => {
			cancelled = true;
		};
	}, [execute, location.hash, location.search, login, navigate, showAlert]);

	const close2FaDialog = (): void => {
		if (isLogin2FaSubmitting) {
			return;
		}
		setPending2FaChallengeId(null);
		setLogin2FaCode("");
	};

	const finalizeLoginWithToken = (accessToken: string): void => {
		login(accessToken);
		showAlert(true, "Login successfully! Welcome back");
		setTimeout(() => navigate('/'), 2000);
	};

	const handleLogin2FaVerify = async (): Promise<void> => {
		const challengeId = String(pending2FaChallengeId || "").trim();
		if (!challengeId) {
			showAlert(false, "2FA challenge expired. Please login again.");
			return;
		}

		const normalizedCode = login2FaCode.trim().replace(/\s+/g, "");
		if (!/^\d{6}$/.test(normalizedCode)) {
			showAlert(false, "Please enter a valid 6-digit code.");
			return;
		}

		setIsLogin2FaSubmitting(true);
		try {
			const verifyResponse: any = await execute({
				url: LOGIN_2FA_VERIFY_ENDPOINT,
				method: "POST",
				body: {
					challenge_id: challengeId,
					code: normalizedCode,
				} as any,
			});
			const accessToken = String(verifyResponse?.access_token || "");
			if (!accessToken) {
				throw new Error("JWT token is missing");
			}

			setPending2FaChallengeId(null);
			setLogin2FaCode("");
			finalizeLoginWithToken(accessToken);
		} catch (err: any) {
			const message = err?.message || "2FA verification failed.";
			showAlert(false, message);
		} finally {
			setIsLogin2FaSubmitting(false);
		}
	};

	const handleLoginSubmit = async (formData: LoginFormData) => {
		try {
			const response: any = await execute({
				url: LOGIN_ENDPOINT,
				method: "POST",
				body: formData
			});

			let accessToken: string = "";
			if (response?.["2fa_required"]) {
				const challengeId = String(response?.challenge_id || "").trim();
				if (!challengeId) {
					throw new Error("2FA challenge is missing. Please retry login.");
				}
				setPending2FaChallengeId(challengeId);
				setLogin2FaCode("");
				showAlert(true, "Enter your 2FA code to complete login.");
				return;
			} else {
				accessToken = String(response?.access_token || "");
			}

			if (!accessToken) throw new Error("JWT token is missing");

			finalizeLoginWithToken(accessToken);
		} catch (err: any) {
			const message = err?.message || "Login failed! Try again.";
			showAlert(false, message);
			console.error("Login failed:", message);
		}
	};

	const handleGoogleAuth = async (e: React.MouseEvent<HTMLButtonElement>) => {
		e.preventDefault();

		setIsGoogleAuth(true);

		try {
			const data: any = await execute({
				url: GOOGLE_AUTH_ENDPOINT
			});

			window.location.href = data.url;
		} catch(err: any) {
			console.error("Google Auth failed:", err.message);
		} finally {
			setIsGoogleAuth(false);
		}
	}

	return (
		<Flex minH="100vh" align="center" justify="center" bg="secondary" p={4}>
			<Box w="full" maxW="350px">
				<Formik<LoginFormData>
					initialValues={{ email: '', password: '' }}
					validationSchema={LoginSchema}
					onSubmit={handleLoginSubmit}
				>
					{({ errors, touched }) => (
						<Form>
							<Stack gap={6} align="center">
								<Image src={logo} alt="Image, logo PeerLoop" w="50%" mb={-4} />
								
								<Stack gap={1} textAlign="center">
									<Heading size="4xl" className="title-styles">Login</Heading>
									<Text fontSize="lg" fontWeight="bold" className="text-styles">Access your account</Text>
								</Stack>

								{/* Email or Username Field */}
								<LoginInput
                                    name="email" label="Username or Email"
                                    placeholder="Enter your username or email"
									isInvalid={!!errors.email && touched.email}
									aria-label="Enter your username or email"
									error={errors.email}
                                />

								{/* Password Field */}
								<LoginInput 
                                    name="password" type="password"
                                    label="Password" placeholder="Enter your password"
									isInvalid={!!errors.password && touched.password}
									aria-label="Enter your password"
									error={errors.password}
                                >
                                </LoginInput>

								{/* Submit Button */}
								<SubmitButton 
									name="Login" 
									loading={isLoading && !isGoogleAuth} 
									disabled={isLoading && !isGoogleAuth}
									aria-label="Login"
								/>

								{/* Button to trigger Google Auth */}
								<Flex align="center" w="full" gap={4}>
									<Separator flex={1} borderColor="text" />
									<IconButton variant="outline" borderRadius="full" w="50px" h="50px" bg="variantSecondary" borderColor="variantText"
										onClick={handleGoogleAuth} disabled={isGoogleAuth}
										aria-label="Authenticate via Google account"
									>
										{ !isGoogleAuth ? <Image src={googleLogo} alt="Image, Google Logo" w="24px" /> : <Spinner color="primary" size="sm" /> }
									</IconButton>
									<Separator flex={1} borderColor="text" />
								</Flex>

								<Text className="title-styles" fontSize="md" fontWeight="medium">
									Not a member yet ?{" "}
									<Link asChild color="primary"
										_hover={{ textDecoration: "underline" }}
										aria-label="Not a member yet ?"
									>
										<RouterLink to="/register">Register!</RouterLink>
									</Link>
								</Text>

								<Box
									w="full"
									p={3}
								>
									<Text className="title-styles" fontSize="sm" fontWeight="500" textAlign="center" lineHeight="1.6">
										By continuing, you agree to PeerLoop&apos;s{" "}
										<Link asChild color="primary" fontWeight="bold" _hover={{ textDecoration: "underline" }}>
											<RouterLink to="/terms-of-use">Terms of Use</RouterLink>
										</Link>{" "}
										and{" "}
										<Link asChild color="primary" fontWeight="bold" _hover={{ textDecoration: "underline" }}>
											<RouterLink to="/privacy-policy">Privacy Policy</RouterLink>
										</Link>
										.
									</Text>
								</Box>
							</Stack>
						</Form>
					)}
				</Formik>
			</Box>
			<Dialog.Root
				open={Boolean(pending2FaChallengeId)}
				onOpenChange={(event) => {
					if (!event.open) {
						close2FaDialog();
					}
				}}
				placement="center"
			>
				<Dialog.Positioner>
					<Dialog.Content
						bg="variantSecondary"
						border="1px solid rgba(255,255,255,0.16)"
						maxW="460px"
						w="calc(100vw - 24px)"
					>
						<Dialog.Header>
							<Dialog.Title className="title-styles">Two-Factor Authentication</Dialog.Title>
						</Dialog.Header>
						<Dialog.Body>
							<Stack gap={4}>
								<Box
									borderRadius="xl"
									border="1px solid rgba(112,205,75,0.35)"
									bg="rgba(112,205,75,0.08)"
									p={4}
								>
									<Text className="text-styles" fontWeight="700" lineHeight="1.5">
										Enter the 6-digit 2FA code from your authenticator app.
									</Text>
								</Box>
								<Field.Root>
									<Field.Label className="text-styles">Verification code</Field.Label>
									<Input
										value={login2FaCode}
										onChange={(event) => setLogin2FaCode(event.target.value.replace(/\s+/g, "").slice(0, 6))}
										placeholder="123456"
										inputMode="numeric"
										autoComplete="one-time-code"
										textAlign="center"
										letterSpacing="0.32em"
										fontWeight="800"
										fontSize="lg"
										className="text-styles"
										borderColor="rgba(255,255,255,0.2)"
										_focus={{ borderColor: "primary", focusRing: "none" }}
										disabled={isLogin2FaSubmitting}
									/>
								</Field.Root>
							</Stack>
						</Dialog.Body>
						<Dialog.Footer>
							<Button
								bg="primary"
								color="variantSecondary"
								_hover={{ opacity: 0.9 }}
								onClick={() => void handleLogin2FaVerify()}
								disabled={isLogin2FaSubmitting}
							>
								{isLogin2FaSubmitting ? "Verifying..." : "Verify"}
							</Button>
							<Button
								bg="transparent"
								border="1px solid rgba(255,255,255,0.24)"
								_hover={{ bg: "rgba(255,255,255,0.08)" }}
								onClick={close2FaDialog}
								disabled={isLogin2FaSubmitting}
							>
								Cancel
							</Button>
						</Dialog.Footer>
					</Dialog.Content>
				</Dialog.Positioner>
			</Dialog.Root>
		</Flex>
	);
}

export default Login;
