import { useCallback, useEffect, useState } from 'react';
import useApi from './useAPI';

export interface UserProfile {
    id: string;
    pseudo: string | null;
    email: string | null;
    address: string | null;
    bio: string | null;
    avatar_id: string | null;
    avatar_url: string | null;
    cover_id: string | null;
    cover_url: string | null;
    created_at: string | null;
    updated_at: string | null;
}

interface UseUserProfileReturn {
    profile: UserProfile | null;
    isLoading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

export const useResolvedUserProfile = (userId: string | null): UseUserProfileReturn => {
    const { execute, isLoading, error } = useApi<UserProfile>();
    const [profile, setProfile] = useState<UserProfile | null>(null);

    const fetchProfile = useCallback(async () => {
        try {
            const endpoint = userId ? `/api/user/${userId}` : '/api/user/me';
            const data = await execute({
                url: endpoint,
                method: 'GET',
                useToken: true,
            });
            setProfile(data);
        } catch (err) {
            console.error('Failed to fetch user profile:', err);
            setProfile(null);
        }
    }, [execute, userId]);

    useEffect(() => {
        void fetchProfile();
    }, [fetchProfile]);

    return {
        profile,
        isLoading,
        error: error ? String(error) : null,
        refetch: fetchProfile,
    };
};

export const useUserProfile = (): UseUserProfileReturn => {
    return useResolvedUserProfile(null);
};

export const useUserProfileById = (userId: string | null): UseUserProfileReturn => {
    return useResolvedUserProfile(userId);
};

export default useUserProfile;
