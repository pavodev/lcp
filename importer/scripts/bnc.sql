BEGIN;

DROP SCHEMA IF EXISTS bnc1 CASCADE;
CREATE SCHEMA bnc1;
SET search_path TO bnc1;
/* == SET SCHEMA 'bnc1'; */

/* types */

CREATE TYPE xpos1 AS ENUM (
   'AJ0',
   'AJ0-AV0',
   'AJ0-NN1',
   'AJ0-VVD',
   'AJ0-VVG',
   'AJ0-VVN',
   'AJC',
   'AJS',
   'AT0',
   'AV0',
   'AV0-AJ0',
   'AVP',
   'AVP-PRP',
   'AVQ',
   'AVQ-CJS',
   'CJC',
   'CJS',
   'CJS-AVQ',
   'CJS-PRP',
   'CJT',
   'CJT-DT0',
   'CRD',
   'CRD-PNI',
   'DPS',
   'DT0',
   'DT0-CJT',
   'DTQ',
   'EX0',
   'ITJ',
   'NN0',
   'NN1',
   'NN1-AJ0',
   'NN1-NP0',
   'NN1-VVB',
   'NN1-VVG',
   'NN2',
   'NN2-VVZ',
   'NP0',
   'NP0-NN1',
   'ORD',
   'PNI',
   'PNI-CRD',
   'PNP',
   'PNQ',
   'PNX',
   'POS',
   'PRF',
   'PRP',
   'PRP-AVP',
   'PRP-CJS',
   'PUL',
   'PUN',
   'PUQ',
   'PUR',
   'TO0',
   'UNC',
   'VBB',
   'VBD',
   'VBG',
   'VBI',
   'VBN',
   'VBZ',
   'VDB',
   'VDD',
   'VDG',
   'VDI',
   'VDN',
   'VDZ',
   'VHB',
   'VHD',
   'VHG',
   'VHI',
   'VHN',
   'VHZ',
   'VM0',
   'VVB',
   'VVB-NN1',
   'VVD',
   'VVD-AJ0',
   'VVD-VVN',
   'VVG',
   'VVG-AJ0',
   'VVG-NN1',
   'VVI',
   'VVN',
   'VVN-AJ0',
   'VVN-VVD',
   'VVZ',
   'VVZ-NN2',
   'XX0',
   'ZZ0'
);

CREATE TYPE xpos2 AS ENUM (
   'ADJ',
   'ADV',
   'ART',
   'CONJ',
   'INTERJ',
   'PREP',
   'PRON',
   'SUBST',
   'UNC',
   'VERB'
);


/* tables */

CREATE TABLE form (
   form_id           int         PRIMARY KEY,
   form              text        NOT NULL UNIQUE
);

CREATE TABLE lemma (
   lemma_id          int         PRIMARY KEY,
   lemma             text        NOT NULL UNIQUE
);

CREATE TABLE segment (
   segment_id        uuid         PRIMARY KEY,
   char_range        int4range    NOT NULL
);

CREATE TABLE paragraph (
   paragraph_id      int         PRIMARY KEY,
   char_range        int4range   NOT NULL
);

CREATE TABLE division (
   division_id       int         PRIMARY KEY,
   char_range        int4range   NOT NULL
);

CREATE TABLE document (
   document_id       int         PRIMARY KEY,
   char_range        int4range   NOT NULL,
   meta              jsonb
);

CREATE TABLE token0 (
    token_id          int,
    form_id           int,
    lemma_id          int,
    xpos1             xpos1,
    xpos2             xpos2,
    char_range        int4range,
    segment_id        uuid
 )
PARTITION BY RANGE (segment_id);

CREATE TABLE token1 PARTITION OF token0
   FOR VALUES FROM ('80000000-0000-0000-0000-000000000000'::uuid) TO ('ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid);

CREATE TABLE token2 PARTITION OF token0
   FOR VALUES FROM ('40000000-0000-0000-0000-000000000000'::uuid) TO ('80000000-0000-0000-0000-000000000000'::uuid);

CREATE TABLE token3 PARTITION OF token0
   FOR VALUES FROM ('20000000-0000-0000-0000-000000000000'::uuid) TO ('40000000-0000-0000-0000-000000000000'::uuid);

CREATE TABLE token4 PARTITION OF token0
   FOR VALUES FROM ('10000000-0000-0000-0000-000000000000'::uuid) TO ('20000000-0000-0000-0000-000000000000'::uuid);

CREATE TABLE token5 PARTITION OF token0
   FOR VALUES FROM ('08000000-0000-0000-0000-000000000000'::uuid) TO ('10000000-0000-0000-0000-000000000000'::uuid);

CREATE TABLE token6 PARTITION OF token0
   FOR VALUES FROM ('04000000-0000-0000-0000-000000000000'::uuid) TO ('08000000-0000-0000-0000-000000000000'::uuid);

CREATE TABLE token7 PARTITION OF token0
   FOR VALUES FROM ('02000000-0000-0000-0000-000000000000'::uuid) TO ('04000000-0000-0000-0000-000000000000'::uuid);

CREATE TABLE tokenrest PARTITION OF token0
   FOR VALUES FROM ('00000000-0000-0000-0000-000000000000'::uuid) TO ('02000000-0000-0000-0000-000000000000'::uuid);



/* DATA IMPORT */

/* indices/FKs */

ALTER TABLE token0 ADD PRIMARY KEY (segment_id, token_id);
ALTER TABLE token0 ADD FOREIGN KEY (form_id)    REFERENCES form(form_id);
ALTER TABLE token0 ADD FOREIGN KEY (lemma_id)   REFERENCES lemma(lemma_id);
ALTER TABLE token0 ADD FOREIGN KEY (segment_id) REFERENCES segment(segment_id);

CREATE INDEX ON token0 (form_id);
CREATE INDEX ON token0 (lemma_id);
CREATE INDEX ON token0 (xpos1);
CREATE INDEX ON token0 (xpos2);
CREATE INDEX ON token0 USING gist (char_range);
CREATE INDEX ON token0 (segment_id);

CREATE INDEX ON form (form);
CREATE INDEX ON lemma (lemma);

CREATE INDEX ON segment   USING gist (char_range);
CREATE INDEX ON division  USING gist (char_range);
CREATE INDEX ON paragraph USING gist (char_range);
CREATE INDEX ON document  USING gist (char_range);



/* prepared_segments */

CREATE TABLE prepared_segment (
    segment_id     uuid        PRIMARY KEY REFERENCES segment (segment_id),
    off_set        int,
    content        jsonb
);

WITH ins AS (
       SELECT segment_id
            , min(token_id) AS off_set
            , to_jsonb(array_agg(toks ORDER BY token_id))
         FROM (
              SELECT s.segment_id
                   , token_id
                   , jsonb_build_array(
                        form
                      , lemma
                      , xpos1
                      , xpos2
                     ) AS toks
                FROM token0 t
                JOIN form      USING (form_id)
                JOIN lemma     USING (lemma_id)
                JOIN segment s USING (segment_id)
               ORDER BY t.token_id) x
        GROUP BY segment_id)
 INSERT INTO prepared_segment
 SELECT *
   FROM ins
 ;

END;