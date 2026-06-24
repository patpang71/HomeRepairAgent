-- Run once against HomeRepairRAGDB after the RDS instance is created.
-- Connect via SSM Session Manager tunnel or a bastion host.

-- Step 1: enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: create the schema Bedrock Knowledge Base expects
CREATE SCHEMA IF NOT EXISTS bedrock_integration;

-- Step 3: Bedrock Knowledge Base table
-- Column names must match the fieldMapping in KnowledgeBaseStack:
--   primaryKeyField → id
--   vectorField     → embedding
--   textField       → chunks
--   metadataField   → metadata
CREATE TABLE IF NOT EXISTS bedrock_integration.bedrock_kb (
    id        uuid          PRIMARY KEY,
    embedding vector(1024),            -- must match EMBEDDING_DIMENSIONS in constants.ts
    chunks    text,
    metadata  json
);

-- Step 4: HNSW index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS bedrock_kb_embedding_hnsw_idx
    ON bedrock_integration.bedrock_kb
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Step 5: grant the Bedrock IAM user (via RDS IAM auth) access to the table
-- Replace <db_user> with the username from the Secrets Manager secret
-- GRANT SELECT, INSERT, UPDATE, DELETE ON bedrock_integration.bedrock_kb TO <db_user>;
-- GRANT USAGE ON SCHEMA bedrock_integration TO <db_user>;
