import { PostData } from "@/types/Post";
import { JSX, type ChangeEvent, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    Avatar,
    Box,
    Button,
    Dialog,
    Field,
    Flex,
    Grid,
    HStack,
    Input,
    Spinner,
    Text,
    Textarea,
    VStack,
} from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import {
    LuCalendarDays,
    LuBan,
    LuEllipsis,
    LuImagePlus,
    LuMail,
    LuMapPin,
    LuMessageCircle,
    LuPencil,
    LuUserMinus,
    LuUserPlus,
} from "react-icons/lu";
import useApi from "@/hooks/useAPI";
import { UserContext } from "@/context/userContext";
import { AlertContext } from "@/context/alertContext";
import { AuthContext } from "@/context/authContext";
import { PostCard } from "@/components/PostCard";
import { cachePost, invalidateAndNotifyPostCache } from "@/utils/postCache";
import { useResolvedUserProfile, type UserProfile } from "@/hooks/useUserProfile";
import {
    acceptFriendRequest,
    blockFriendship,
    deleteFriendship,
    fetchFriendships,
    friendshipInvitationsUpdatedEventName,
    sendFriendRequest,
} from "@/services/friendshipService";
import type { Friendship } from "@/types/friendship";

type PreviewTarget = "avatar" | "cover" | null;
type FriendshipState = "none" | "pending_incoming" | "pending_outgoing" | "accepted" | "blocked";

interface UploadedFileResponse {
    media_id?: string;
    id?: string;
    url?: string;
    preview_url?: string;
}

interface ProfilePost extends PostData {
    media_id?: string | null;
    updated_at?: string | null;
    comment_count?: number;
}

interface TwoFaEnableResponse {
    qr_code?: string;
    otpauth_url?: string;
    secret?: string;
    account_name?: string;
    issuer?: string;
    message?: string;
}

interface TwoFaStatusResponse {
    enabled?: boolean;
    initialized?: boolean;
}

interface EditProfileFormState {
    pseudo: string;
    bio: string;
    address: string;
}

interface PendingProfileMediaUpload {
    target: "avatar" | "cover";
    file: File;
}

interface ProfilePageCacheEntry {
    profile: UserProfile | null;
    posts: ProfilePost[];
    savedAt: number;
}

type ProfilePageCacheMap = Record<string, ProfilePageCacheEntry>;
type TwoFaStatusCacheMap = Record<string, { enabled: boolean; savedAt: number }>;

const PROFILE_PAGE_CACHE_KEY = "profile-page-cache:v1";
const PROFILE_PAGE_CACHE_TTL_MS = 15 * 60 * 1000;
const TWOFA_STATUS_CACHE_KEY = "profile-twofa-status-cache:v1";
const TWOFA_STATUS_CACHE_TTL_MS = 15 * 60 * 1000;

const riseIn = keyframes`
    from { opacity: 0; transform: translateY(24px); }
    to { opacity: 1; transform: translateY(0); }
`;

const slideIn = keyframes`
    from { opacity: 0; transform: translateX(24px); }
    to { opacity: 1; transform: translateX(0); }
`;

const readProfileCacheMap = (): ProfilePageCacheMap => {
    if (typeof window === "undefined") {
        return {};
    }

    try {
        const raw = window.sessionStorage.getItem(PROFILE_PAGE_CACHE_KEY);
        if (!raw) {
            return {};
        }
        const parsed = JSON.parse(raw) as ProfilePageCacheMap;
        return parsed || {};
    } catch {
        return {};
    }
};

const writeProfileCacheMap = (cacheMap: ProfilePageCacheMap): void => {
    if (typeof window === "undefined") {
        return;
    }

    try {
        window.sessionStorage.setItem(PROFILE_PAGE_CACHE_KEY, JSON.stringify(cacheMap));
    } catch {
        // Ignore storage errors.
    }
};

const readProfileCacheEntry = (scope: string): ProfilePageCacheEntry | null => {
    const cacheMap = readProfileCacheMap();
    const entry = cacheMap[scope];
    if (!entry) {
        return null;
    }

    const isFresh = Date.now() - Number(entry.savedAt || 0) <= PROFILE_PAGE_CACHE_TTL_MS;
    if (!isFresh) {
        return null;
    }

    return entry;
};

const upsertProfileCacheEntry = (scope: string, entry: ProfilePageCacheEntry): void => {
    const cacheMap = readProfileCacheMap();
    cacheMap[scope] = entry;
    writeProfileCacheMap(cacheMap);
};

const readTwoFaStatusCacheMap = (): TwoFaStatusCacheMap => {
    if (typeof window === "undefined") {
        return {};
    }

    try {
        const raw = window.sessionStorage.getItem(TWOFA_STATUS_CACHE_KEY);
        if (!raw) {
            return {};
        }
        const parsed = JSON.parse(raw) as TwoFaStatusCacheMap;
        return parsed || {};
    } catch {
        return {};
    }
};

const writeTwoFaStatusCacheMap = (cacheMap: TwoFaStatusCacheMap): void => {
    if (typeof window === "undefined") {
        return;
    }

    try {
        window.sessionStorage.setItem(TWOFA_STATUS_CACHE_KEY, JSON.stringify(cacheMap));
    } catch {
        // Ignore storage failures.
    }
};

const readTwoFaStatusCacheEntry = (scope: string): { enabled: boolean; savedAt: number } | null => {
    const cacheMap = readTwoFaStatusCacheMap();
    const entry = cacheMap[scope];
    if (!entry) {
        return null;
    }

    const isFresh = Date.now() - Number(entry.savedAt || 0) <= TWOFA_STATUS_CACHE_TTL_MS;
    if (!isFresh) {
        return null;
    }
    return entry;
};

const upsertTwoFaStatusCacheEntry = (scope: string, enabled: boolean): void => {
    const cacheMap = readTwoFaStatusCacheMap();
    cacheMap[scope] = {
        enabled,
        savedAt: Date.now(),
    };
    writeTwoFaStatusCacheMap(cacheMap);
};

const toFormState = (profile: UserProfile | null): EditProfileFormState => ({
    pseudo: profile?.pseudo || "",
    bio: profile?.bio || "",
    address: profile?.address || "",
});

const formatMemberSince = (dateValue: string | null | undefined): string => {
    if (!dateValue) {
        return "Unknown date";
    }

    const date = new Date(dateValue);
    if (Number.isNaN(date.getTime())) {
        return "Unknown date";
    }

    return new Intl.DateTimeFormat("en-US", {
        month: "long",
        year: "numeric",
    }).format(date);
};

const withCacheBuster = (rawUrl: string | null | undefined, seed: string | number): string | null => {
    if (!rawUrl || typeof rawUrl !== "string") {
        return null;
    }

    const trimmed = rawUrl.trim();
    if (!trimmed) {
        return null;
    }

    const cacheSeed = String(seed);
    try {
        const parsed = new URL(trimmed);
        parsed.searchParams.set("v", cacheSeed);
        return parsed.toString();
    } catch {
        const separator = trimmed.includes("?") ? "&" : "?";
        return `${trimmed}${separator}v=${encodeURIComponent(cacheSeed)}`;
    }
};

