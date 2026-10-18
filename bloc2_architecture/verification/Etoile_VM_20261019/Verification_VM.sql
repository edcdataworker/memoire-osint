
SELECT json_build_object(
 'views',(SELECT json_agg(viewname ORDER BY viewname) FROM pg_views WHERE schemaname='analytics'),
 'fact_rows',(SELECT count(*) FROM analytics.fact_article),
 'unique_articles',(SELECT count(DISTINCT article_id) FROM analytics.fact_article),
 'article_count',(SELECT sum(article_count) FROM analytics.fact_article),
 'expected_rows',(SELECT count(*) FROM public.articles a WHERE NOT EXISTS(SELECT 1 FROM public.erasures e WHERE e.article_id=a.article_id)),
 'synthetic_rows',(SELECT count(*) FROM analytics.fact_article WHERE synthetic),
 'joined_rows',(SELECT count(*) FROM analytics.fact_article JOIN analytics.dim_date USING(date_key) JOIN analytics.dim_source USING(source_id) JOIN analytics.dim_execution USING(run_id)),
 'wrong_dates',(SELECT count(*) FROM analytics.fact_article f JOIN public.articles a USING(article_id) WHERE f.date_key IS DISTINCT FROM (a.published_at AT TIME ZONE 'UTC')::date),
 'excluded_rows',(SELECT count(*) FROM analytics.fact_article JOIN public.erasures USING(article_id)),
 'dimensions',json_build_object('dates',(SELECT count(*) FROM analytics.dim_date),'sources',(SELECT count(*) FROM analytics.dim_source),'executions',(SELECT count(*) FROM analytics.dim_execution)),
 'rights',(SELECT json_agg(json_build_object('role',r,'view',v,'select',has_table_privilege(r,'analytics.'||v,'SELECT'),'insert',has_table_privilege(r,'analytics.'||v,'INSERT'),'update',has_table_privilege(r,'analytics.'||v,'UPDATE'),'delete',has_table_privilege(r,'analytics.'||v,'DELETE'))) FROM unnest(ARRAY['osint_reader','osint_writer']) r CROSS JOIN unnest(ARRAY['dim_date','dim_source','dim_execution','fact_article']) v)
);
