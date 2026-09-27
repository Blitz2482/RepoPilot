CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    role TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    url TEXT NOT NULL,
    default_branch TEXT,
    analyzed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS onboarding_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    plan_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS code_chunks (
    id BIGSERIAL PRIMARY KEY,
    repo_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    start_line INT NOT NULL,
    end_line INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    code_chunks_fts tsvector
);

ALTER TABLE code_chunks
    ADD COLUMN IF NOT EXISTS code_chunks_fts tsvector;

UPDATE code_chunks
SET code_chunks_fts = to_tsvector('english', content)
WHERE code_chunks_fts IS NULL;

CREATE INDEX IF NOT EXISTS code_chunks_embedding_idx
  ON code_chunks USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS code_chunks_repo_idx
  ON code_chunks (repo_id);

CREATE INDEX IF NOT EXISTS code_chunks_fts_idx
  ON code_chunks USING GIN (code_chunks_fts);
