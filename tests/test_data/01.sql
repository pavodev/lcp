WITH RECURSIVE fixed_parts AS
  (SELECT s.segment_id AS s,
          t12.token_id AS t12,
          t22.token_id AS t22,
          t32.token_id AS t32,
          t3_lemma.lemma AS t3_lemma
   FROM
     (SELECT Segment_id
      FROM bnc1.fts_vectorrest vec
      WHERE vec.vector @@ E'2true'
        AND vec.vector @@ E' 7ART <1> ( 2true &  7ADJ) <1>  7SUBST') AS fts_vector_s
   CROSS JOIN bnc1.document d
   CROSS JOIN bnc1.segmentrest s
   CROSS JOIN bnc1.tokenrest t12
   CROSS JOIN bnc1.tokenrest t22
   CROSS JOIN bnc1.lemma t3_lemma
   CROSS JOIN bnc1.tokenrest t32
   CROSS JOIN bnc1.lemma t22_lemma
   WHERE (d.meta->>'classCode')::text ~ '^S'
     AND d.char_range && s.char_range
     AND fts_vector_s.segment_id = s.segment_id
     AND s.segment_id = t12.segment_id
     AND t12.xpos2 = 'ART'
     AND s.segment_id = t22.segment_id
     AND (t22_lemma.lemma = 'true'
          AND t22.xpos2 = 'ADJ')
     AND s.segment_id = t32.segment_id
     AND t32.xpos2 = 'SUBST'
     AND t22.lemma_id = t22_lemma.lemma_id
     AND t22.token_id - t12.token_id = 1
     AND t32.token_id - t22.token_id = 1
     AND t3_lemma.lemma_id = t32.lemma_id ),
               gather AS
  (SELECT s,
          t12,
          t22,
          t32,
          t3_lemma
   FROM fixed_parts) ,
               match_list AS
  (SELECT gather.s AS s,
          gather.t12 AS t1,
          gather.t22 AS t2,
          gather.t32 AS t3,
          gather.t3_lemma AS t3_lemma
   FROM gather),
               res0 AS
  (SELECT 0::int2 AS rstype,
          jsonb_build_array(count(*))
   FROM match_list) ,
               res1 AS
  (SELECT 1::int2 AS rstype,
          jsonb_build_array(s, jsonb_build_array(t1, t2, t3))
   FROM match_list) ,
               res2 AS
  (SELECT 2::int2 AS rstype,
          jsonb_build_array(t3_lemma, frequency)
   FROM
     (SELECT t3_lemma ,
             count(*) AS frequency
      FROM match_list
      GROUP BY t3_lemma) x)
SELECT *
FROM res0
UNION ALL
SELECT *
FROM res1
UNION ALL
SELECT *
FROM res2 ;