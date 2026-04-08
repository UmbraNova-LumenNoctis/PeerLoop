import { JSX } from "react";
import { Box, Button, Container, Heading, Link, List, Stack, Text } from "@chakra-ui/react";
import { Link as RouterLink, useNavigate } from "react-router-dom";

function TermsOfUse(): JSX.Element {
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
                <Heading className="title-styles" size="3xl">Terms of Use</Heading>
                <Text className="text-styles" color="variantText">Last updated: March 12, 2026</Text>
            </Stack>

            <Text className="text-styles" lineHeight="1.7">
                Welcome to PeerLoop. By accessing or using the platform, you agree to these Terms of Use.
                If you do not agree, please do not use the service.
            </Text>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">1. Eligibility and account security</Heading>
                <List.Root className="text-styles" ps={5} lineHeight="1.7">
                <List.Item>You must provide accurate registration information.</List.Item>
                <List.Item>You are responsible for keeping your credentials and 2FA secrets confidential.</List.Item>
                <List.Item>You are responsible for all actions taken through your account.</List.Item>
                </List.Root>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">2. Acceptable use</Heading>
                <Text className="text-styles" lineHeight="1.7">
                You agree to use PeerLoop lawfully and respectfully. You must not attempt to abuse, disrupt,
                bypass security mechanisms, or access data that you are not authorized to access.
                </Text>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">3. User-generated content</Heading>
                <Text className="text-styles" lineHeight="1.7">
                You keep ownership of your content (posts, comments, messages, media), and grant PeerLoop
                a limited right to store, process, and display it in order to operate the service.
                </Text>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">4. Service availability</Heading>
                <Text className="text-styles" lineHeight="1.7">
                PeerLoop is provided on a best-effort basis. Features may evolve, be interrupted, or be
                temporarily unavailable for maintenance, security, or infrastructure reasons.
                </Text>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">5. Termination</Heading>
                <Text className="text-styles" lineHeight="1.7">
                We may suspend or terminate access in case of misuse, security risk, or violation of these terms.
                </Text>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">6. Privacy</Heading>
                <Text className="text-styles" lineHeight="1.7">
                Your use of PeerLoop is also governed by our Privacy Policy.
                <Link asChild color="primary" fontWeight="700" _hover={{ textDecoration: "underline" }}>
                    <RouterLink to="/privacy-policy"> View Privacy Policy</RouterLink>
                </Link>
                </Text>
            </Stack>

            <Stack gap={3}>
                <Heading className="title-styles" size="md">7. Contact</Heading>
                <Text className="text-styles" lineHeight="1.7">
                For questions about these terms, contact the project team through the repository communication channels.
                </Text>
            </Stack>

            <Text className="text-styles" color="variantText" fontSize="sm">
                These terms may be updated to reflect platform, legal, or security changes.
            </Text>
            </Stack>
        </Container>
    </Box>
  );
}

export default TermsOfUse;
