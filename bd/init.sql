-- ==============================================================================
-- 🛠️ 0. INITIALISATION & UTILITAIRES
-- ==============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Fonction générique pour mettre à jour 'updated_at' automatiquement
CREATE OR REPLACE FUNCTION public.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Gestion sécurisée de l'ENUM 'friend_status' (évite les erreurs si existe déjà)
DO $$ BEGIN
    CREATE TYPE friend_status AS ENUM ('pending', 'accepted', 'blocked');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ==============================================================================
-- 👤 1. UTILISATEURS
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    pseudo VARCHAR(30) UNIQUE,
    email VARCHAR(255),
    address TEXT,
    bio TEXT,
    avatar_url TEXT,
    cover_url TEXT,
    avatar_id UUID,
    cover_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS cover_url TEXT;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS avatar_id UUID;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS cover_id UUID;
ALTER TABLE public.users DROP COLUMN IF EXISTS is_bot;

-- Trigger updated_at
DROP TRIGGER IF EXISTS set_updated_at_users ON public.users;
CREATE TRIGGER set_updated_at_users
BEFORE UPDATE ON public.users
FOR EACH ROW EXECUTE PROCEDURE public.update_timestamp();

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF to_regclass('public.media_files') IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conname = 'users_avatar_id_fkey'
        AND conrelid = 'public.users'::regclass
    ) THEN
      ALTER TABLE public.users
      ADD CONSTRAINT users_avatar_id_fkey
      FOREIGN KEY (avatar_id) REFERENCES public.media_files(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conname = 'users_cover_id_fkey'
        AND conrelid = 'public.users'::regclass
    ) THEN
      ALTER TABLE public.users
      ADD CONSTRAINT users_cover_id_fkey
      FOREIGN KEY (cover_id) REFERENCES public.media_files(id) ON DELETE SET NULL;
    END IF;
  END IF;
END
$$;

-- 🔄 TRIGGER : Synchronisation Auth -> Public
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email, pseudo, avatar_url, cover_url)
  VALUES (
    NEW.id,
    NEW.email,
    -- Génère un pseudo par défaut si non fourni : "User_a1b2c3d4"
    COALESCE(NEW.raw_user_meta_data->>'username', 'User_' || substr(NEW.id::text, 1, 8)),
    NEW.raw_user_meta_data->>'avatar_url',
    NEW.raw_user_meta_data->>'cover_url'
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Recréation propre du trigger auth
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- ==============================================================================
-- 🤝 3. AMIS (Friendships)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.friendships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_a_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    user_b_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    status friend_status DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_friendship UNIQUE (user_a_id, user_b_id),
    CONSTRAINT not_self_friend CHECK (user_a_id <> user_b_id)
);

-- Ensure updated_at column exists (required by the update_timestamp trigger)
ALTER TABLE public.friendships ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Recreate the trigger so updates work correctly
DROP TRIGGER IF EXISTS set_updated_at_friendships ON public.friendships;
CREATE TRIGGER set_updated_at_friendships
BEFORE UPDATE ON public.friendships
FOR EACH ROW EXECUTE PROCEDURE public.update_timestamp();

ALTER TABLE public.friendships ENABLE ROW LEVEL SECURITY;

-- ==============================================================================
-- 📰 5. POSTS & INTERACTIONS
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    content TEXT,
    media_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS media_id UUID;
ALTER TABLE public.posts DROP COLUMN IF EXISTS media_url;

DO $$
BEGIN
  IF to_regclass('public.media_files') IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conname = 'posts_media_id_fkey'
        AND conrelid = 'public.posts'::regclass
    ) THEN
      ALTER TABLE public.posts
      ADD CONSTRAINT posts_media_id_fkey
      FOREIGN KEY (media_id) REFERENCES public.media_files(id) ON DELETE SET NULL;
    END IF;
  END IF;
END
$$;