function Profile(): JSX.Element {
    const { userId } = useParams();
    const navigate = useNavigate();
    const cacheScope = userId || "me";
    const cachedEntry = useMemo(() => readProfileCacheEntry(cacheScope), [cacheScope]);

    const { profile, isLoading, error } = useResolvedUserProfile(userId || null);
    const { execute: executePostsRequest } = useApi<ProfilePost[]>();
    const { execute: executeUpload } = useApi<UploadedFileResponse>();
    const { execute: executeProfileUpdate } = useApi<UserProfile>();
    const { execute: executeProfileFetch } = useApi<UserProfile>();
    const { execute: executeCreatePost } = useApi<PostData>();
    const { execute: executeTwoFaStatus } = useApi<TwoFaStatusResponse>();
    const { execute: executeTwoFaEnable } = useApi<TwoFaEnableResponse>();
    const { execute: executeTwoFaVerify } = useApi<{ message?: string }>();
    const { execute: executeTwoFaDisable } = useApi<{ message?: string }>();
    const userContext = useContext(UserContext) as any;
    const alertContext = useContext(AlertContext) as any;
    const authContext = useContext(AuthContext) as any;

    const [displayProfile, setDisplayProfile] = useState<UserProfile | null>(cachedEntry?.profile || null);
    const [publishedPosts, setPublishedPosts] = useState<ProfilePost[]>(cachedEntry?.posts || []);
    const [isPostsLoading, setIsPostsLoading] = useState<boolean>(!cachedEntry);
    const [postsError, setPostsError] = useState<string | null>(null);
    const [isEditDialogOpen, setIsEditDialogOpen] = useState<boolean>(false);
    const [editForm, setEditForm] = useState<EditProfileFormState>(toFormState(cachedEntry?.profile || null));
    const [isSavingProfile, setIsSavingProfile] = useState<boolean>(false);
    const [isAvatarUploading, setIsAvatarUploading] = useState<boolean>(false);
    const [isCoverUploading, setIsCoverUploading] = useState<boolean>(false);
    const [avatarUploadProgress, setAvatarUploadProgress] = useState<number>(0);
    const [coverUploadProgress, setCoverUploadProgress] = useState<number>(0);
    const [pendingMediaUpload, setPendingMediaUpload] = useState<PendingProfileMediaUpload | null>(null);
    const [mediaPostDescription, setMediaPostDescription] = useState<string>("");
    const [isMediaUploadDialogBusy, setIsMediaUploadDialogBusy] = useState<boolean>(false);
    const [previewTarget, setPreviewTarget] = useState<PreviewTarget>(null);
    const [friendshipRelation, setFriendshipRelation] = useState<Friendship | null>(null);
    const [friendshipActionBusy, setFriendshipActionBusy] = useState<boolean>(false);
    const [isRelationMenuOpen, setIsRelationMenuOpen] = useState<boolean>(false);
    const [isOwnMenuOpen, setIsOwnMenuOpen] = useState<boolean>(false);
    const [isTwoFaEnabled, setIsTwoFaEnabled] = useState<boolean>(false);
    const [isTwoFaLoading, setIsTwoFaLoading] = useState<boolean>(false);
    const [isTwoFaBusy, setIsTwoFaBusy] = useState<boolean>(false);
    const [isTwoFaDialogOpen, setIsTwoFaDialogOpen] = useState<boolean>(false);
    const [twoFaQrCode, setTwoFaQrCode] = useState<string | null>(null);
    const [twoFaSecret, setTwoFaSecret] = useState<string>("");
    const [twoFaOtpAuthUrl, setTwoFaOtpAuthUrl] = useState<string>("");
    const [twoFaCode, setTwoFaCode] = useState<string>("");

    const avatarInputRef = useRef<HTMLInputElement | null>(null);
    const coverInputRef = useRef<HTMLInputElement | null>(null);
    const relationMenuRef = useRef<HTMLDivElement | null>(null);
    const ownMenuRef = useRef<HTMLDivElement | null>(null);

    const effectiveProfile = displayProfile || profile || null;
    const currentUserId = userContext?.user?.id || null;
    const twoFaCacheScope = currentUserId ? String(currentUserId) : "me";
    const isOwnProfile = useMemo(
        () => Boolean(!userId || (effectiveProfile?.id && currentUserId && effectiveProfile.id === currentUserId)),
        [currentUserId, effectiveProfile?.id, userId],
    );
    const targetProfileId = effectiveProfile?.id ? String(effectiveProfile.id) : null;

    const friendshipState = useMemo<FriendshipState>(() => {
        if (!friendshipRelation) {
            return "none";
        }
        if (friendshipRelation.status === "blocked") {
            return "blocked";
        }
        if (friendshipRelation.status === "accepted") {
            return "accepted";
        }
        if (friendshipRelation.status === "pending") {
            return friendshipRelation.direction === "incoming" ? "pending_incoming" : "pending_outgoing";
        }
        return "none";
    }, [friendshipRelation]);
    const isRelationshipBusy = friendshipActionBusy;

    const pseudo = useMemo(() => {
        if (!effectiveProfile) {
            return "User";
        }
        return effectiveProfile.pseudo || effectiveProfile.email?.split("@")[0] || "User";
    }, [effectiveProfile]);

    const memberSince = useMemo(() => formatMemberSince(effectiveProfile?.created_at), [effectiveProfile?.created_at]);

    const persistProfileState = useCallback(
        (nextProfile: UserProfile | null, nextPosts: ProfilePost[]) => {
            upsertProfileCacheEntry(cacheScope, {
                profile: nextProfile,
                posts: nextPosts,
                savedAt: Date.now(),
            });
        },
        [cacheScope],
    );

    const applyProfileLocally = useCallback(
        (nextProfile: UserProfile) => {
            setDisplayProfile(nextProfile);
            persistProfileState(nextProfile, publishedPosts);

            if (isOwnProfile && typeof userContext?.setUser === "function") {
                userContext.setUser((previous: any) => ({
                    ...(previous || {}),
                    id: nextProfile.id || previous?.id || "",
                    pseudo: nextProfile.pseudo || previous?.pseudo || "",
                    email: nextProfile.email || previous?.email || "",
                    avatar: nextProfile.avatar_url || previous?.avatar || "",
                }));
            }
        },
        [isOwnProfile, persistProfileState, publishedPosts, userContext],
    );

    const loadPublishedPosts = useCallback(
        async (targetUserId: string, options?: { silent?: boolean }) => {
            if (!options?.silent) {
                setIsPostsLoading(true);
                setPostsError(null);
            }

            try {
                const query = new URLSearchParams({
                    user_id: targetUserId,
                    limit: "30",
                    offset: "0",
                    include_self: "true",
                    friend_only: "false",
                    sort_by: "created_at",
                    order: "desc",
                });

                const rawPosts = await executePostsRequest({
                    url: `/api/posts?${query.toString()}`,
                    method: "GET",
                    useToken: true,
                });

                const posts = Array.isArray(rawPosts) ? rawPosts : [];
                posts.forEach((post) => cachePost(post));
                setPublishedPosts(posts);
                persistProfileState(effectiveProfile, posts);
            } catch {
                if (!options?.silent) {
                    setPublishedPosts([]);
                    setPostsError("Unable to load published posts.");
                }
            } finally {
                if (!options?.silent) {
                    setIsPostsLoading(false);
                }
            }
        },
        [effectiveProfile, executePostsRequest, persistProfileState],
    );

    const loadFriendshipRelation = useCallback(
        async (targetUserId: string, options?: { silent?: boolean }) => {
            if (!targetUserId || isOwnProfile) {
                setFriendshipRelation(null);
                return;
            }

            try {
                const relations = await fetchFriendships();
                const relation = relations.find((item) => String(item.friend_user_id || "") === String(targetUserId)) || null;
                setFriendshipRelation(relation);
            } catch (relationError: any) {
                const message = relationError?.response?.data?.detail || relationError?.message;
                if (message) {
                    alertContext?.showAlert?.(false, `Failed to load friendship status: ${message}`);
                }
                setFriendshipRelation(null);
            }
        },
        [alertContext, isOwnProfile],
    );

    const refreshFriendshipRelation = useCallback(async () => {
        if (!targetProfileId || isOwnProfile) {
            setFriendshipRelation(null);
            return;
        }
        await loadFriendshipRelation(targetProfileId, { silent: true });
    }, [isOwnProfile, loadFriendshipRelation, targetProfileId]);

    const runFriendshipAction = useCallback(
        async (action: () => Promise<void>) => {
            setFriendshipActionBusy(true);
            try {
                await action();
                await refreshFriendshipRelation();
            } finally {
                setFriendshipActionBusy(false);
            }
        },
        [refreshFriendshipRelation],
    );

    const handleSendFriendRequest = useCallback(async () => {
        if (!targetProfileId) {
            return;
        }
        await runFriendshipAction(async () => {
            try {
                const createdRelation = await sendFriendRequest(targetProfileId);
                setFriendshipRelation(createdRelation || null);
                alertContext?.showAlert?.(true, "Invitation sent.");
            } catch (requestError: any) {
                const message = requestError?.response?.data?.detail || requestError?.message || "Unable to send invitation.";
                alertContext?.showAlert?.(false, message);
            }
        });
    }, [alertContext, runFriendshipAction, targetProfileId]);

    const handleAcceptInvitation = useCallback(async () => {
        if (!friendshipRelation?.id) {
            return;
        }
        await runFriendshipAction(async () => {
            try {
                const acceptedRelation = await acceptFriendRequest(friendshipRelation.id);
                setFriendshipRelation(acceptedRelation || null);
                alertContext?.showAlert?.(true, "Invitation accepted.");
            } catch (acceptError: any) {
                const message = acceptError?.response?.data?.detail || acceptError?.message || "Unable to accept invitation.";
                alertContext?.showAlert?.(false, message);
            }
        });
    }, [alertContext, friendshipRelation?.id, runFriendshipAction]);

    const handleDeleteOrCancelRelation = useCallback(
        async (successMessage: string) => {
            if (!friendshipRelation?.id) {
                return;
            }
            await runFriendshipAction(async () => {
                try {
                    await deleteFriendship(friendshipRelation.id);
                    setFriendshipRelation(null);
                    alertContext?.showAlert?.(true, successMessage);
                } catch (deleteError: any) {
                    const message = deleteError?.response?.data?.detail || deleteError?.message || "Unable to update invitation.";
                    alertContext?.showAlert?.(false, message);
                }
            });
        },
        [alertContext, friendshipRelation?.id, runFriendshipAction],
    );

    const handleBlockUser = useCallback(async () => {
        if (!targetProfileId) {
            return;
        }
        await runFriendshipAction(async () => {
            try {
                let relationId = friendshipRelation?.id || null;
                if (!relationId) {
                    const createdRelation = await sendFriendRequest(targetProfileId);
                    relationId = createdRelation.id;
                }
                if (!relationId) {
                    throw new Error("Unable to initialize relation before blocking.");
                }
                const blockedRelation = await blockFriendship(relationId);
                setFriendshipRelation(blockedRelation || null);
                alertContext?.showAlert?.(true, "User blocked.");
            } catch (blockError: any) {
                const message = blockError?.response?.data?.detail || blockError?.message || "Unable to block user.";
                alertContext?.showAlert?.(false, message);
            }
        });
    }, [alertContext, friendshipRelation?.id, runFriendshipAction, targetProfileId]);

    const handleStartConversation = useCallback(() => {
        if (!targetProfileId) {
            return;
        }
        const params = new URLSearchParams({
            start_with: targetProfileId,
            start_name: pseudo,
        });

        if (effectiveProfile?.avatar_url) {
            params.set("start_avatar", effectiveProfile.avatar_url);
        }

        navigate(`/chat?${params.toString()}`);
    }, [effectiveProfile?.avatar_url, navigate, pseudo, targetProfileId]);

    const closeTwoFaDialog = useCallback(() => {
        if (isTwoFaBusy) {
            return;
        }
        setIsTwoFaDialogOpen(false);
        setTwoFaCode("");
        setTwoFaQrCode(null);
        setTwoFaSecret("");
        setTwoFaOtpAuthUrl("");
    }, [isTwoFaBusy]);

    const loadTwoFaStatus = useCallback(async (options?: { silent?: boolean; force?: boolean }) => {
        if (!isOwnProfile) {
            setIsTwoFaEnabled(false);
            setIsTwoFaLoading(false);
            return;
        }

        const cachedStatus = options?.force ? null : readTwoFaStatusCacheEntry(twoFaCacheScope);
        if (cachedStatus) {
            setIsTwoFaEnabled(Boolean(cachedStatus.enabled));
            setIsTwoFaLoading(false);
            return;
        }

        if (!options?.silent) {
            setIsTwoFaLoading(true);
        }
        try {
            const status = await executeTwoFaStatus({
                url: "/api/2fa/status",
                method: "GET",
                useToken: true,
            });
            const enabled = Boolean(status?.enabled);
            setIsTwoFaEnabled(enabled);
            upsertTwoFaStatusCacheEntry(twoFaCacheScope, enabled);
        } catch {
            if (!cachedStatus) {
                setIsTwoFaEnabled(false);
            }
        } finally {
            if (!options?.silent) {
                setIsTwoFaLoading(false);
            }
        }
    }, [executeTwoFaStatus, isOwnProfile, twoFaCacheScope]);

    const handleEnableTwoFa = useCallback(async () => {
        setIsTwoFaBusy(true);
        try {
            const response = await executeTwoFaEnable({
                url: "/api/2fa/enable",
                method: "POST",
                useToken: true,
            });
            const rawQrCode = String(response?.qr_code || "").trim();
            if (!rawQrCode) {
                throw new Error("QR code is missing in 2FA setup response.");
            }
            const qrImage = rawQrCode.startsWith("data:image")
                ? rawQrCode
                : `data:image/png;base64,${rawQrCode}`;
            setTwoFaQrCode(qrImage);
            setTwoFaSecret(String(response?.secret || "").trim());
            setTwoFaOtpAuthUrl(String(response?.otpauth_url || "").trim());
            setTwoFaCode("");
            setIsTwoFaDialogOpen(true);
        } catch (twoFaError: any) {
            const message = twoFaError?.message || "Unable to initialize 2FA.";
            alertContext?.showAlert?.(false, message);
        } finally {
            setIsTwoFaBusy(false);
        }
    }, [alertContext, executeTwoFaEnable]);

    const handleVerifyTwoFa = useCallback(async () => {
        const normalizedCode = twoFaCode.trim();
        if (!/^\d{6}$/.test(normalizedCode)) {
            alertContext?.showAlert?.(false, "Enter a valid 6-digit code.");
            return;
        }

        setIsTwoFaBusy(true);
        try {
            await executeTwoFaVerify({
                url: "/api/2fa/verify",
                method: "POST",
                useToken: true,
                body: { code: normalizedCode } as any,
            });
            setIsTwoFaEnabled(true);
            upsertTwoFaStatusCacheEntry(twoFaCacheScope, true);
            setIsTwoFaDialogOpen(false);
            setTwoFaCode("");
            setTwoFaQrCode(null);
            setTwoFaSecret("");
            setTwoFaOtpAuthUrl("");
            alertContext?.showAlert?.(true, "Two-factor authentication enabled.");
        } catch (verifyError: any) {
            const message = verifyError?.message || "Unable to verify 2FA code.";
            alertContext?.showAlert?.(false, message);
        } finally {
            setIsTwoFaBusy(false);
        }
    }, [alertContext, executeTwoFaVerify, twoFaCode]);

    const handleDisableTwoFa = useCallback(async () => {
        setIsTwoFaBusy(true);
        try {
            await executeTwoFaDisable({
                url: "/api/2fa/disable",
                method: "POST",
                useToken: true,
            });
            setIsTwoFaEnabled(false);
            upsertTwoFaStatusCacheEntry(twoFaCacheScope, false);
            setTwoFaCode("");
            setTwoFaQrCode(null);
            setTwoFaSecret("");
            setTwoFaOtpAuthUrl("");
            setIsTwoFaDialogOpen(false);
            alertContext?.showAlert?.(true, "Two-factor authentication disabled.");
        } catch (disableError: any) {
            const message = disableError?.message || "Unable to disable 2FA.";
            alertContext?.showAlert?.(false, message);
        } finally {
            setIsTwoFaBusy(false);
        }
    }, [alertContext, executeTwoFaDisable, twoFaCacheScope]);

    const handleLogout = useCallback(() => {
        authContext?.logout?.();
        navigate("/login", { replace: true });
    }, [authContext, navigate]);

    const uploadMediaAndPatchProfile = useCallback(
        async (target: "avatar" | "cover", file: File, postDescription: string) => {
            const setUploading = target === "avatar" ? setIsAvatarUploading : setIsCoverUploading;
            const setUploadProgress = target === "avatar" ? setAvatarUploadProgress : setCoverUploadProgress;
            setUploading(true);
            setUploadProgress(0);

            try {
                const formData = new FormData();
                formData.append("file", file);

                const uploadResult = await executeUpload({
                    url: "/api/files/upload",
                    method: "POST",
                    useToken: true,
                    body: formData as any
                });

                const mediaId = uploadResult?.media_id || uploadResult?.id;
                if (!mediaId) {
                    throw new Error("Upload succeeded but media id is missing.");
                }
                const uploadedMediaUrl = withCacheBuster(uploadResult?.url || uploadResult?.preview_url, mediaId);

                if (effectiveProfile) {
                    const optimisticProfile: UserProfile = {
                        ...effectiveProfile,
                        avatar_id: target === "avatar" ? mediaId : effectiveProfile.avatar_id,
                        cover_id: target === "cover" ? mediaId : effectiveProfile.cover_id,
                        avatar_url: target === "avatar" ? (uploadedMediaUrl || effectiveProfile.avatar_url) : effectiveProfile.avatar_url,
                        cover_url: target === "cover" ? (uploadedMediaUrl || effectiveProfile.cover_url) : effectiveProfile.cover_url,
                        updated_at: new Date().toISOString(),
                    };
                    applyProfileLocally(optimisticProfile);
                }

                const payload = target === "avatar" ? { avatar_id: mediaId } : { cover_id: mediaId };
                const updatedProfile = await executeProfileUpdate({
                    url: "/api/user/me",
                    method: "PATCH",
                    useToken: true,
                    body: payload as any,
                });

                if (!updatedProfile) {
                    throw new Error("Profile update returned no data.");
                }

                const normalizedUpdatedProfile: UserProfile = {
                    ...updatedProfile,
                    avatar_url:
                        target === "avatar"
                            ? uploadedMediaUrl || updatedProfile.avatar_url
                            : updatedProfile.avatar_url,
                    cover_url:
                        target === "cover"
                            ? uploadedMediaUrl || updatedProfile.cover_url
                            : updatedProfile.cover_url,
                };

                applyProfileLocally(normalizedUpdatedProfile);

                try {
                    const freshProfile = await executeProfileFetch({
                        url: "/api/user/me",
                        method: "GET",
                        useToken: true,
                    });
                    if (freshProfile?.id) {
                        const freshNormalized: UserProfile = {
                            ...freshProfile,
                            avatar_url:
                                target === "avatar"
                                    ? uploadedMediaUrl || freshProfile.avatar_url
                                    : freshProfile.avatar_url,
                            cover_url:
                                target === "cover"
                                    ? uploadedMediaUrl || freshProfile.cover_url
                                    : freshProfile.cover_url,
                        };
                        applyProfileLocally(freshNormalized);
                    }
                } catch {
                    // Keep optimistic/server PATCH state if follow-up GET fails.
                }

                try {
                    const normalizedPostDescription = postDescription.trim();
                    const createdPost = await executeCreatePost({
                        url: "/api/posts",
                        method: "POST",
                        useToken: true,
                        body: {
                            content: normalizedPostDescription || null,
                            media_id: mediaId,
                        } as any,
                    });

                    if (createdPost?.id) {
                        cachePost(createdPost);
                        setPublishedPosts((previous) => {
                            const deduped = previous.filter((post) => post.id !== createdPost.id);
                            const nextPosts = [createdPost as ProfilePost, ...deduped];
                            persistProfileState(normalizedUpdatedProfile, nextPosts);
                            return nextPosts;
                        });
                        invalidateAndNotifyPostCache();
                    }
                } catch {
                    // Keep profile update successful even if the post creation fails.
                }

                if (normalizedUpdatedProfile.id) {
                    void loadPublishedPosts(normalizedUpdatedProfile.id);
                }

                alertContext?.showAlert?.(true, target === "avatar" ? "Profile photo updated." : "Cover photo updated.");
            } catch (uploadError: any) {
                const message = uploadError?.message || "Failed to update image.";
                alertContext?.showAlert?.(false, message);
            } finally {
                setUploading(false);
                setUploadProgress(0);
            }
        },
        [
            alertContext,
            applyProfileLocally,
            executeCreatePost,
            executeProfileFetch,
            executeProfileUpdate,
            executeUpload,
            effectiveProfile,
            loadPublishedPosts,
            persistProfileState,
        ],
    );

    const handleAvatarFileChange = async (event: ChangeEvent<HTMLInputElement>): Promise<void> => {
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }
        setPendingMediaUpload({ target: "avatar", file });
        setMediaPostDescription("");
        event.target.value = "";
    };

    const handleCoverFileChange = async (event: ChangeEvent<HTMLInputElement>): Promise<void> => {
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }
        setPendingMediaUpload({ target: "cover", file });
        setMediaPostDescription("");
        event.target.value = "";
    };

    const closeMediaUploadDialog = useCallback(() => {
        if (isMediaUploadDialogBusy || isAvatarUploading || isCoverUploading) {
            return;
        }
        setPendingMediaUpload(null);
        setMediaPostDescription("");
    }, [isAvatarUploading, isCoverUploading, isMediaUploadDialogBusy]);

    const confirmMediaUpload = useCallback(async (): Promise<void> => {
        if (!pendingMediaUpload) {
            return;
        }

        setIsMediaUploadDialogBusy(true);
        try {
            await uploadMediaAndPatchProfile(
                pendingMediaUpload.target,
                pendingMediaUpload.file,
                mediaPostDescription,
            );
            setPendingMediaUpload(null);
            setMediaPostDescription("");
        } catch {
            // Keep dialog open so user can retry.
        } finally {
            setIsMediaUploadDialogBusy(false);
        }
    }, [mediaPostDescription, pendingMediaUpload, uploadMediaAndPatchProfile]);

    const saveProfileChanges = async (): Promise<void> => {
        const payload = {
            pseudo: editForm.pseudo.trim(),
            bio: editForm.bio.trim() || null,
            address: editForm.address.trim() || null,
        };

        if (!payload.pseudo) {
            alertContext?.showAlert?.(false, "Display name cannot be empty.");
            return;
        }

        setIsSavingProfile(true);
        try {
            const updatedProfile = await executeProfileUpdate({
                url: "/api/user/me",
                method: "PATCH",
                useToken: true,
                body: payload as any,
            });

            if (!updatedProfile) {
                throw new Error("Profile update returned no data.");
            }

            applyProfileLocally(updatedProfile);
            setIsEditDialogOpen(false);
            alertContext?.showAlert?.(true, "Profile updated successfully.");
        } catch (saveError: any) {
            const message = saveError?.message || "Failed to update profile.";
            alertContext?.showAlert?.(false, message);
        } finally {
            setIsSavingProfile(false);
        }
    };

    useEffect(() => {
        if (cachedEntry) {
            setDisplayProfile(cachedEntry.profile);
            setPublishedPosts(cachedEntry.posts || []);
            setIsPostsLoading(false);
            setPostsError(null);
        } else {
            setDisplayProfile(null);
            setPublishedPosts([]);
            setIsPostsLoading(true);
            setPostsError(null);
        }
    }, [cacheScope, cachedEntry]);

    useEffect(() => {
        if (!profile) {
            return;
        }
        setDisplayProfile((previous) => {
            if (!previous || previous.id !== profile.id) {
                return profile;
            }

            const previousStamp = Date.parse(previous.updated_at || previous.created_at || "");
            const nextStamp = Date.parse(profile.updated_at || profile.created_at || "");
            if (!Number.isNaN(previousStamp) && !Number.isNaN(nextStamp) && previousStamp > nextStamp) {
                return previous;
            }

            return profile;
        });
    }, [profile]);

    useEffect(() => {
        persistProfileState(displayProfile, publishedPosts);
    }, [displayProfile, persistProfileState, publishedPosts]);

    useEffect(() => {
        if (!effectiveProfile?.id) {
            return;
        }

        const hasCachedEntry = Boolean(cachedEntry);
        if (hasCachedEntry) {
            void loadPublishedPosts(effectiveProfile.id, { silent: true });
            return;
        }

        void loadPublishedPosts(effectiveProfile.id, { silent: false });
    }, [cachedEntry, effectiveProfile?.id, loadPublishedPosts]);

    useEffect(() => {
        if (!targetProfileId || isOwnProfile) {
            setFriendshipRelation(null);
            return;
        }
        void loadFriendshipRelation(targetProfileId);
    }, [isOwnProfile, loadFriendshipRelation, targetProfileId]);

    useEffect(() => {
        if (!targetProfileId || isOwnProfile) {
            return;
        }

        const handleFriendshipInvitationsUpdated = (): void => {
            void loadFriendshipRelation(targetProfileId, { silent: true });
        };

        window.addEventListener(friendshipInvitationsUpdatedEventName, handleFriendshipInvitationsUpdated as EventListener);
        return () => {
            window.removeEventListener(friendshipInvitationsUpdatedEventName, handleFriendshipInvitationsUpdated as EventListener);
        };
    }, [isOwnProfile, loadFriendshipRelation, targetProfileId]);

    useEffect(() => {
        if (!isOwnProfile) {
            setIsTwoFaEnabled(false);
            setIsTwoFaLoading(false);
            return;
        }
        const cachedStatus = readTwoFaStatusCacheEntry(twoFaCacheScope);
        if (cachedStatus) {
            setIsTwoFaEnabled(Boolean(cachedStatus.enabled));
            setIsTwoFaLoading(false);
        }
    }, [isOwnProfile, twoFaCacheScope]);

    useEffect(() => {
        if (!effectiveProfile?.id || !isOwnProfile) {
            return;
        }
        void loadTwoFaStatus({ silent: true });
    }, [effectiveProfile?.id, isOwnProfile, loadTwoFaStatus]);

    useEffect(() => {
        setIsRelationMenuOpen(false);
        setIsOwnMenuOpen(false);
    }, [targetProfileId]);

    useEffect(() => {
        if (!isRelationMenuOpen) {
            return;
        }

        const closeMenuOnOutsideClick = (event: MouseEvent): void => {
            const eventTarget = event.target;
            if (!(eventTarget instanceof Node)) {
                return;
            }

            if (relationMenuRef.current && !relationMenuRef.current.contains(eventTarget)) {
                setIsRelationMenuOpen(false);
            }
        };

        document.addEventListener("mousedown", closeMenuOnOutsideClick);
        return () => {
            document.removeEventListener("mousedown", closeMenuOnOutsideClick);
        };
    }, [isRelationMenuOpen]);

    useEffect(() => {
        if (!isOwnMenuOpen) {
            return;
        }

        const closeMenuOnOutsideClick = (event: MouseEvent): void => {
            const eventTarget = event.target;
            if (!(eventTarget instanceof Node)) {
                return;
            }

            if (ownMenuRef.current && !ownMenuRef.current.contains(eventTarget)) {
                setIsOwnMenuOpen(false);
            }
        };

        document.addEventListener("mousedown", closeMenuOnOutsideClick);
        return () => {
            document.removeEventListener("mousedown", closeMenuOnOutsideClick);
        };
    }, [isOwnMenuOpen]);

    useEffect(() => {
        if (!isEditDialogOpen) {
            return;
        }
        setEditForm(toFormState(effectiveProfile));
    }, [effectiveProfile, isEditDialogOpen]);

    const showLoader = isLoading && !effectiveProfile;
    if (showLoader) {
        return (
            <Flex w="100%" h="calc(100vh - 80px)" alignItems="center" justifyContent="center">
                <Spinner size="xl" color="primary" />
            </Flex>
        );
    }

    if (!effectiveProfile || (!effectiveProfile && error)) {
        return (
            <Flex
                w="100%"
                h="calc(100vh - 80px)"
                alignItems="center"
                justifyContent="center"
                flexDirection="column"
                gap={3}
                px={4}
                textAlign="center"
            >
                <Text className="title-styles" fontSize="xl" fontWeight="900" color="error">
                    Unable to load profile
                </Text>
                <Text className="text-styles" fontWeight="700">
                    {error || "Profile not found."}
                </Text>
            </Flex>
        );
    }

    return (
        <Flex
            w="100%"
            minH="calc(100vh - 80px)"
            justifyContent="center"
            px={{ base: 2, md: 6 }}
            pb={{ base: 8, md: 10 }}
            bg="radial-gradient(circle at top right, rgba(112,205,75,0.24), transparent 36%), radial-gradient(circle at top left, rgba(112,205,75,0.14), transparent 34%), linear-gradient(180deg, #2a3135 0%, #26272d 42%, #20252a 100%)"
            overflowX="hidden"
        >
            <input
                ref={avatarInputRef}
                type="file"
                accept="image/*"
                style={{ display: "none" }}
                onChange={(event) => void handleAvatarFileChange(event)}
            />
            <input
                ref={coverInputRef}
                type="file"
                accept="image/*"
                style={{ display: "none" }}
                onChange={(event) => void handleCoverFileChange(event)}
            />

            <Box w="100%" maxW="1180px" animation={`${riseIn} 0.6s ease-out both`} overflow="visible">
                <Box
                    h={{ base: "180px", md: "320px" }}
                    borderBottomRadius={{ base: "2xl", md: "3xl" }}
                    position="relative"
                    overflow="hidden"
                    border="1px solid rgba(255,255,255,0.16)"
                    backgroundImage={
                        effectiveProfile.cover_url
                            ? `linear-gradient(180deg, rgba(0,0,0,0.15), rgba(0,0,0,0.55)), url(${effectiveProfile.cover_url})`
                            : "linear-gradient(135deg, #70cd4b 0%, #5fb541 45%, #8adf62 100%)"
                    }
                    backgroundSize="cover"
                    backgroundPosition="center"
                    cursor={effectiveProfile.cover_url ? "pointer" : "default"}
                    onClick={() => effectiveProfile.cover_url && setPreviewTarget("cover")}
                >
                    <Box
                        position="absolute"
                        top="-35px"
                        right="-35px"
                        w="140px"
                        h="140px"
                        borderRadius="full"
                        bg="rgba(255,255,255,0.17)"
                    />
                    <Box
                        position="absolute"
                        bottom="-46px"
                        left="-20px"
                        w="170px"
                        h="170px"
                        borderRadius="full"
                        bg="rgba(255,255,255,0.1)"
                    />

                    {isOwnProfile && (
                        <Button
                            position="absolute"
                            right={{ base: 3, md: 5 }}
                            top={{ base: 3, md: 5 }}
                            size={{ base: "sm", md: "md" }}
                            maxW={{ base: "calc(100% - 24px)", md: "none" }}
                            bg="rgba(20,20,20,0.58)"
                            color="white"
                            borderRadius="full"
                            _hover={{ bg: "rgba(20,20,20,0.75)" }}
                            disabled={isCoverUploading}
                            onClick={(event) => {
                                event.stopPropagation();
                                coverInputRef.current?.click();
                            }}
                        >
                            <HStack gap={2}>
                                <LuImagePlus />
                                <Text className="text-styles" fontSize="sm" fontWeight="700" lineClamp={1}>
                                    {isCoverUploading
                                        ? `Uploading... ${Math.max(0, Math.min(100, coverUploadProgress))}%`
                                        : "Change cover"}
                                </Text>
                            </HStack>
                        </Button>
                    )}

                    {isCoverUploading && (
                        <Box position="absolute" left={4} right={4} bottom={4}>
                            <HStack justifyContent="space-between" mb={1}>
                                <Text className="text-styles" fontSize="xs" fontWeight="800" color="rgba(255,255,255,0.9)">
                                    Cover upload
                                </Text>
                                <Text className="text-styles" fontSize="xs" fontWeight="900" color="white">
                                    {Math.max(0, Math.min(100, coverUploadProgress))}%
                                </Text>
                            </HStack>
                            <Box w="100%" h="6px" borderRadius="full" bg="rgba(255,255,255,0.25)" overflow="hidden">
                                <Box
                                    h="100%"
                                    bg="white"
                                    w={`${Math.max(0, Math.min(100, coverUploadProgress))}%`}
                                    transition="width 0.2s ease"
                                />
                            </Box>
                        </Box>
                    )}
                </Box>

                <Box
                    mx={{ base: 2, md: 8 }}
                    mt={{ base: "-56px", md: "-72px" }}
                    px={{ base: 4, md: 7 }}
                    py={{ base: 5, md: 6 }}
                    borderRadius="2xl"
                    border="1px solid rgba(255,255,255,0.18)"
                    bg="linear-gradient(140deg, rgba(21,29,39,0.97), rgba(34,45,61,0.95))"
                    boxShadow="0 18px 48px rgba(0,0,0,0.33)"
                    position="relative"
                    zIndex={2}
                    overflow="visible"
                >
                    <Flex
                        direction={{ base: "column", xl: "row" }}
                        justifyContent="space-between"
                        alignItems={{ base: "stretch", xl: "end" }}
                        gap={{ base: 4, md: 5 }}
                    >
                        <Flex
                            direction={{ base: "column", sm: "row" }}
                            alignItems={{ base: "start", sm: "end" }}
                            gap={{ base: 3, md: 4 }}
                            minW={0}
                            flex={1}
                        >
                            <Box position="relative">
                                <Avatar.Root
                                    w={{ base: "110px", sm: "124px", md: "144px" }}
                                    h={{ base: "110px", sm: "124px", md: "144px" }}
                                    border="4px solid"
                                    borderColor="rgba(61,71,74,0.95)"
                                    boxShadow="0 8px 24px rgba(0,0,0,0.36)"
                                    cursor={effectiveProfile.avatar_url ? "pointer" : "default"}
                                    onClick={() => effectiveProfile.avatar_url && setPreviewTarget("avatar")}
                                >
                                    <Avatar.Fallback name={pseudo} />
                                    {effectiveProfile.avatar_url && <Avatar.Image src={effectiveProfile.avatar_url} />}
                                </Avatar.Root>

                                {isOwnProfile && (
                                    <Button
                                        position="absolute"
                                        right="-6px"
                                        bottom="-6px"
                                        size="sm"
                                        borderRadius="full"
                                        bg="primary"
                                        color="secondary"
                                        _hover={{ opacity: 0.9 }}
                                        disabled={isAvatarUploading}
                                        onClick={(event) => {
                                            event.stopPropagation();
                                            avatarInputRef.current?.click();
                                        }}
                                    >
                                        {isAvatarUploading ? `${Math.max(0, Math.min(100, avatarUploadProgress))}%` : <LuPencil />}
                                    </Button>
                                )}
                            </Box>

                            <VStack align="start" gap={1} pb={{ base: 0, sm: 1 }} minW={0} w="100%">
                                <Text
                                    className="title-styles"
                                    fontSize={{ base: "2xl", md: "3xl" }}
                                    fontWeight="900"
                                    wordBreak="break-word"
                                    overflowWrap="anywhere"
                                >
                                    {pseudo}
                                </Text>
                                <HStack gap={2} color="rgba(229,231,235,0.88)" minW={0}>
                                    <LuMail size={14} />
                                    <Text className="text-styles" wordBreak="break-word" overflowWrap="anywhere">
                                        {effectiveProfile.email || "No email provided"}
                                    </Text>
                                </HStack>
                                <HStack gap={2} color="rgba(229,231,235,0.78)" flexWrap="wrap">
                                    <LuCalendarDays size={15} />
                                    <Text className="text-styles" fontSize="sm">
                                        Member since {memberSince}
                                    </Text>
                                </HStack>
                                {isAvatarUploading && (
                                    <Box w="100%" maxW="260px" pt={1}>
                                        <HStack justifyContent="space-between" mb={1}>
                                            <Text className="text-styles" fontSize="xs" fontWeight="800" color="rgba(229,231,235,0.88)">
                                                Profile photo upload
                                            </Text>
                                            <Text className="text-styles" fontSize="xs" fontWeight="900" color="primary">
                                                {Math.max(0, Math.min(100, avatarUploadProgress))}%
                                            </Text>
                                        </HStack>
                                        <Box w="100%" h="6px" borderRadius="full" bg="rgba(229,231,235,0.18)" overflow="hidden">
                                            <Box
                                                h="100%"
                                                bg="primary"
                                                w={`${Math.max(0, Math.min(100, avatarUploadProgress))}%`}
                                                transition="width 0.2s ease"
                                            />
                                        </Box>
                                    </Box>
                                )}
                            </VStack>
                        </Flex>

                        <Flex
                            gap={3}
                            wrap="wrap"
                            minW={0}
                            w={{ base: "100%", xl: "auto" }}
                            justifyContent={{ base: "flex-start", xl: "flex-end" }}
                        >
                            {isOwnProfile ? (
                                <>
                                    <Button
                                        bg="primary"
                                        _hover={{ opacity: 0.9 }}
                                        borderRadius="xl"
                                        color="secondary"
                                        onClick={() => setIsEditDialogOpen(true)}
                                        flex={{ base: "1 1 170px", sm: "0 0 auto" }}
                                    >
                                        <HStack gap={2}>
                                            <LuPencil />
                                            <Text className="text-styles" fontWeight="700">
                                                Edit profile
                                            </Text>
                                        </HStack>
                                    </Button>
                                    <Box
                                        ref={ownMenuRef}
                                        position="relative"
                                        flex={{ base: "0 0 auto", sm: "0 0 auto" }}
                                        minW={{ base: "44px", sm: "auto" }}
                                        zIndex={isOwnMenuOpen ? 2600 : 1}
                                    >
                                        <Button
                                            bg="rgba(255,255,255,0.11)"
                                            _hover={{ bg: "rgba(255,255,255,0.2)" }}
                                            borderRadius="xl"
                                            minW={{ base: "44px", sm: "56px" }}
                                            px={{ base: 0, sm: 3 }}
                                            disabled={isTwoFaBusy || isTwoFaLoading}
                                            onClick={() => setIsOwnMenuOpen((previous) => !previous)}
                                        >
                                            <LuEllipsis />
                                        </Button>

                                        {isOwnMenuOpen && (
                                            <VStack
                                                position="absolute"
                                                top="calc(100% + 8px)"
                                                right={0}
                                                align="stretch"
                                                gap={2}
                                                p={2}
                                                borderRadius="xl"
                                                bg="rgba(20,24,31,0.98)"
                                                border="1px solid rgba(255,255,255,0.14)"
                                                boxShadow="0 18px 36px rgba(0,0,0,0.42)"
                                                minW="210px"
                                                zIndex={3000}
                                            >
                                                <Button
                                                    justifyContent="flex-start"
                                                    bg="rgba(255,255,255,0.08)"
                                                    _hover={{ bg: "rgba(255,255,255,0.16)" }}
                                                    borderRadius="lg"
                                                    disabled={isTwoFaBusy}
                                                    onClick={() => {
                                                        setIsOwnMenuOpen(false);
                                                        if (isTwoFaEnabled) {
                                                            void handleDisableTwoFa();
                                                            return;
                                                        }
                                                        void handleEnableTwoFa();
                                                    }}
                                                >
                                                    <Text className="text-styles" fontWeight="700">
                                                        {isTwoFaEnabled ? "Disable 2FA" : "Enable 2FA"}
                                                    </Text>
                                                </Button>
                                                <Button
                                                    justifyContent="flex-start"
                                                    bg="rgba(255,85,85,0.2)"
                                                    _hover={{ bg: "rgba(255,85,85,0.3)" }}
                                                    borderRadius="lg"
                                                    color="#ffd7d7"
                                                    onClick={() => {
                                                        setIsOwnMenuOpen(false);
                                                        handleLogout();
                                                    }}
                                                >
                                                    <Text className="text-styles" fontWeight="700">
                                                        Logout
                                                    </Text>
                                                </Button>
                                            </VStack>
                                        )}
                                    </Box>
                                </>
                            ) : (
                                <>
                                    <Button
                                        bg="rgba(255,255,255,0.11)"
                                        _hover={{ bg: "rgba(255,255,255,0.2)" }}
                                        borderRadius="xl"
                                        flex={{ base: "1 1 170px", sm: "0 0 auto" }}
                                        disabled={isRelationshipBusy || friendshipState === "blocked"}
                                        onClick={() => void handleStartConversation()}
                                    >
                                        <HStack gap={2}>
                                            <LuMessageCircle />
                                            <Text className="text-styles" fontWeight="700">
                                                Message
                                            </Text>
                                        </HStack>
                                    </Button>

                                    {friendshipState === "none" && (
                                        <Button
                                            bg="primary"
                                            _hover={{ opacity: 0.9 }}
                                            borderRadius="xl"
                                            color="secondary"
                                            flex={{ base: "1 1 170px", sm: "0 0 auto" }}
                                            disabled={isRelationshipBusy}
                                            onClick={() => void handleSendFriendRequest()}
                                        >
                                            <HStack gap={2}>
                                                <LuUserPlus />
                                                <Text className="text-styles" fontWeight="700">
                                                    Send invitation
                                                </Text>
                                            </HStack>
                                        </Button>
                                    )}

                                    {friendshipState === "pending_outgoing" && (
                                        <Button
                                            bg="rgba(255,255,255,0.11)"
                                            _hover={{ bg: "rgba(255,255,255,0.2)" }}
                                            borderRadius="xl"
                                            flex={{ base: "1 1 170px", sm: "0 0 auto" }}
                                            disabled={isRelationshipBusy}
                                            onClick={() => void handleDeleteOrCancelRelation("Invitation canceled.")}
                                        >
                                            <HStack gap={2}>
                                                <LuUserMinus />
                                                <Text className="text-styles" fontWeight="700">
                                                    Cancel invitation
                                                </Text>
                                            </HStack>
                                        </Button>
                                    )}

                                    {friendshipState === "pending_incoming" && (
                                        <>
                                            <Button
                                                bg="primary"
                                                _hover={{ opacity: 0.9 }}
                                                borderRadius="xl"
                                                color="secondary"
                                                flex={{ base: "1 1 170px", sm: "0 0 auto" }}
                                                disabled={isRelationshipBusy}
                                                onClick={() => void handleAcceptInvitation()}
                                            >
                                                <HStack gap={2}>
                                                    <LuUserPlus />
                                                    <Text className="text-styles" fontWeight="700">
                                                        Accept invitation
                                                    </Text>
                                                </HStack>
                                            </Button>
                                            <Button
                                                bg="rgba(255,255,255,0.11)"
                                                _hover={{ bg: "rgba(255,255,255,0.2)" }}
                                                borderRadius="xl"
                                                flex={{ base: "1 1 170px", sm: "0 0 auto" }}
                                                disabled={isRelationshipBusy}
                                                onClick={() => void handleDeleteOrCancelRelation("Invitation declined.")}
                                            >
                                                <HStack gap={2}>
                                                    <LuUserMinus />
                                                    <Text className="text-styles" fontWeight="700">
                                                        Decline invitation
                                                    </Text>
                                                </HStack>
                                            </Button>
                                        </>
                                    )}

                                    <Box
                                        ref={relationMenuRef}
                                        position="relative"
                                        flex={{ base: "0 0 auto", sm: "0 0 auto" }}
                                        minW={{ base: "44px", sm: "auto" }}
                                        zIndex={isRelationMenuOpen ? 2600 : 1}
                                    >
                                        <Button
                                            bg="rgba(255,255,255,0.11)"
                                            _hover={{ bg: "rgba(255,255,255,0.2)" }}
                                            borderRadius="xl"
                                            minW={{ base: "44px", sm: "56px" }}
                                            px={{ base: 0, sm: 3 }}
                                            disabled={isRelationshipBusy}
                                            onClick={() => setIsRelationMenuOpen((previous) => !previous)}
                                        >
                                            <LuEllipsis />
                                        </Button>

                                        {isRelationMenuOpen && (
                                            <VStack
                                                position="absolute"
                                                top="calc(100% + 8px)"
                                                right={0}
                                                align="stretch"
                                                gap={2}
                                                p={2}
                                                borderRadius="xl"
                                                bg="rgba(20,24,31,0.98)"
                                                border="1px solid rgba(255,255,255,0.14)"
                                                boxShadow="0 18px 36px rgba(0,0,0,0.42)"
                                                minW="210px"
                                                zIndex={3000}
                                            >
                                                {friendshipState === "accepted" && (
                                                    <Button
                                                        justifyContent="flex-start"
                                                        bg="rgba(255,255,255,0.08)"
                                                        _hover={{ bg: "rgba(255,255,255,0.16)" }}
                                                        borderRadius="lg"
                                                        disabled={isRelationshipBusy}
                                                        onClick={() => {
                                                            setIsRelationMenuOpen(false);
                                                            void handleDeleteOrCancelRelation("Friend removed.");
                                                        }}
                                                    >
                                                        <HStack gap={2}>
                                                            <LuUserMinus />
                                                            <Text className="text-styles" fontWeight="700">
                                                                Remove friend
                                                            </Text>
                                                        </HStack>
                                                    </Button>
                                                )}

                                                {friendshipState === "blocked" ? (
                                                    <Button
                                                        justifyContent="flex-start"
                                                        bg="rgba(255,85,85,0.18)"
                                                        _hover={{ bg: "rgba(255,85,85,0.28)" }}
                                                        borderRadius="lg"
                                                        color="#ffc5c5"
                                                        disabled={isRelationshipBusy}
                                                        onClick={() => {
                                                            setIsRelationMenuOpen(false);
                                                            void handleDeleteOrCancelRelation("Blocked relation removed.");
                                                        }}
                                                    >
                                                        <HStack gap={2}>
                                                            <LuBan />
                                                            <Text className="text-styles" fontWeight="700">
                                                                Remove block
                                                            </Text>
                                                        </HStack>
                                                    </Button>
                                                ) : (
                                                    <Button
                                                        justifyContent="flex-start"
                                                        bg="rgba(255,85,85,0.18)"
                                                        _hover={{ bg: "rgba(255,85,85,0.28)" }}
                                                        borderRadius="lg"
                                                        color="#ffc5c5"
                                                        disabled={isRelationshipBusy}
                                                        onClick={() => {
                                                            setIsRelationMenuOpen(false);
                                                            void handleBlockUser();
                                                        }}
                                                    >
                                                        <HStack gap={2}>
                                                            <LuBan />
                                                            <Text className="text-styles" fontWeight="700">
                                                                Block user
                                                            </Text>
                                                        </HStack>
                                                    </Button>
                                                )}
                                            </VStack>
                                        )}
                                    </Box>

                                </>
                            )}
                        </Flex>
                    </Flex>

                </Box>

                <Grid
                    templateColumns={{ base: "1fr", lg: "320px 1fr" }}
                    gap={5}
                    mt={5}
                    px={{ base: 4, md: 8 }}
                    overflow="hidden"
                >
                    <VStack align="stretch" gap={5} animation={`${slideIn} 0.55s ease-out both`}>
                        <Box
                            borderRadius="2xl"
                            bg="rgba(20,24,31,0.86)"
                            border="1px solid rgba(255,255,255,0.12)"
                            p={5}
                            overflow="hidden"
                        >
                            <Text className="title-styles" fontSize="lg" fontWeight="900" mb={3}>
                                About
                            </Text>
                            <Text className="text-styles" color="rgba(229,231,235,0.9)" wordBreak="break-word">
                                {effectiveProfile.bio || "No bio yet. Add a short intro to make your profile stand out."}
                            </Text>
                        </Box>

                        <Box
                            borderRadius="2xl"
                            bg="rgba(20,24,31,0.86)"
                            border="1px solid rgba(255,255,255,0.12)"
                            p={5}
                            overflow="hidden"
                        >
                            <Text className="title-styles" fontSize="lg" fontWeight="900" mb={3}>
                                Details
                            </Text>
                            <VStack align="start" gap={3}>
                                <HStack gap={2} color="rgba(229,231,235,0.86)">
                                    <LuMapPin size={16} />
                                    <Text className="text-styles" wordBreak="break-word" overflowWrap="anywhere">
                                        {effectiveProfile.address || "Address not provided"}
                                    </Text>
                                </HStack>
                                <HStack gap={2} color="rgba(229,231,235,0.86)" minW={0}>
                                    <LuMail size={16} />
                                    <Text className="text-styles" wordBreak="break-word" overflowWrap="anywhere">
                                        {effectiveProfile.email || "Email not provided"}
                                    </Text>
                                </HStack>
                                <HStack gap={2} color="rgba(229,231,235,0.86)">
                                    <LuCalendarDays size={16} />
                                    <Text className="text-styles">Joined in {memberSince}</Text>
                                </HStack>
                            </VStack>
                        </Box>
                    </VStack>

                    <VStack id="profile-posts-section" align="stretch" gap={4} minW={0}>
                        <Box
                            borderRadius="2xl"
                            bg="rgba(20,24,31,0.86)"
                            border="1px solid rgba(255,255,255,0.12)"
                            p={5}
                            animation={`${riseIn} 0.6s ease-out both`}
                            animationDelay="0.12s"
                            overflow="hidden"
                        >
                            <HStack justifyContent="space-between" mb={3} flexWrap="wrap" gap={2}>
                                <Text className="title-styles" fontSize="lg" fontWeight="900">
                                    Published posts
                                </Text>
                                <Text className="text-styles" color="rgba(229,231,235,0.8)">
                                    {publishedPosts.length}
                                </Text>
                            </HStack>

                            {isPostsLoading ? (
                                <Flex py={8} justifyContent="center">
                                    <Spinner size="md" color="primary" />
                                </Flex>
                            ) : postsError ? (
                                <Text className="text-styles" color="error">
                                    {postsError}
                                </Text>
                            ) : publishedPosts.length === 0 ? (
                                <Text className="text-styles" color="rgba(229,231,235,0.8)">
                                    No posts published yet.
                                </Text>
                            ) : (
                                <VStack align="stretch" gap={4}>
                                    {publishedPosts.map((post: any) => {
                                        const newPost: PostData = {
                                            id: post.id,
                                            image: post.media_url,
                                            content: post.content,
                                            createdAt: post.created_at,
                                            authorId: post.user_id,
                                            authorPseudonym: post.author_pseudo,
                                            authorAvatar: post.author_avatar_url,
                                            comments: post.comment_count,
                                            likes: post.like_count,
                                            likedByMe: post.liked_by_me
                                        }
                                        
                                        return <PostCard key={post.id} post={newPost} />;
                                    })}
                                </VStack>
                            )}
                        </Box>
                    </VStack>
                </Grid>
            </Box>

            <Dialog.Root open={isEditDialogOpen} onOpenChange={(event) => setIsEditDialogOpen(event.open)} placement="center">
                <Dialog.Positioner>
                    <Dialog.Content
                        bg="variantSecondary"
                        border="1px solid rgba(255,255,255,0.16)"
                        maxW="560px"
                        w="calc(100vw - 24px)"
                    >
                        <Dialog.Header>
                            <Dialog.Title className="title-styles">Edit profile</Dialog.Title>
                        </Dialog.Header>
                        <Dialog.Body>
                            <VStack align="stretch" gap={4}>
                                <Field.Root>
                                    <Field.Label className="text-styles">Display name</Field.Label>
                                    <Input
                                        value={editForm.pseudo}
                                        onChange={(event) => setEditForm((previous) => ({ ...previous, pseudo: event.target.value }))}
                                        placeholder="Your display name"
                                        className="text-styles"
                                        borderColor="rgba(255,255,255,0.2)"
                                        _focus={{ borderColor: "primary", focusRing: "none" }}
                                    />
                                </Field.Root>

                                <Field.Root>
                                    <Field.Label className="text-styles">Address</Field.Label>
                                    <Input
                                        value={editForm.address}
                                        onChange={(event) => setEditForm((previous) => ({ ...previous, address: event.target.value }))}
                                        placeholder="City, country"
                                        className="text-styles"
                                        borderColor="rgba(255,255,255,0.2)"
                                        _focus={{ borderColor: "primary", focusRing: "none" }}
                                    />
                                </Field.Root>

                                <Field.Root>
                                    <Field.Label className="text-styles">Bio</Field.Label>
                                    <Textarea
                                        value={editForm.bio}
                                        onChange={(event) => setEditForm((previous) => ({ ...previous, bio: event.target.value }))}
                                        placeholder="Tell people about yourself"
                                        className="text-styles"
                                        minH="120px"
                                        resize="vertical"
                                        borderColor="rgba(255,255,255,0.2)"
                                        _focus={{ borderColor: "primary", focusRing: "none" }}
                                    />
                                </Field.Root>
                            </VStack>
                        </Dialog.Body>
                        <Dialog.Footer>
                            <Button
                                bg="primary"
                                color="variantSecondary"
                                _hover={{ opacity: 0.9 }}
                                onClick={() => void saveProfileChanges()}
                                disabled={isSavingProfile}
                            >
                                {isSavingProfile ? "Saving..." : "Save changes"}
                            </Button>
                            <Button
                                bg="transparent"
                                border="1px solid rgba(255,255,255,0.24)"
                                _hover={{ bg: "rgba(255,255,255,0.08)" }}
                                onClick={() => setIsEditDialogOpen(false)}
                            >
                                Cancel
                            </Button>
                        </Dialog.Footer>
                    </Dialog.Content>
                </Dialog.Positioner>
            </Dialog.Root>

            <Dialog.Root
                open={isTwoFaDialogOpen}
                onOpenChange={(event) => {
                    if (!event.open) {
                        closeTwoFaDialog();
                    }
                }}
                placement="center"
            >
                <Dialog.Positioner>
                    <Dialog.Content
                        bg="variantSecondary"
                        border="1px solid rgba(255,255,255,0.16)"
                        maxW="560px"
                        w="calc(100vw - 24px)"
                    >
                        <Dialog.Header>
                            <Dialog.Title className="title-styles">Enable 2FA</Dialog.Title>
                        </Dialog.Header>
                        <Dialog.Body>
                            <VStack align="stretch" gap={4}>
                                <Text className="text-styles" color="rgba(229,231,235,0.82)">
                                    Scan the QR code in your authenticator app, then enter the 6-digit code.
                                </Text>
                                <Box
                                    borderRadius="xl"
                                    border="1px solid rgba(255,255,255,0.14)"
                                    bg="rgba(255,255,255,0.08)"
                                    p={3}
                                    display="flex"
                                    justifyContent="center"
                                    alignItems="center"
                                >
                                    {twoFaQrCode ? (
                                        <img
                                            src={twoFaQrCode}
                                            alt="Two-factor authentication QR code"
                                            style={{
                                                width: "220px",
                                                maxWidth: "100%",
                                                height: "220px",
                                                objectFit: "contain",
                                                borderRadius: "12px",
                                                background: "white",
                                                padding: "8px",
                                            }}
                                        />
                                    ) : (
                                        <Text className="text-styles" color="rgba(229,231,235,0.72)">
                                            QR code is not available.
                                        </Text>
                                    )}
                                </Box>

                                <Text className="text-styles" fontSize="sm" color="rgba(229,231,235,0.76)">
                                    If scanning fails, add it manually with this setup key:
                                </Text>
                                <Input
                                    value={twoFaSecret}
                                    readOnly
                                    className="text-styles"
                                    fontFamily="monospace"
                                    borderColor="rgba(255,255,255,0.2)"
                                    _focus={{ borderColor: "primary", focusRing: "none" }}
                                    placeholder="Manual setup key"
                                />
                                <Textarea
                                    value={twoFaOtpAuthUrl}
                                    readOnly
                                    className="text-styles"
                                    minH="84px"
                                    resize="vertical"
                                    borderColor="rgba(255,255,255,0.2)"
                                    _focus={{ borderColor: "primary", focusRing: "none" }}
                                    placeholder="otpauth URI"
                                />

                                <Field.Root>
                                    <Field.Label className="text-styles">Verification code</Field.Label>
                                    <Input
                                        value={twoFaCode}
                                        onChange={(event) => setTwoFaCode(event.target.value.replace(/\s+/g, "").slice(0, 6))}
                                        placeholder="123456"
                                        className="text-styles"
                                        inputMode="numeric"
                                        autoComplete="one-time-code"
                                        borderColor="rgba(255,255,255,0.2)"
                                        _focus={{ borderColor: "primary", focusRing: "none" }}
                                        disabled={isTwoFaBusy}
                                    />
                                </Field.Root>
                            </VStack>
                        </Dialog.Body>
                        <Dialog.Footer>
                            <Button
                                bg="primary"
                                color="variantSecondary"
                                _hover={{ opacity: 0.9 }}
                                onClick={() => void handleVerifyTwoFa()}
                                disabled={isTwoFaBusy || (!twoFaQrCode && !twoFaSecret)}
                            >
                                {isTwoFaBusy ? "Verifying..." : "Verify"}
                            </Button>
                            <Button
                                bg="transparent"
                                border="1px solid rgba(255,255,255,0.24)"
                                _hover={{ bg: "rgba(255,255,255,0.08)" }}
                                onClick={closeTwoFaDialog}
                                disabled={isTwoFaBusy}
                            >
                                Cancel
                            </Button>
                        </Dialog.Footer>
                    </Dialog.Content>
                </Dialog.Positioner>
            </Dialog.Root>

            <Dialog.Root
                open={Boolean(pendingMediaUpload)}
                onOpenChange={(event) => {
                    if (!event.open) {
                        closeMediaUploadDialog();
                    }
                }}
                placement="center"
            >
                <Dialog.Positioner>
                    <Dialog.Content
                        bg="variantSecondary"
                        border="1px solid rgba(255,255,255,0.16)"
                        maxW="560px"
                        w="calc(100vw - 24px)"
                    >
                        <Dialog.Header>
                            <Dialog.Title className="title-styles">
                                {pendingMediaUpload?.target === "avatar" ? "Publish profile photo post" : "Publish cover photo post"}
                            </Dialog.Title>
                        </Dialog.Header>
                        <Dialog.Body>
                            <VStack align="stretch" gap={4}>
                                <Text className="text-styles" color="rgba(229,231,235,0.82)">
                                    Add a description for this post.
                                </Text>
                                <Field.Root>
                                    <Field.Label className="text-styles">Description</Field.Label>
                                    <Textarea
                                        value={mediaPostDescription}
                                        onChange={(event) => setMediaPostDescription(event.target.value)}
                                        placeholder={
                                            pendingMediaUpload?.target === "avatar"
                                                ? "I just updated my profile photo"
                                                : "I just updated my cover photo"
                                        }
                                        className="text-styles"
                                        minH="120px"
                                        resize="vertical"
                                        borderColor="rgba(255,255,255,0.2)"
                                        _focus={{ borderColor: "primary", focusRing: "none" }}
                                        disabled={isMediaUploadDialogBusy || isAvatarUploading || isCoverUploading}
                                    />
                                </Field.Root>
                                <Text className="text-styles" fontSize="xs" color="rgba(229,231,235,0.7)">
                                    If left empty, the post will be published without description.
                                </Text>
                            </VStack>
                        </Dialog.Body>
                        <Dialog.Footer>
                            <Button
                                bg="primary"
                                color="variantSecondary"
                                _hover={{ opacity: 0.9 }}
                                onClick={() => void confirmMediaUpload()}
                                disabled={isMediaUploadDialogBusy || isAvatarUploading || isCoverUploading}
                            >
                                {(isMediaUploadDialogBusy || isAvatarUploading || isCoverUploading) ? "Publishing..." : "Publish"}
                            </Button>
                            <Button
                                bg="transparent"
                                border="1px solid rgba(255,255,255,0.24)"
                                _hover={{ bg: "rgba(255,255,255,0.08)" }}
                                onClick={closeMediaUploadDialog}
                                disabled={isMediaUploadDialogBusy || isAvatarUploading || isCoverUploading}
                            >
                                Cancel
                            </Button>
                        </Dialog.Footer>
                    </Dialog.Content>
                </Dialog.Positioner>
            </Dialog.Root>

            <Dialog.Root open={Boolean(previewTarget)} onOpenChange={(event) => !event.open && setPreviewTarget(null)} placement="center">
                <Dialog.Positioner>
                    <Dialog.Content
                        bg="variantSecondary"
                        border="1px solid rgba(255,255,255,0.16)"
                        maxW="720px"
                        w="calc(100vw - 24px)"
                    >
                        <Dialog.Header>
                            <Dialog.Title className="title-styles">
                                {previewTarget === "avatar" ? "Profile photo" : "Cover photo"}
                            </Dialog.Title>
                        </Dialog.Header>
                        <Dialog.Body>
                            <VStack align="stretch" gap={4}>
                                <Box
                                    borderRadius="xl"
                                    overflow="hidden"
                                    border="1px solid rgba(255,255,255,0.14)"
                                    bg="rgba(0,0,0,0.3)"
                                >
                                    {previewTarget === "avatar" && effectiveProfile.avatar_url ? (
                                        <img
                                            src={effectiveProfile.avatar_url}
                                            alt="Profile"
                                            style={{ width: "100%", maxHeight: "420px", objectFit: "contain" }}
                                        />
                                    ) : previewTarget === "cover" && effectiveProfile.cover_url ? (
                                        <img
                                            src={effectiveProfile.cover_url}
                                            alt="Cover"
                                            style={{ width: "100%", maxHeight: "420px", objectFit: "contain" }}
                                        />
                                    ) : (
                                        <Text className="text-styles" p={5}>Image not available.</Text>
                                    )}
                                </Box>

                            </VStack>
                        </Dialog.Body>
                    </Dialog.Content>
                </Dialog.Positioner>
            </Dialog.Root>
        </Flex>
    );
}

export default Profile;