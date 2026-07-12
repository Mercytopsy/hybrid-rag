-- NovaTech Document Q&A System — database bootstrap.
-- Applied automatically on first Postgres container start (mounted into
-- /docker-entrypoint-initdb.d/).
--
-- Embedding storage is handled by langchain_postgres.PGVector itself (it
-- creates `langchain_pg_collection` and `langchain_pg_embedding` on first
-- use, one row per collection: "novatech_text_chunks" and "novatech_tables").
-- We only need the vector extension to exist.

CREATE EXTENSION IF NOT EXISTS vector;

-- Backing store for MultiVectorRetriever's table collection. Holds the full
-- table (rows/columns/markdown as a serialized Document), keyed by doc_id,
-- separate from the embedded summary that lives in langchain_pg_embedding.
-- PostgresByteStore also creates this lazily on first use; declared here
-- too so a fresh DB has it up front.
CREATE TABLE IF NOT EXISTS docstore (
    collection_name TEXT NOT NULL,
    key             TEXT NOT NULL,
    value           BYTEA NOT NULL,
    PRIMARY KEY (collection_name, key)
);
