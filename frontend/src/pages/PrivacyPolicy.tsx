import { JSX } from "react";
import { Box, Button, Container, Heading, Link, List, Stack, Text } from "@chakra-ui/react";
import { Link as RouterLink, useNavigate } from "react-router-dom";

function PrivacyPolicy(): JSX.Element {
  const navigate = useNavigate();

  return (
    <Box minH="100vh" bg="secondary" py={{ base: 8, md: 12 }} px={4}>
        <Button
        alignSelf="flex-start"
        m={4}
        bg="transparent"
        border="1px solid rgba(255,255,255,0.24)"
        color="text"
        _hover={{ bg: "rgba(255,255,255,0.08)", borderColor: "primary" }}
        onClick={() => navigate(-1)}
        aria-label="Retour à la page précédente"
        >
        ← Retour
        </Button>
        <Container maxW="3xl">
            <Stack gap={6}>

            <Stack gap={2}>
                <Heading className="title-styles" size="3xl">Privacy Policy</Heading>
                <Text className="text-styles" color="variantText">Last updated: March 12, 2026</Text>
            </Stack>

            <Text className="text-styles" lineHeight="1.7">
                This Privacy Policy explains how PeerLoop collects, uses, and protects personal data
                when you use the platform.
            </Text>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">1. Data we process</Heading>
                <List.Root className="text-styles" ps={5} lineHeight="1.7">
                <List.Item>Account data (email, username, authentication metadata).</List.Item>
                <List.Item>Profile data and uploaded files/media.</List.Item>
                <List.Item>Social interactions (friendships, posts, comments, likes, notifications).</List.Item>
                <List.Item>Chat content and realtime presence signals.</List.Item>
                <List.Item>Technical and security logs necessary to operate and protect the service.</List.Item>
                </List.Root>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">2. Why we process data</Heading>
                <List.Root className="text-styles" ps={5} lineHeight="1.7">
                <List.Item>To create and manage user accounts and authentication sessions.</List.Item>
                <List.Item>To provide core social features (profiles, posts, chat, notifications).</List.Item>
                <List.Item>To secure the platform (WAF, monitoring, abuse prevention).</List.Item>
                <List.Item>To maintain service reliability and performance.</List.Item>
                </List.Root>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">3. Third-party services</Heading>
                <Text className="text-styles" lineHeight="1.7">
                PeerLoop uses integrated providers including Supabase (data/auth), ImageKit (media),
                Google OAuth (sign-in), and Gemini (LLM features). These services process data according
                to their own privacy terms.
                </Text>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">4. Security measures</Heading>
                <Text className="text-styles" lineHeight="1.7">
                We use HTTPS, segmented services, Vault-managed secrets, and monitoring controls to reduce risk.
                No system is perfectly secure, but we continuously improve protection measures.
                </Text>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">5. Data retention</Heading>
                <Text className="text-styles" lineHeight="1.7">
                Data is retained only as long as needed for service operation, legal obligations,
                and security investigations.
                </Text>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">6. Your choices</Heading>
                <Text className="text-styles" lineHeight="1.7">
                You can review and update profile information in your account settings.
                If applicable, you may request correction or deletion of your account data.
                </Text>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">7. Related terms</Heading>
                <Text className="text-styles" lineHeight="1.7">
                Your use of PeerLoop is governed by our Terms of Use.
                <Link asChild color="primary" fontWeight="700" _hover={{ textDecoration: "underline" }}>
                    <RouterLink to="/terms-of-use"> View Terms of Use</RouterLink>
                </Link>
                </Text>
            </Stack>
            </Stack>
        </Container>
    </Box>
  );
}

export default PrivacyPolicy;
