-- Query example: daily corpus coverage, not military activity or NER mentions.
-- Execute after 03_analytics_star.sql; only completed, non-synthetic corpus rows.
SELECT d.date_key, s.source_id, s.label, SUM(f.article_count) AS articles
FROM analytics.fact_article AS f
JOIN analytics.dim_date AS d USING (date_key)
JOIN analytics.dim_source AS s USING (source_id)
JOIN analytics.dim_execution AS x USING (run_id)
WHERE NOT f.synthetic AND x.status = 'complete'
GROUP BY d.date_key, s.source_id, s.label
ORDER BY d.date_key, s.source_id;
