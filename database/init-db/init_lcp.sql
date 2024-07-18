-- run DLL as lcp_production_owner

BEGIN;


CREATE TABLE main.corpus (
   project_id        uuid
 , created_at        timestamptz    NOT NULL DEFAULT now()
 , corpus_id         int            GENERATED ALWAYS AS IDENTITY PRIMARY KEY
 , current_version   smallint       NOT NULL
 , enabled           bool           NOT NULL DEFAULT TRUE
 , corpus_template   jsonb          NOT NULL
 , description       text
 , mapping           jsonb
 , name              text           NOT NULL
 , sample_query      text
 , schema_path       text           NOT NULL
 , token_counts      jsonb
 , version_history   jsonb
 , UNIQUE (name, current_version, project_id)
);


CREATE TABLE main.inprogress_corpus (
   schema_path       uuid           PRIMARY KEY
 , project_id        uuid
 , created_at        timestamptz    NOT NULL DEFAULT now()
 , corpus_id         int            REFERENCES main.corpus
 , is_finished       bool           NOT NULL DEFAULT FALSE
 , corpus_template   jsonb          NOT NULL
);


COMMIT;