DROP TRIGGER IF EXISTS set_updated_at_posts ON public.posts;
CREATE TRIGGER set_updated_at_posts
BEFORE UPDATE ON public.posts
FOR EACH ROW EXECUTE PROCEDURE public.update_timestamp();

CREATE INDEX IF NOT EXISTS idx_posts_user_id ON public.posts(user_id);

CREATE TABLE IF NOT EXISTS public.post_likes (
    post_id UUID REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, user_id)
);
ALTER TABLE public.post_likes DROP COLUMN IF EXISTS created_at;

CREATE TABLE IF NOT EXISTS public.comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES public.comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comments_post_id ON public.comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_comment_id ON public.comments(parent_comment_id);
ALTER TABLE public.comments ADD COLUMN IF NOT EXISTS parent_comment_id UUID;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'comments_parent_comment_id_fkey'
          AND conrelid = 'public.comments'::regclass
    ) THEN
        ALTER TABLE public.comments
        ADD CONSTRAINT comments_parent_comment_id_fkey
        FOREIGN KEY (parent_comment_id) REFERENCES public.comments(id) ON DELETE CASCADE;
    END IF;
END
$$;

ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.post_likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;

-- ==============================================================================
-- 💬 6. MESSAGERIE
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE public.conversations DROP COLUMN IF EXISTS is_group;

DROP TRIGGER IF EXISTS set_updated_at_conversations ON public.conversations;
ALTER TABLE public.conversations DROP COLUMN IF EXISTS updated_at;

CREATE TABLE IF NOT EXISTS public.conversation_participants (
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    last_read_at TIMESTAMPTZ DEFAULT NOW(),
    hidden_at TIMESTAMPTZ,
    PRIMARY KEY (conversation_id, user_id)
);
ALTER TABLE public.conversation_participants ADD COLUMN IF NOT EXISTS hidden_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_conversation_participants_user_visibility
ON public.conversation_participants(user_id, hidden_at, last_read_at);

CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    -- Pas de sender_username ici (redondance), on fera un JOIN avec users
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE public.messages DROP COLUMN IF EXISTS attachment_path;

ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- ==============================================================================
-- 🔔 7. NOTIFICATIONS
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    -- Utilisation de VARCHAR pour permettre 'friend_req', 'game_invite', etc.
    type VARCHAR(50) NOT NULL, 
    content TEXT,
    source_id UUID,
  actor_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

-- ==============================================================================
-- 🤖 8. LLM HISTORY
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.llm_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    provider VARCHAR(64),
    model VARCHAR(128),
    finish_reason VARCHAR(64),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT llm_messages_role_check CHECK (role IN ('user', 'assistant'))
);

CREATE INDEX IF NOT EXISTS idx_llm_messages_user_created_at
ON public.llm_messages(user_id, created_at);

ALTER TABLE public.llm_messages ENABLE ROW LEVEL SECURITY;

-- ==============================================================================
-- 🔐 9. POLITIQUES DE SÉCURITÉ (RLS) - RESET & RECREATE
-- ==============================================================================

-- USERS
DROP POLICY IF EXISTS users_read_all ON public.users;
CREATE POLICY users_read_all ON public.users FOR SELECT USING (true);

DROP POLICY IF EXISTS users_update_own ON public.users;
CREATE POLICY users_update_own ON public.users FOR UPDATE USING (auth.uid() = id);

-- FRIENDSHIPS
DROP POLICY IF EXISTS friendships_select ON public.friendships;
CREATE POLICY friendships_select ON public.friendships FOR SELECT
USING (auth.uid() = user_a_id OR auth.uid() = user_b_id);

DROP POLICY IF EXISTS friendships_insert ON public.friendships;
CREATE POLICY friendships_insert ON public.friendships FOR INSERT
WITH CHECK (auth.uid() = user_a_id);

