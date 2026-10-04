CREATE TABLE sources (
    source_id text PRIMARY KEY,
    label text NOT NULL,
    base_url text NOT NULL
);
INSERT INTO sources VALUES ('tass', 'TASS, source unique à contextualiser', 'https://tass.com');
CREATE TABLE runs (
    run_id uuid PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('corpus','synthetic','fixture')),
    source_sha256 char(64) NOT NULL,
    status text NOT NULL CHECK (status IN ('running','complete','failed')),
    checkpoint bigint NOT NULL DEFAULT 0,
    expected bigint NOT NULL CHECK (expected >= 0),
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);
CREATE TABLE articles (
    article_id text PRIMARY KEY,
    source_id text NOT NULL REFERENCES sources(source_id),
    published_at timestamptz NOT NULL,
    content_sha256 char(64) NOT NULL,
    schema_version smallint NOT NULL DEFAULT 1 CHECK (schema_version > 0),
    run_id uuid NOT NULL REFERENCES runs(run_id),
    synthetic boolean NOT NULL DEFAULT false
);
CREATE INDEX articles_date ON articles (published_at);
CREATE INDEX articles_run ON articles (run_id);
CREATE TABLE erasures (
    article_id text PRIMARY KEY,
    request_id uuid NOT NULL,
    requested_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL CHECK (status IN ('pending','complete'))
);
-- Separate read and write capabilities. Administrative credentials are not used by ingestion.
GRANT CONNECT ON DATABASE osint TO osint_writer, osint_reader;
GRANT USAGE ON SCHEMA public TO osint_writer, osint_reader;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO osint_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO osint_reader;
