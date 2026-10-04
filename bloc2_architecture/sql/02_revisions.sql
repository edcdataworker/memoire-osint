-- Additive migration: preserve old metadata when a collected article changes.
CREATE TABLE IF NOT EXISTS article_revisions (
    article_id text NOT NULL,
    content_sha256 char(64) NOT NULL,
    source_id text NOT NULL REFERENCES sources(source_id),
    published_at timestamptz NOT NULL,
    schema_version smallint NOT NULL,
    run_id uuid NOT NULL REFERENCES runs(run_id),
    archived_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (article_id, content_sha256)
);
CREATE INDEX IF NOT EXISTS article_revisions_date ON article_revisions(published_at);
GRANT SELECT, INSERT, UPDATE, DELETE ON article_revisions TO osint_writer;
GRANT SELECT ON article_revisions TO osint_reader;
