import { PostData } from "@/types/Post";

interface CachedPostEntry {
  data: PostData;
  cachedAt: number;
}

const POST_CACHE_TTL_MS = 60_000;
const POST_CACHE_INVALIDATION_EVENT = "post-cache:invalidate";
const POST_CACHE_STORAGE_KEY = "post:cache:v1";
const postCache = new Map<string, CachedPostEntry>();

const persistPostCache = (): void => {
  if (typeof window === "undefined") {
    return;
  }

  try {
    const serialized = JSON.stringify(Object.fromEntries(postCache.entries()));
    window.sessionStorage.setItem(POST_CACHE_STORAGE_KEY, serialized);
  } catch {
    // Ignore storage quota/private mode errors.
  }
};

const hydratePostCache = (): void => {
  if (typeof window === "undefined") {
    return;
  }

  try {
    const raw = window.sessionStorage.getItem(POST_CACHE_STORAGE_KEY);
    if (!raw) {
      return;
    }

    const parsed = JSON.parse(raw) as Record<string, CachedPostEntry>;
    Object.entries(parsed || {}).forEach(([postId, entry]) => {
      if (!entry?.data || !entry?.cachedAt) {
        return;
      }
      postCache.set(postId, entry);
    });
  } catch {
    // Ignore corrupted session cache.
  }
};

hydratePostCache();

const isCacheFresh = (entry: CachedPostEntry | undefined): boolean => {
  if (!entry) {
    return false;
  }

  return Date.now() - entry.cachedAt <= POST_CACHE_TTL_MS;
};

const mergePostPayload = (existing: PostData | undefined, incoming: PostData): PostData => {
  return {
    ...(existing || {}),
    ...incoming,
    id: incoming.id || existing?.id || "",
  };
};

export const getCachedPost = (
  postId: string,
  options?: { allowStale?: boolean },
): PostData | null => {
  const entry = postCache.get(postId);
  if (!entry) {
    return null;
  }

  if (!options?.allowStale && !isCacheFresh(entry)) {
    return null;
  }

  return entry.data;
};

export const hasFreshPostCache = (postId: string): boolean => {
  return isCacheFresh(postCache.get(postId));
};

export const cachePost = (post: PostData): void => {
  if (!post?.id) {
    return;
  }

  const existing = postCache.get(post.id)?.data;
  postCache.set(post.id, {
    data: mergePostPayload(existing, post),
    cachedAt: Date.now(),
  });
  persistPostCache();
};

export const invalidatePostCache = (postId?: string): void => {
  if (postId) {
    postCache.delete(postId);
    persistPostCache();
    return;
  }

  postCache.clear();
  persistPostCache();
};

export const notifyPostCacheInvalidated = (postId?: string): void => {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(
    new CustomEvent(POST_CACHE_INVALIDATION_EVENT, {
      detail: { postId },
    }),
  );
};

export const invalidateAndNotifyPostCache = (postId?: string): void => {
  invalidatePostCache(postId);
  notifyPostCacheInvalidated(postId);
};

export const postCacheInvalidationEventName = POST_CACHE_INVALIDATION_EVENT;
