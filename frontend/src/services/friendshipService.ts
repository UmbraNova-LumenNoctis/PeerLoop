import axios from "axios";
import type { Friendship } from "@/types/friendship";
import type { FriendshipDirection, FriendshipStatus } from "@/types/friendship";
import { attachAuthInterceptors, getStoredToken, resolveApiBaseUrl } from "@/utils/authSession";

interface FriendshipInvitationsSnapshot {
  incoming: Friendship[];
  outgoing: Friendship[];
  updatedAt: number;
}

interface FriendshipInvitationsEventDetail {
  reason?: string;
  snapshot: FriendshipInvitationsSnapshot;
}

const FRIENDSHIP_INVITATIONS_CACHE_TTL_MS = 60_000;
const FRIENDSHIP_INVITATIONS_CACHE_KEY = "friendship:invitations-cache:v1";
const FRIENDSHIP_INVITATIONS_UPDATED_EVENT = "friendship:invitations-updated";

const friendshipInvitationsCache: FriendshipInvitationsSnapshot = {
  incoming: [],
  outgoing: [],
  updatedAt: 0,
};

const friendshipApi = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 10000,
  withCredentials: true,
});
attachAuthInterceptors(friendshipApi);

const authHeaders = (): Record<string, string> => {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const cloneInvitations = (items: Friendship[]): Friendship[] => items.map((item) => ({ ...item }));

const friendshipListSignature = (items: Friendship[]): string => {
  return items
    .map((item) => `${item.id}:${item.status}:${item.direction || ""}:${item.friend_user_id || ""}`)
    .sort()
    .join("|");
};

const persistFriendshipInvitationsCache = (): void => {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.sessionStorage.setItem(
      FRIENDSHIP_INVITATIONS_CACHE_KEY,
      JSON.stringify(friendshipInvitationsCache),
    );
  } catch {
    // Ignore storage failures.
  }
};

const hydrateFriendshipInvitationsCache = (): void => {
  if (typeof window === "undefined") {
    return;
  }

  try {
    const raw = window.sessionStorage.getItem(FRIENDSHIP_INVITATIONS_CACHE_KEY);
    if (!raw) {
      return;
    }

    const parsed = JSON.parse(raw) as Partial<FriendshipInvitationsSnapshot>;
    friendshipInvitationsCache.incoming = Array.isArray(parsed?.incoming) ? cloneInvitations(parsed.incoming) : [];
    friendshipInvitationsCache.outgoing = Array.isArray(parsed?.outgoing) ? cloneInvitations(parsed.outgoing) : [];
    friendshipInvitationsCache.updatedAt = Number(parsed?.updatedAt || 0);
  } catch {
    friendshipInvitationsCache.incoming = [];
    friendshipInvitationsCache.outgoing = [];
    friendshipInvitationsCache.updatedAt = 0;
  }
};

hydrateFriendshipInvitationsCache();

const emitFriendshipInvitationsUpdated = (reason?: string): void => {
  if (typeof window === "undefined") {
    return;
  }

  const detail: FriendshipInvitationsEventDetail = {
    reason,
    snapshot: {
      incoming: cloneInvitations(friendshipInvitationsCache.incoming),
      outgoing: cloneInvitations(friendshipInvitationsCache.outgoing),
      updatedAt: friendshipInvitationsCache.updatedAt,
    },
  };

  window.dispatchEvent(
    new CustomEvent(FRIENDSHIP_INVITATIONS_UPDATED_EVENT, {
      detail,
    }),
  );
};

const setFriendshipInvitationsCache = (
  incoming: Friendship[],
  outgoing: Friendship[],
  reason?: string,
): FriendshipInvitationsSnapshot => {
  const previousIncomingSignature = friendshipListSignature(friendshipInvitationsCache.incoming);
  const previousOutgoingSignature = friendshipListSignature(friendshipInvitationsCache.outgoing);
  const nextIncomingSignature = friendshipListSignature(incoming);
  const nextOutgoingSignature = friendshipListSignature(outgoing);
  const hasChanged = previousIncomingSignature !== nextIncomingSignature
    || previousOutgoingSignature !== nextOutgoingSignature;

  friendshipInvitationsCache.incoming = cloneInvitations(incoming);
  friendshipInvitationsCache.outgoing = cloneInvitations(outgoing);
  friendshipInvitationsCache.updatedAt = Date.now();
  persistFriendshipInvitationsCache();
  if (hasChanged) {
    emitFriendshipInvitationsUpdated(reason);
  }

  return {
    incoming: cloneInvitations(friendshipInvitationsCache.incoming),
    outgoing: cloneInvitations(friendshipInvitationsCache.outgoing),
    updatedAt: friendshipInvitationsCache.updatedAt,
  };
};

const mutateFriendshipInvitationsCache = (
  updater: (current: FriendshipInvitationsSnapshot) => FriendshipInvitationsSnapshot,
  reason?: string,
): FriendshipInvitationsSnapshot => {
  const currentSnapshot: FriendshipInvitationsSnapshot = {
    incoming: cloneInvitations(friendshipInvitationsCache.incoming),
    outgoing: cloneInvitations(friendshipInvitationsCache.outgoing),
    updatedAt: friendshipInvitationsCache.updatedAt,
  };
  const nextSnapshot = updater(currentSnapshot);
  return setFriendshipInvitationsCache(nextSnapshot.incoming, nextSnapshot.outgoing, reason);
};

