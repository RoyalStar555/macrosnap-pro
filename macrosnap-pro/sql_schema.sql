-- =============================================================
-- MacroSnap Pro — Full Database Reset & Setup
-- Run this in the Supabase SQL Editor (one shot, idempotent)
-- =============================================================

-- 0. Ensure pgcrypto is available for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Drop existing tables (meal_logs first due to FK dependency)
DROP TABLE IF EXISTS meal_logs CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;

-- 2. Create profiles table with ALL required columns
CREATE TABLE profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_number TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    full_name       TEXT,
    age             INT NOT NULL,
    gender          TEXT NOT NULL,
    height_cm       FLOAT NOT NULL,
    weight_kg       FLOAT NOT NULL,
    activity_level  TEXT NOT NULL,
    goal            TEXT NOT NULL,
    tdee            FLOAT NOT NULL,
    calorie_target  FLOAT NOT NULL,
    protein_target_g FLOAT NOT NULL,
    carb_target_g   FLOAT NOT NULL,
    fat_target_g    FLOAT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 3. Create meal_logs table
CREATE TABLE meal_logs (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id   UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    food_name TEXT NOT NULL,
    calories  FLOAT NOT NULL,
    protein_g FLOAT NOT NULL,
    carbs_g   FLOAT NOT NULL,
    fat_g     FLOAT NOT NULL,
    log_date  DATE DEFAULT CURRENT_DATE
);

-- 4. Enable Row-Level Security on both tables
ALTER TABLE profiles  ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_logs ENABLE ROW LEVEL SECURITY;

-- 5. Create fully permissive RLS policies for local/dev testing
--    (Replace with proper auth-based policies before going to production)

-- profiles: allow everything for anon
DROP POLICY IF EXISTS "profiles_allow_all_anon" ON profiles;
CREATE POLICY "profiles_allow_all_anon" ON profiles
    FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- profiles: allow everything for authenticated
DROP POLICY IF EXISTS "profiles_allow_all_authenticated" ON profiles;
CREATE POLICY "profiles_allow_all_authenticated" ON profiles
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- meal_logs: allow everything for anon
DROP POLICY IF EXISTS "meal_logs_allow_all_anon" ON meal_logs;
CREATE POLICY "meal_logs_allow_all_anon" ON meal_logs
    FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- meal_logs: allow everything for authenticated
DROP POLICY IF EXISTS "meal_logs_allow_all_authenticated" ON meal_logs;
CREATE POLICY "meal_logs_allow_all_authenticated" ON meal_logs
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- 6. Grant full DML permissions to both roles
GRANT SELECT, INSERT, UPDATE, DELETE ON profiles  TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON profiles  TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON meal_logs TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON meal_logs TO authenticated;

-- 7. Grant USAGE on the public schema (required for supabase-py to see the tables)
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO authenticated;

-- =============================================================
-- Done. Both tables are ready with auto-UUID, permissive RLS,
-- and full grants for local development.
-- =============================================================
