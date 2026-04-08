import { useCallback, useContext, useEffect, useMemo, useState, type JSX } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Avatar,
  Badge,
  Box,
  Button,
  Flex,
  HStack,
  Icon,
  Link,
  Spinner,
  Stack,
  Text,
  VStack,
} from "@chakra-ui/react";
import { LuRefreshCcw, LuUserPlus } from "react-icons/lu";
import { AlertContext } from "@/context/alertContext";
import {
  acceptFriendRequest,
  blockFriendship,
  deleteFriendship,
  friendshipInvitationsUpdatedEventName,
  getCachedFriendshipInvitations,
  syncFriendshipInvitationsCache,
} from "@/services/friendshipService";
import type { Friendship } from "@/types/friendship";

type InvitationTab = "incoming" | "outgoing";

const formatRelativeDate = (value: string | null): string => {
  if (!value) {
    return "Unknown date";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
};

const fallbackFriendName = (friendship: Friendship): string => {
  const pseudo = friendship.friend_pseudo?.trim();
  if (pseudo) {
    return pseudo;
  }
  const fallbackId = friendship.friend_user_id || friendship.user_b_id || friendship.user_a_id || "user";
  return `User_${String(fallbackId).slice(0, 8)}`;
};

function Invitations(): JSX.Element {
  const alertContext = useContext(AlertContext) as any;
  const initialCachedInvitations = useMemo(
    () => getCachedFriendshipInvitations({ allowStale: true }),
    [],
  );
  const [activeTab, setActiveTab] = useState<InvitationTab>("incoming");
  const [incomingRequests, setIncomingRequests] = useState<Friendship[]>(initialCachedInvitations?.incoming || []);
  const [outgoingRequests, setOutgoingRequests] = useState<Friendship[]>(initialCachedInvitations?.outgoing || []);
  const [isLoading, setIsLoading] = useState<boolean>(!initialCachedInvitations);
  const [error, setError] = useState<string | null>(null);
  const [busyActionKey, setBusyActionKey] = useState<string | null>(null);

  const applyInvitationsSnapshot = useCallback((incoming: Friendship[], outgoing: Friendship[]): void => {
    setIncomingRequests(incoming);
    setOutgoingRequests(outgoing);
  }, []);

  const loadInvitations = useCallback(async (silent = false): Promise<void> => {
    if (!silent) {
      setIsLoading(true);
      setError(null);
    }

    try {
      const snapshot = await syncFriendshipInvitationsCache();
      applyInvitationsSnapshot(snapshot.incoming, snapshot.outgoing);
      setError(null);
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Failed to load invitations.";
      if (!silent) {
        setError(String(message));
      }
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }, [applyInvitationsSnapshot]);

  useEffect(() => {
    let cancelled = false;

    const cachedSnapshot = getCachedFriendshipInvitations({ allowStale: true });
    if (cachedSnapshot) {
      applyInvitationsSnapshot(cachedSnapshot.incoming, cachedSnapshot.outgoing);
      setIsLoading(false);
      void loadInvitations(true);
    } else {
      void loadInvitations(false);
    }

    const handleFriendshipInvitationsUpdated = (event: Event): void => {
      if (cancelled) {
        return;
      }

      const customEvent = event as CustomEvent<{
        snapshot?: { incoming?: Friendship[]; outgoing?: Friendship[] };
      }>;
      const snapshot = customEvent.detail?.snapshot || getCachedFriendshipInvitations({ allowStale: true });
      if (!snapshot) {
        return;
      }

      applyInvitationsSnapshot(snapshot.incoming || [], snapshot.outgoing || []);
      setError(null);
      setIsLoading(false);
    };

    const intervalId = window.setInterval(() => {
      void loadInvitations(true);
    }, 5000);

    window.addEventListener(friendshipInvitationsUpdatedEventName, handleFriendshipInvitationsUpdated as EventListener);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      window.removeEventListener(friendshipInvitationsUpdatedEventName, handleFriendshipInvitationsUpdated as EventListener);
    };
  }, [applyInvitationsSnapshot, loadInvitations]);

  const currentList = useMemo(
    () => (activeTab === "incoming" ? incomingRequests : outgoingRequests),
    [activeTab, incomingRequests, outgoingRequests],
  );

  const withBusy = async (key: string, callback: () => Promise<void>): Promise<void> => {
    setBusyActionKey(key);
    try {
      await callback();
    } finally {
      setBusyActionKey(null);
    }
  };

  const handleAccept = async (friendshipId: string): Promise<void> => {
    await withBusy(`${friendshipId}:accept`, async () => {
      try {
        await acceptFriendRequest(friendshipId);
        alertContext?.showAlert?.(true, "Friend request accepted.");
      } catch (err: any) {
        const message = err?.response?.data?.detail || err?.message || "Failed to accept friend request.";
        alertContext?.showAlert?.(false, String(message));
      }
    });
  };

  const handleBlock = async (friendshipId: string): Promise<void> => {
    await withBusy(`${friendshipId}:block`, async () => {
      try {
        await blockFriendship(friendshipId);
        alertContext?.showAlert?.(true, "Friendship blocked.");
      } catch (err: any) {
        const message = err?.response?.data?.detail || err?.message || "Failed to block friendship.";
        alertContext?.showAlert?.(false, String(message));
      }
    });
  };

  const handleDelete = async (friendshipId: string, successMessage: string): Promise<void> => {
    await withBusy(`${friendshipId}:delete`, async () => {
      try {
        await deleteFriendship(friendshipId);
        alertContext?.showAlert?.(true, successMessage);
      } catch (err: any) {
        const message = err?.response?.data?.detail || err?.message || "Failed to delete invitation.";
        alertContext?.showAlert?.(false, String(message));
      }
    });
  };

  return (
    <VStack 
      justifyContent="flex-end"
            alignItems={{ base: "center", md: "flex-start" }}
      px={{ base: 4, md: 8 }} 
      py={6} w="100%"
    >
      <VStack w="100%" maxW="500px" gap={5}>
        <HStack justifyContent="space-between" alignItems="flex-start" mb={4}>
          <Stack gap={1}>
            <HStack gap={2}>
              <Icon as={LuUserPlus} color="primary" boxSize={5} />
              <Text className="title-styles" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="900">
                Friend invitations
              </Text>
            </HStack>
            <Text className="text-styles" color="rgba(229,231,235,0.82)" fontWeight="700">
              Manage your incoming and outgoing friend requests.
            </Text>
          </Stack>

          <Button
            onClick={() => void loadInvitations()}
            borderRadius="full"
            bg="rgba(255,255,255,0.08)"
            color="text"
            _hover={{ bg: "rgba(255,255,255,0.16)" }}
          >
            <LuRefreshCcw />
          </Button>
        </HStack>

        <HStack
          bg="variantSecondary"
          borderRadius="xl"
          p={2}
          mb={5}
          w="fit-content"
          maxW="100%"
          flexWrap="wrap"
          gap={2}
        >
          <Button
            borderRadius="full"
            bg={activeTab === "incoming" ? "primary" : "transparent"}
            color={activeTab === "incoming" ? "secondary" : "text"}
            _hover={{ bg: activeTab === "incoming" ? "primary" : "rgba(255,255,255,0.08)" }}
            onClick={() => setActiveTab("incoming")}
          >
            Incoming
            <Badge ml={2} borderRadius="full" bg="rgba(0,0,0,0.18)" color="white" px={2}>
              {incomingRequests.length}
            </Badge>
          </Button>

          <Button
            borderRadius="full"
            bg={activeTab === "outgoing" ? "primary" : "transparent"}
            color={activeTab === "outgoing" ? "secondary" : "text"}
            _hover={{ bg: activeTab === "outgoing" ? "primary" : "rgba(255,255,255,0.08)" }}
            onClick={() => setActiveTab("outgoing")}
          >
            Sent
            <Badge ml={2} borderRadius="full" bg="rgba(0,0,0,0.18)" color="white" px={2}>
              {outgoingRequests.length}
            </Badge>
          </Button>
        </HStack>

        {isLoading && (
          <Flex py={12} justifyContent="center">
            <Spinner color="primary" size="xl" />
          </Flex>
        )}

        {!isLoading && error && (
          <Box
            bg="rgba(246,105,105,0.14)"
            border="1px solid"
            borderColor="rgba(246,105,105,0.45)"
            borderRadius="lg"
            p={4}
            mb={4}
          >
            <Text className="text-styles" color="error" fontWeight="800">
              {error}
            </Text>
          </Box>
        )}

        {!isLoading && !error && currentList.length === 0 && (
          <Box
            bg="variantSecondary"
            borderRadius="2xl"
            p={{ base: 6, md: 8 }}
            textAlign="center"
          >
            <Text className="title-styles" fontWeight="800" fontSize="xl" mb={1}>
              {activeTab === "incoming" ? "No incoming invitations" : "No sent invitations"}
            </Text>
            <Text className="text-styles" color="rgba(229,231,235,0.82)" fontWeight="700">
              {activeTab === "incoming"
                ? "When someone sends you a friend request, it will appear here."
                : "Requests you send will appear here until accepted."}
            </Text>
          </Box>
        )}

        {!isLoading && !error && currentList.length > 0 && (
          <Stack gap={3}>
            {currentList.map((friendship) => {
              const friendName = fallbackFriendName(friendship);
              const profilePath = friendship.friend_user_id ? `/profile/${friendship.friend_user_id}` : "/profile";
              const avatarUrl = friendship.friend_avatar_url;

              return (
                <Flex
                  key={friendship.id}
                  bg="variantSecondary"
                  borderRadius="2xl"
                  p={{ base: 4, md: 5 }}
                  gap={4}
                  alignItems={{ base: "stretch", md: "center" }}
                  justifyContent="space-between"
                  flexDirection={{ base: "column", md: "row" }}
                >
                  <HStack minW={0} gap={3}>
                    <Link asChild _hover={{ textDecoration: "none" }}>
                      <RouterLink to={profilePath}>
                        <Avatar.Root size="lg">
                          <Avatar.Fallback name={friendName || ""} />
                          <Avatar.Image src={avatarUrl || undefined} />
                        </Avatar.Root>
                      </RouterLink>
                    </Link>

                    <Stack gap={0} minW={0}>
                      <Link asChild color="text" _hover={{ color: "primary" }}>
                        <RouterLink to={profilePath}>
                          <Text className="title-styles" fontWeight="900" truncate>
                            {friendName}
                          </Text>
                        </RouterLink>
                      </Link>
                      <Text className="text-styles" color="rgba(229,231,235,0.82)" fontSize="sm" fontWeight="700">
                        {activeTab === "incoming" ? "Sent you a friend request" : "Request sent"}
                      </Text>
                      <Text className="text-styles" color="rgba(229,231,235,0.62)" fontSize="xs" fontWeight="600">
                        {formatRelativeDate(friendship.created_at)}
                      </Text>
                    </Stack>
                  </HStack>

                  <HStack
                    gap={2}
                    justifyContent={{ base: "flex-start", md: "flex-end" }}
                    flexWrap="wrap"
                  >
                    {friendship.friend_online && (
                      <Badge colorPalette="green" borderRadius="full">
                        Online
                      </Badge>
                    )}

                    {activeTab === "incoming" ? (
                      <>
                        <Button
                          size="sm"
                          borderRadius="full"
                          bg="primary"
                          color="secondary"
                          _hover={{ bg: "#f4cf4f" }}
                          disabled={busyActionKey !== null}
                          onClick={() => void handleAccept(friendship.id)}
                        >
                          Accept
                        </Button>
                        <Button
                          size="sm"
                          borderRadius="full"
                          variant="outline"
                          borderColor="rgba(255,255,255,0.25)"
                          color="text"
                          _hover={{ bg: "rgba(255,255,255,0.08)" }}
                          disabled={busyActionKey !== null}
                          onClick={() => void handleDelete(friendship.id, "Friend request declined.")}
                        >
                          Decline
                        </Button>
                        <Button
                          size="sm"
                          borderRadius="full"
                          variant="outline"
                          borderColor="rgba(255,94,94,0.45)"
                          color="#ff8b8b"
                          _hover={{ bg: "rgba(255,94,94,0.14)" }}
                          disabled={busyActionKey !== null}
                          onClick={() => void handleBlock(friendship.id)}
                        >
                          Block
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        borderRadius="full"
                        variant="outline"
                        borderColor="rgba(255,255,255,0.25)"
                        color="text"
                        _hover={{ bg: "rgba(255,255,255,0.08)" }}
                        disabled={busyActionKey !== null}
                        onClick={() => void handleDelete(friendship.id, "Friend request canceled.")}
                      >
                        Cancel request
                      </Button>
                    )}
                  </HStack>
                </Flex>
              );
            })}
          </Stack>
        )}
      </VStack>
    </VStack>
  );
}

export default Invitations;