DROP POLICY IF EXISTS friendships_update ON public.friendships;
CREATE POLICY friendships_update ON public.friendships FOR UPDATE
USING (auth.uid() = user_a_id OR auth.uid() = user_b_id);

-- POSTS
DROP POLICY IF EXISTS posts_read_all ON public.posts;
CREATE POLICY posts_read_all ON public.posts FOR SELECT USING (true);

DROP POLICY IF EXISTS posts_insert_own ON public.posts;
CREATE POLICY posts_insert_own ON public.posts FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS posts_modify_own ON public.posts;
CREATE POLICY posts_modify_own ON public.posts FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS posts_delete_own ON public.posts;
CREATE POLICY posts_delete_own ON public.posts FOR DELETE USING (auth.uid() = user_id);

-- LIKES
DROP POLICY IF EXISTS likes_read_all ON public.post_likes;
CREATE POLICY likes_read_all ON public.post_likes FOR SELECT USING (true);

DROP POLICY IF EXISTS likes_create_own ON public.post_likes;
CREATE POLICY likes_create_own ON public.post_likes FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS likes_delete_own ON public.post_likes;
CREATE POLICY likes_delete_own ON public.post_likes FOR DELETE USING (auth.uid() = user_id);

-- COMMENTS
DROP POLICY IF EXISTS comments_read_all ON public.comments;
CREATE POLICY comments_read_all ON public.comments FOR SELECT USING (true);

DROP POLICY IF EXISTS comments_create_own ON public.comments;
CREATE POLICY comments_create_own ON public.comments FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS comments_delete_own ON public.comments;
CREATE POLICY comments_delete_own ON public.comments FOR DELETE USING (auth.uid() = user_id);

-- MESSAGING
-- Conversations
DROP POLICY IF EXISTS conversations_select_part ON public.conversations;
CREATE POLICY conversations_select_part ON public.conversations FOR SELECT
USING (
    EXISTS (
        SELECT 1
        FROM public.conversation_participants
        WHERE conversation_id = id
          AND user_id = auth.uid()
          AND hidden_at IS NULL
    )
);

DROP POLICY IF EXISTS conversations_insert_auth ON public.conversations;
CREATE POLICY conversations_insert_auth ON public.conversations FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Participants
DROP POLICY IF EXISTS participants_select_own ON public.conversation_participants;
CREATE POLICY participants_select_own ON public.conversation_participants FOR SELECT
USING (user_id = auth.uid() OR conversation_id IN (SELECT conversation_id FROM public.conversation_participants WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS participants_insert_auth ON public.conversation_participants;
CREATE POLICY participants_insert_auth ON public.conversation_participants FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Messages
DROP POLICY IF EXISTS messages_read_part ON public.messages;
CREATE POLICY messages_read_part ON public.messages FOR SELECT
USING (
    EXISTS (
        SELECT 1
        FROM public.conversation_participants cp
        WHERE cp.conversation_id = messages.conversation_id
          AND cp.user_id = auth.uid()
          AND cp.hidden_at IS NULL
    )
);

DROP POLICY IF EXISTS messages_insert_own ON public.messages;
CREATE POLICY messages_insert_own ON public.messages FOR INSERT WITH CHECK (auth.uid() = sender_id);

-- NOTIFICATIONS
DROP POLICY IF EXISTS notif_select_own ON public.notifications;
CREATE POLICY notif_select_own ON public.notifications FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS notif_update_own ON public.notifications;
CREATE POLICY notif_update_own ON public.notifications FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS notif_insert_auth ON public.notifications;
CREATE POLICY notif_insert_auth ON public.notifications FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- LLM MESSAGES
DROP POLICY IF EXISTS llm_messages_select_own ON public.llm_messages;
CREATE POLICY llm_messages_select_own ON public.llm_messages FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS llm_messages_insert_own ON public.llm_messages;
CREATE POLICY llm_messages_insert_own ON public.llm_messages FOR INSERT WITH CHECK (auth.uid() = user_id);
