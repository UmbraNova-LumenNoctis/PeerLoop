import { useCallback, useContext, useEffect, useMemo, useState, type JSX } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import {
  Avatar,
  Badge,
  Box,
  Button,
  Flex,
  HStack,
  Icon,
  Input,
  InputGroup,
  Link,
  Spinner,
  Stack,
  Text,
} from "@chakra-ui/react";
import { LuMessageCircleMore, LuRefreshCcw, LuSearch, LuShieldBan, LuTrash2, LuUsers } from "react-icons/lu";
import { AlertContext } from "@/context/alertContext";
import {
  blockFriendship,
  deleteFriendship,
  fetchFriendships,
  friendshipInvitationsUpdatedEventName,
} from "@/services/friendshipService";
import type { Friendship } from "@/types/friendship";

const fallbackFriendName = (friendship: Friendship): string => {
  const pseudo = friendship.friend_pseudo?.trim();
  if (pseudo) {
    return pseudo;
  }
  const fallbackId = friendship.friend_user_id || friendship.user_b_id || friendship.user_a_id || "user";
  return `User_${String(fallbackId).slice(0, 8)}`;
};

const formatFriendshipDate = (value: string | null): string => {
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

function Friends(): JSX.Element {
  const navigate = useNavigate();
  const alertContext = useContext(AlertContext) as any;
  const [friends, setFriends] = useState<Friendship[]>([]);
  const [query, setQuery] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [busyActionKey, setBusyActionKey] = useState<string | null>(null);

  const loadFriends = useCallback(async (silent = false): Promise<void> => {
    if (!silent) {
      setIsLoading(true);
    }

    try {
      const items = await fetchFriendships("accepted");
      const sorted = [...items].sort((left, right) => {
        const leftTs = new Date(left.created_at || 0).getTime();
        const rightTs = new Date(right.created_at || 0).getTime();
        return rightTs - leftTs;
      });
      setFriends(sorted);
      setError(null);
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Failed to load friends.";
      if (!silent) {
        setError(String(message));
      }
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadFriends(false);

    const handleInvitationChange = (): void => {
      void loadFriends(true);
    };

    const intervalId = window.setInterval(() => {
      if (document.visibilityState !== "visible") {
        return;
      }
      void loadFriends(true);
    }, 15000);

    window.addEventListener(friendshipInvitationsUpdatedEventName, handleInvitationChange as EventListener);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener(friendshipInvitationsUpdatedEventName, handleInvitationChange as EventListener);
    };
  }, [loadFriends]);

  const filteredFriends = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return friends;
    }

    return friends.filter((friendship) => {
      const pseudo = (friendship.friend_pseudo || "").toLowerCase();
      const friendId = (friendship.friend_user_id || "").toLowerCase();
      return pseudo.includes(normalized) || friendId.includes(normalized);
    });
  }, [friends, query]);

  const withBusy = async (key: string, callback: () => Promise<void>): Promise<void> => {
    setBusyActionKey(key);
    try {
      await callback();
    } finally {
      setBusyActionKey(null);
    }
  };

  const handleRemoveFriend = async (friendship: Friendship): Promise<void> => {
    const previousFriends = friends;
    setFriends((current) => current.filter((item) => item.id !== friendship.id));

    await withBusy(`${friendship.id}:remove`, async () => {
      try {
        await deleteFriendship(friendship.id);
        alertContext?.showAlert?.(true, "Friend removed.");
      } catch (err: any) {
        setFriends(previousFriends);
        const message = err?.response?.data?.detail || err?.message || "Failed to remove friend.";
        alertContext?.showAlert?.(false, String(message));
      }
    });
  };

  const handleBlockFriend = async (friendship: Friendship): Promise<void> => {
    const previousFriends = friends;
    setFriends((current) => current.filter((item) => item.id !== friendship.id));

    await withBusy(`${friendship.id}:block`, async () => {
      try {
        await blockFriendship(friendship.id);
        alertContext?.showAlert?.(true, "User blocked.");
      } catch (err: any) {
        setFriends(previousFriends);
        const message = err?.response?.data?.detail || err?.message || "Failed to block user.";
        alertContext?.showAlert?.(false, String(message));
      }
    });
  };

  const handleMessage = (friendship: Friendship): void => {
    if (!friendship.friend_user_id) {
      alertContext?.showAlert?.(false, "This friend cannot be messaged right now.");
      return;
    }

    const params = new URLSearchParams();
    params.set("start_with", friendship.friend_user_id);
    params.set("start_name", fallbackFriendName(friendship));
    if (friendship.friend_avatar_url) {
      params.set("start_avatar", friendship.friend_avatar_url);
    }

    navigate(`/chat?${params.toString()}`);
  };

  return (
    <Flex w="100%" justifyContent="flex-end" alignItems="flex-start" px={{ base: 4, md: 8 }} py={6}>
      <Box w="100%" maxW="500px">
        <HStack justifyContent="space-between" alignItems="flex-start" mb={4}>
          <Stack gap={1}>
            <HStack gap={2}>
              <Icon as={LuUsers} color="primary" boxSize={5} />
              <Text className="title-styles" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="900">
                Friends
              </Text>
              <Badge borderRadius="full" bg="rgba(112,205,75,0.18)" color="primary" px={3} py={1}>
                {friends.length}
              </Badge>
            </HStack>
            <Text className="text-styles" color="rgba(229,231,235,0.82)" fontWeight="700">
              See and manage your friend list.
            </Text>
          </Stack>

          <Button
            onClick={() => void loadFriends(false)}
            borderRadius="full"
            bg="hsla(0, 0%, 100%, 0.08)"
            color="text"
            _hover={{ bg: "rgba(255,255,255,0.16)" }}
          >
            <LuRefreshCcw />
          </Button>
        </HStack>

        <InputGroup startElement={<LuSearch color="white" />} mb={5}>
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by name or user id"
            borderRadius="full"
            borderColor="text"
            className="title-styles"
            bg="secondary"
            _placeholder={{ fontFamily: "Poppins", color: "text" }}
            _focus={{ focusRing: "none", borderColor: "primary" }}
            _hover={{ borderColor: "primary" }}
            maxLength={120}
          />
        </InputGroup>

        {isLoading && (
          <Flex py={12} justifyContent="center">
            <Spinner color="primary" size="xl" />
          </Flex>
        )}

        {!isLoading && error && (
          <Box
            bg="rgba(246,105,105,0.14)"
            border="1px solid"
            borderColor="hsla(0, 89%, 69%, 0.45)"
            borderRadius="lg"
            p={4}
            mb={4}
          >
            <Text className="text-styles" color="error" fontWeight="800">
              {error}
            </Text>
          </Box>
        )}

        {!isLoading && !error && filteredFriends.length === 0 && (
          <Box
            bg="variantSecondary"
            borderRadius="2xl"
            p={{ base: 6, md: 8 }}
            textAlign="center"
          >
            <Text className="title-styles" fontWeight="800" fontSize="xl" mb={1}>
              No friends found
            </Text>
            <Text className="text-styles" color="rgba(229,231,235,0.82)" fontWeight="700">
              Add friends from profiles, then manage them here.
            </Text>
          </Box>
        )}

        {!isLoading && !error && filteredFriends.length > 0 && (
          <Stack gap={3}>
            {filteredFriends.map((friendship) => {
              const friendName = fallbackFriendName(friendship);
              const avatarUrl = friendship.friend_avatar_url;
              const profilePath = friendship.friend_user_id ? `/profile/${friendship.friend_user_id}` : "/profile";
              const isRemoving = busyActionKey === `${friendship.id}:remove`;
              const isBlocking = busyActionKey === `${friendship.id}:block`;
              const isBusy = Boolean(busyActionKey);

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

                    <Box minW={0}>
                      <Link asChild _hover={{ textDecoration: "none", color: "primary" }}>
                        <RouterLink to={profilePath}>
                          <Text className="title-styles" fontWeight="900" fontSize="lg" lineClamp={1}>
                            {friendName}
                          </Text>
                        </RouterLink>
                      </Link>
                      <HStack gap={2} wrap="wrap">
                        <Text className="text-styles" fontSize="sm" color="rgba(229,231,235,0.78)" fontWeight="700">
                          Friends since {formatFriendshipDate(friendship.created_at)}
                        </Text>
                        {friendship.friend_online && (
                          <Badge borderRadius="full" bg="rgba(112,205,75,0.22)" color="primary" px={2}>
                            Online
                          </Badge>
                        )}
                      </HStack>
                    </Box>
                  </HStack>

                  <HStack gap={2} flexWrap="wrap" justifyContent={{ base: "flex-start", md: "flex-end" }}>
                    <Button
                      borderRadius="full"
                      bg="primary"
                      color="secondary"
                      _hover={{ opacity: 0.9 }}
                      onClick={() => handleMessage(friendship)}
                    >
                      <LuMessageCircleMore />
                    </Button>

                    <Button
                      borderRadius="full"
                      bg="rgba(255,255,255,0.1)"
                      color="text"
                      _hover={{ bg: "rgba(255,255,255,0.16)" }}
                      loading={isRemoving}
                      disabled={isBusy}
                      onClick={() => void handleRemoveFriend(friendship)}
                    >
                      <LuTrash2 />
                    </Button>

                    <Button
                      borderRadius="full"
                      bg="rgba(246,105,105,0.18)"
                      color="#f9cece"
                      _hover={{ bg: "rgba(246,105,105,0.3)" }}
                      loading={isBlocking}
                      disabled={isBusy}
                      onClick={() => void handleBlockFriend(friendship)}
                    >
                      <LuShieldBan />
                    </Button>
                  </HStack>
                </Flex>
              );
            })}
          </Stack>
        )}
      </Box>
    </Flex>
  );
}

export default Friends;
