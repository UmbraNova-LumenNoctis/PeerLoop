export interface PostData
{
    id: string;
    image: string;
    content: string;
    createdAt: string;
    authorId: string;
    authorPseudonym: string;
    authorAvatar: string;
    comments: number;
    likes: number;
    likedByMe: boolean;
}

export interface CommentData
{
    id: string;
    content: string;
    authorId: string;
    authorAvatar: string;
    authorPseudo: string;
	createdAt: string;
}
