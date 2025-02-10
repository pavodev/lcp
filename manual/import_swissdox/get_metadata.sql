\copy (
  SELECT content_id
       , language
       , dateline
       , head
       , subhead
       , pubdate::date
       , source
       , source_name
       , jsonb_strip_nulls(
            jsonb_build_object(
              'articleId',     article_id
            , 'contentId',     content_id
            , 'SMDId',         smd_id
            , 'doctype',       doctype
            , 'articleURL',    article_url
            , 'otherPubList',  o_pub_list
            , 'otherPubCount', o_pub_count
            )
         ) AS meta
    FROM (
         SELECT content_id
              , (array_agg(language)                                         FILTER (WHERE i = 1))[1] AS language
              , (array_agg(dateline)                                         FILTER (WHERE i = 1))[1] AS dateline
              , (array_agg(head)                                             FILTER (WHERE i = 1))[1] AS head
              , (array_agg(subhead)                                          FILTER (WHERE i = 1))[1] AS subhead
              , (array_agg(pubtime)                                          FILTER (WHERE i = 1))[1] AS pubdate
              , (array_agg(code)                                             FILTER (WHERE i = 1))[1] AS source
              , (array_agg(name)                                             FILTER (WHERE i = 1))[1] AS source_name
              , (array_agg(article_id)                                       FILTER (WHERE i = 1))[1] AS article_id
              , (array_agg(original_id)                                      FILTER (WHERE i = 1))[1] AS smd_id
              , (array_agg(doctype)                                          FILTER (WHERE i = 1))[1] AS doctype
              , (array_agg(article_link)                                     FILTER (WHERE i = 1))[1] AS article_url
              , string_agg(name || ' [' || code || ']', E'\n' ORDER BY name) FILTER (WHERE i > 1)     AS o_pub_list
              , CASE WHEN count(*) FILTER (WHERE i > 1) > 1 THEN count(*)    FILTER (WHERE i > 1)
                                                            ELSE NULL
                END                                                                                   AS o_pub_count
           FROM (
                  SELECT row_number() OVER w AS i
                       , *
                    FROM core.article
                    JOIN core.publication AS p USING (article_id)
                    JOIN core.source      AS s USING (source_id)
                   WHERE NOT ocr_processed
                     AND NOT EXISTS (
                            SELECT 1
                              FROM import.suppressed AS sup
                             WHERE sup.original_id = p.original_id
                          )
                  WINDOW w AS (PARTITION BY content_id ORDER BY pubtime, original_id, content_id)
                ) AS x
       GROUP BY content_id
         ) AS y
ORDER BY language, pubdate, content_id
) TO '/srv/data/sdoxviz/v2/meta_data.tsv';
