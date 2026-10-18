-- Logical star on current operational metadata, without copying article text.
-- Grain: one current, non-excluded article. Revisions never add a second fact.
-- View keys are logical PK/FK; uniqueness and references come from the OLTP tables.
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE OR REPLACE VIEW analytics.dim_source AS
SELECT source_id, label, base_url
FROM public.sources;

CREATE OR REPLACE VIEW analytics.dim_execution AS
SELECT run_id, kind, status, source_sha256, started_at, completed_at
FROM public.runs;

CREATE OR REPLACE VIEW analytics.fact_article AS
SELECT a.article_id,
       (a.published_at AT TIME ZONE 'UTC')::date AS date_key,
       a.source_id,
       a.run_id,
       a.content_sha256,
       a.schema_version,
       a.synthetic,
       1::integer AS article_count
FROM public.articles AS a
WHERE NOT EXISTS (
    SELECT 1 FROM public.erasures AS e WHERE e.article_id = a.article_id
);

CREATE OR REPLACE VIEW analytics.dim_date AS
SELECT DISTINCT date_key,
       EXTRACT(YEAR FROM date_key)::integer AS year_number,
       EXTRACT(MONTH FROM date_key)::integer AS month_number,
       EXTRACT(DAY FROM date_key)::integer AS day_number
FROM analytics.fact_article;

-- The analytic interface is read-only for both application roles.
GRANT USAGE ON SCHEMA analytics TO osint_reader, osint_writer;
GRANT SELECT ON analytics.dim_source, analytics.dim_execution,
                analytics.dim_date, analytics.fact_article
TO osint_reader, osint_writer;