const isInvitationsCacheFresh = (): boolean => {
  if (!friendshipInvitationsCache.updatedAt) {
    return false;
  }
  return Date.now() - friendshipInvitationsCache.updatedAt <= FRIENDSHIP_INVITATIONS_CACHE_TTL_MS;
};

export const friendshipInvitationsUpdatedEventName = FRIENDSHIP_INVITATIONS_UPDATED_EVENT;

export const getCachedFriendshipInvitations = (
  options?: { allowStale?: boolean },
): FriendshipInvitationsSnapshot | null => {
  if (!options?.allowStale && !isInvitationsCacheFresh()) {
    return null;
  }

  return {
    incoming: cloneInvitations(friendshipInvitationsCache.incoming),
    outgoing: cloneInvitations(friendshipInvitationsCache.outgoing),
    updatedAt: friendshipInvitationsCache.updatedAt,
  };
};

export const syncFriendshipInvitationsCache = async (): Promise<FriendshipInvitationsSnapshot> => {
  const [incomingResponse, outgoingResponse] = await Promise.all([
    friendshipApi.get<Friendship[]>("/api/friendships/incoming", { headers: authHeaders() }),
    friendshipApi.get<Friendship[]>("/api/friendships/outgoing", { headers: authHeaders() }),
  ]);

  const incoming = Array.isArray(incomingResponse.data) ? incomingResponse.data : [];
  const outgoing = Array.isArray(outgoingResponse.data) ? outgoingResponse.data : [];

  return setFriendshipInvitationsCache(incoming, outgoing, "sync");
};

export const fetchIncomingFriendRequests = async (): Promise<Friendship[]> => {
  const response = await friendshipApi.get<Friendship[]>("/api/friendships/incoming", {
    headers: authHeaders(),
  });
  const incoming = Array.isArray(response.data) ? response.data : [];
  setFriendshipInvitationsCache(incoming, friendshipInvitationsCache.outgoing, "fetch_incoming");
  return incoming;
};

export const fetchOutgoingFriendRequests = async (): Promise<Friendship[]> => {
  const response = await friendshipApi.get<Friendship[]>("/api/friendships/outgoing", {
    headers: authHeaders(),
  });
  const outgoing = Array.isArray(response.data) ? response.data : [];
  setFriendshipInvitationsCache(friendshipInvitationsCache.incoming, outgoing, "fetch_outgoing");
  return outgoing;
};

export const fetchFriendships = async (
  status?: FriendshipStatus,
  direction?: FriendshipDirection,
): Promise<Friendship[]> => {
  const response = await friendshipApi.get<Friendship[]>("/api/friendships", {
    headers: authHeaders(),
    params: {
      ...(status ? { status } : {}),
      ...(direction ? { direction } : {}),
    },
  });
  return Array.isArray(response.data) ? response.data : [];
};

export const fetchPendingFriendRequests = async (): Promise<Friendship[]> => {
  const response = await friendshipApi.get<Friendship[]>("/api/friendships/pending", {
    headers: authHeaders(),
  });
  return Array.isArray(response.data) ? response.data : [];
};

export const sendFriendRequest = async (targetUserId: string): Promise<Friendship> => {
  const response = await friendshipApi.post<Friendship>(
    "/api/friendships/request",
    { target_user_id: targetUserId },
    { headers: authHeaders() },
  );
  const created = response.data;

  mutateFriendshipInvitationsCache((current) => {
    const dedupedOutgoing = current.outgoing.filter((item) => {
      if (item.id === created.id) {
        return false;
      }

      if (created.friend_user_id && item.friend_user_id === created.friend_user_id) {
        return false;
      }

      return true;
    });

    return {
      ...current,
      outgoing: [created, ...dedupedOutgoing],
    };
  }, "request_sent");

  return created;
};

export const acceptFriendRequest = async (friendshipId: string): Promise<Friendship> => {
  const response = await friendshipApi.patch<Friendship>(
    `/api/friendships/${friendshipId}/accept`,
    {},
    { headers: authHeaders() },
  );
  const accepted = response.data;

  mutateFriendshipInvitationsCache((current) => ({
    ...current,
    incoming: current.incoming.filter((item) => item.id !== friendshipId),
    outgoing: current.outgoing.filter((item) => item.id !== friendshipId),
  }), "request_accepted");

  return accepted;
};

export const blockFriendship = async (friendshipId: string): Promise<Friendship> => {
  const response = await friendshipApi.patch<Friendship>(
    `/api/friendships/${friendshipId}/block`,
    {},
    { headers: authHeaders() },
  );
  const blocked = response.data;

  mutateFriendshipInvitationsCache((current) => ({
    ...current,
    incoming: current.incoming.filter((item) => item.id !== friendshipId),
    outgoing: current.outgoing.filter((item) => item.id !== friendshipId),
  }), "request_blocked");

  return blocked;
};

export const deleteFriendship = async (friendshipId: string): Promise<void> => {
  await friendshipApi.delete(`/api/friendships/${friendshipId}`, {
    headers: authHeaders(),
  });

  mutateFriendshipInvitationsCache((current) => ({
    ...current,
    incoming: current.incoming.filter((item) => item.id !== friendshipId),
    outgoing: current.outgoing.filter((item) => item.id !== friendshipId),
  }), "request_deleted");
};
