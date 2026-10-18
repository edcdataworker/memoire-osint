BEGIN;
INSERT INTO sources VALUES
 ('fixture-a','Fictional source A','https://a.example.invalid'),
 ('fixture-b','Fictional source B','https://b.example.invalid');
INSERT INTO runs(run_id,kind,source_sha256,status,checkpoint,expected) VALUES
 ('00000000-0000-0000-0000-000000000001','fixture',repeat('a',64),'complete',3,3),
 ('00000000-0000-0000-0000-000000000002','fixture',repeat('b',64),'complete',2,2);
INSERT INTO articles(article_id,source_id,published_at,content_sha256,run_id,synthetic) VALUES
 ('a1','fixture-a','2026-01-01 00:30:00+02',repeat('1',64),'00000000-0000-0000-0000-000000000001',true),
 ('a2','fixture-a','2026-01-01 22:30:00-03',repeat('2',64),'00000000-0000-0000-0000-000000000001',true),
 ('b1','fixture-b','2026-01-01 12:00:00+00',repeat('3',64),'00000000-0000-0000-0000-000000000002',true),
 ('a3','fixture-a','2026-01-01 12:00:00+00',repeat('4',64),'00000000-0000-0000-0000-000000000001',true),
 ('denied','fixture-a','2026-01-01 12:00:00+00',repeat('5',64),'00000000-0000-0000-0000-000000000002',true);
INSERT INTO erasures VALUES ('denied','00000000-0000-0000-0000-000000000003',now(),'pending');
SET TIME ZONE 'Pacific/Honolulu';
DO $$ BEGIN
 IF (SELECT count(*) FROM analytics.fact_article) <> 4
    OR EXISTS(SELECT 1 FROM analytics.fact_article WHERE article_count<>1 OR NOT synthetic)
 THEN RAISE EXCEPTION 'Invalid article grain or measure'; END IF;
END $$;
SELECT 'PASS:grain';
DO $$ BEGIN
 IF (SELECT date_key FROM analytics.fact_article WHERE article_id='a1') <> DATE '2025-12-31'
    OR (SELECT date_key FROM analytics.fact_article WHERE article_id='a2') <> DATE '2026-01-02'
    OR (SELECT year_number FROM analytics.dim_date WHERE date_key='2025-12-31') <> 2025
 THEN RAISE EXCEPTION 'UTC boundary depends on session timezone'; END IF;
END $$;
SELECT 'PASS:utc';
DO $$ BEGIN
 IF (SELECT sum(article_count) FROM analytics.fact_article
     JOIN analytics.dim_date USING(date_key)
     JOIN analytics.dim_source USING(source_id)
     JOIN analytics.dim_execution USING(run_id)) <> 4
    OR EXISTS(SELECT 1 FROM analytics.fact_article f
      LEFT JOIN analytics.dim_date d USING(date_key)
      LEFT JOIN analytics.dim_source s USING(source_id)
      LEFT JOIN analytics.dim_execution x USING(run_id)
      WHERE d.date_key IS NULL OR s.source_id IS NULL OR x.run_id IS NULL)
 THEN RAISE EXCEPTION 'Broken star joins or double counting'; END IF;
END $$;
SELECT 'PASS:joins';
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM analytics.fact_article WHERE article_id='denied')
 THEN RAISE EXCEPTION 'Pending erasure leaked'; END IF;
END $$;
SELECT 'PASS:exclusion';
INSERT INTO article_revisions(article_id,content_sha256,source_id,published_at,schema_version,run_id)
 SELECT article_id,repeat('9',64),source_id,'2025-12-20 00:00+00',schema_version,run_id
 FROM articles WHERE article_id='a3';
UPDATE articles SET content_sha256=repeat('8',64), published_at='2026-01-03 00:00+00'
 WHERE article_id='a3';
DO $$ BEGIN
 IF (SELECT count(*) FROM analytics.fact_article) <> 4
    OR (SELECT content_sha256 FROM analytics.fact_article WHERE article_id='a3') <> repeat('8',64)
    OR EXISTS(SELECT 1 FROM analytics.dim_date WHERE date_key='2025-12-20')
 THEN RAISE EXCEPTION 'Revision double counted or stale projection'; END IF;
END $$;
SELECT 'PASS:revision';
SET ROLE osint_reader;
DO $$ BEGIN
 IF (SELECT count(*) FROM analytics.fact_article) <> 4 THEN RAISE EXCEPTION 'Reader denied'; END IF;
 BEGIN
  UPDATE analytics.fact_article SET content_sha256=repeat('e',64) WHERE article_id='a1';
  RAISE EXCEPTION 'Reader was allowed to update';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
END $$;
RESET ROLE;
SELECT 'PASS:reader';
SET ROLE osint_writer;
DO $$ BEGIN
 BEGIN
  UPDATE analytics.fact_article SET content_sha256=repeat('e',64) WHERE article_id='a1';
  RAISE EXCEPTION 'Writer analytic interface was writable';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
END $$;
RESET ROLE;
SELECT 'PASS:writer';
DELETE FROM articles WHERE article_id='a1';
DO $$ BEGIN
 IF (SELECT count(*) FROM analytics.fact_article) <> 3
    OR EXISTS(SELECT 1 FROM analytics.dim_date WHERE date_key='2025-12-31')
 THEN RAISE EXCEPTION 'Deleted article still appears in analytic views'; END IF;
END $$;
SELECT 'PASS:deletion';
ROLLBACK;
