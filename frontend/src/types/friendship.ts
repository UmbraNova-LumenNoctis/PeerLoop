export type FriendshipStatus = "pending" | "accepted" | "blocked";
export type FriendshipDirection = "incoming" | "outgoing";

export interface Friendship {
  id: string;
  user_a_id: string;
  user_b_id: string;
  status: FriendshipStatus;
  created_at: string | null;
  direction: FriendshipDirection | null;
  friend_user_id: string | null;
  friend_pseudo: string | null;
  friend_avatar_id: string | null;
  friend_avatar_url: string | null;
  friend_online: boolean;
}
