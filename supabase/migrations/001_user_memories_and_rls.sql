-- Zenith Multi-Tenant Memory & Row-Level Security Migration
-- Run in Supabase SQL Editor for project Zenith

CREATE TABLE IF NOT EXISTS public.user_memories (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    master_summary text NOT NULL DEFAULT '',
    user_profile jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Enable Row-Level Security on all tenant-scoped tables
ALTER TABLE IF EXISTS public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_memories ENABLE ROW LEVEL SECURITY;

-- Sessions policies (owner only; text cast accommodates uuid or text columns)
DROP POLICY IF EXISTS "sessions_owner_select" ON public.sessions;
CREATE POLICY "sessions_owner_select"
    ON public.sessions FOR SELECT
    USING (auth.uid()::text = user_id::text);

DROP POLICY IF EXISTS "sessions_owner_insert" ON public.sessions;
CREATE POLICY "sessions_owner_insert"
    ON public.sessions FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

DROP POLICY IF EXISTS "sessions_owner_update" ON public.sessions;
CREATE POLICY "sessions_owner_update"
    ON public.sessions FOR UPDATE
    USING (auth.uid()::text = user_id::text)
    WITH CHECK (auth.uid()::text = user_id::text);

DROP POLICY IF EXISTS "sessions_owner_delete" ON public.sessions;
CREATE POLICY "sessions_owner_delete"
    ON public.sessions FOR DELETE
    USING (auth.uid()::text = user_id::text);

-- Interactions policies (ownership via parent session)
DROP POLICY IF EXISTS "interactions_session_owner_select" ON public.interactions;
CREATE POLICY "interactions_session_owner_select"
    ON public.interactions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.sessions s
            WHERE s.id::text = interactions.session_id::text
              AND s.user_id::text = auth.uid()::text
        )
    );

DROP POLICY IF EXISTS "interactions_session_owner_insert" ON public.interactions;
CREATE POLICY "interactions_session_owner_insert"
    ON public.interactions FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.sessions s
            WHERE s.id::text = interactions.session_id::text
              AND s.user_id::text = auth.uid()::text
        )
    );

DROP POLICY IF EXISTS "interactions_session_owner_delete" ON public.interactions;
CREATE POLICY "interactions_session_owner_delete"
    ON public.interactions FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.sessions s
            WHERE s.id::text = interactions.session_id::text
              AND s.user_id::text = auth.uid()::text
        )
    );

-- Usage logs policies (owner only)
DROP POLICY IF EXISTS "usage_logs_owner_select" ON public.usage_logs;
CREATE POLICY "usage_logs_owner_select"
    ON public.usage_logs FOR SELECT
    USING (auth.uid()::text = user_id::text);

DROP POLICY IF EXISTS "usage_logs_owner_insert" ON public.usage_logs;
CREATE POLICY "usage_logs_owner_insert"
    ON public.usage_logs FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

-- User memories policies (owner only)
DROP POLICY IF EXISTS "user_memories_owner_select" ON public.user_memories;
CREATE POLICY "user_memories_owner_select"
    ON public.user_memories FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_memories_owner_insert" ON public.user_memories;
CREATE POLICY "user_memories_owner_insert"
    ON public.user_memories FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_memories_owner_update" ON public.user_memories;
CREATE POLICY "user_memories_owner_update"
    ON public.user_memories FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_memories_owner_delete" ON public.user_memories;
CREATE POLICY "user_memories_owner_delete"
    ON public.user_memories FOR DELETE
    USING (auth.uid() = user_id);
