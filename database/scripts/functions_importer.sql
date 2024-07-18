-- create functions as ROLE lcp_production_owner
-- security issues covered here: https://www.cybertec-postgresql.com/en/abusing-security-definer-functions/
REVOKE CREATE ON SCHEMA public FROM public;


CREATE OR REPLACE PROCEDURE main.open_import(
   temp_schema_hash  uuid
 , project_id        uuid
 , corpus_template   jsonb
)
AS $$
   DECLARE
      previous_version  int;
      corpus_name       text;
   BEGIN
      SELECT template -> 'meta' ->> 'name'
        INTO corpus_name
           ;

      ASSERT corpus_name IS NOT NULL AND corpus_name <> ''
           ;

     EXECUTE format('CREATE SCHEMA %I AUTHORIZATION lcp_production_owner;', $1)
           ;
     EXECUTE format('GRANT ALL ON SCHEMA %I TO lcp_production_importer;', $1)
           ;

      SELECT corpus_id
        INTO previous_version
        FROM main.corpus
       WHERE corpus.name       = corpus_name
         AND corpus.project_id = $2
    ORDER BY current_version DESC
       LIMIT 1
           ;

      INSERT
        INTO main.inprogress_corpus (schema_path, corpus_id, project_id, corpus_template, status)
      SELECT $1
           , previous_version
           , $2
           , $3
           , 'ongoing'
           ;

   END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- security issues covered here: https://www.cybertec-postgresql.com/en/abusing-security-definer-functions/
ALTER PROCEDURE main.open_import
   SET search_path = pg_catalog,pg_temp;

REVOKE EXECUTE ON PROCEDURE main.open_import FROM public;
GRANT EXECUTE ON PROCEDURE main.open_import TO lcp_production_importer;


CREATE OR REPLACE FUNCTION main.finish_import(
   temp_schema_hash  uuid
 , project_id        uuid
 , schema_name       text
 , mapping           jsonb
 , token_counts      jsonb
 , OUT new_entry     record
)
AS $$
   DECLARE
      curr_version      int;
      next_version      int;
      new_schema_name   text;
      corpus_name       text;
      template          jsonb;
   BEGIN

      SELECT max(current_version) + 1
           , max(current_version)
        FROM (
                SELECT current_version
                  FROM main.corpus            AS c
                  JOIN main.inprogress_corpus AS t USING (corpus_id)
                 WHERE t.schema_path = $1
             UNION ALL
                SELECT 0
             ) AS x
        INTO next_version
           , curr_version
           ;

      SELECT format('%s_%s', $3, next_version)
        INTO new_schema_name
           ;

      SELECT corpus_template
        INTO template
        FROM main.inprogress_corpus
       WHERE schema_path = $1
           ;

      SELECT template -> 'meta' ->> 'name'
        INTO corpus_name
           ;

      ASSERT corpus_name IS NOT NULL AND corpus_name <> ''
           ;

     EXECUTE format('ALTER SCHEMA %I RENAME TO %I;', $1, new_schema_name)
           ;
     EXECUTE format('GRANT USAGE ON SCHEMA %I TO lcp_production_query_engine;', new_schema_name)
           ;
     EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO lcp_production_query_engine;', new_schema_name)
           ;
     EXECUTE format('REVOKE ALL ON SCHEMA %I FROM lcp_production_importer;', new_schema_name)
           ;

      INSERT
        INTO main.corpus (name, project_id, current_version, corpus_template, schema_path, mapping, token_counts)
      SELECT corpus_name
           , $2
           , next_version
           , template
           , new_schema_name
           , $4
           , $5
   RETURNING *
        INTO new_entry
           ;

      UPDATE main.corpus
         SET enabled = FALSE
       WHERE corpus_id = (
             SELECT corpus_id
               FROM main.inprogress_corpus
              WHERE schema_path = $1
             )
           ;

      UPDATE main.inprogress_corpus
         SET status = 'succeeded'
       WHERE schema_path = $1
           ;

   END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


ALTER FUNCTION main.finish_import
   SET search_path = pg_catalog,pg_temp;

REVOKE EXECUTE ON FUNCTION main.finish_import FROM public;
GRANT EXECUTE ON FUNCTION main.finish_import TO lcp_production_importer;


CREATE OR REPLACE PROCEDURE main.cleanup(
   temp_schema_hash  uuid
)
AS $$

        DROP SCHEMA $1 CASCADE
           ;

      UPDATE main.inprogress_corpus
         SET status = 'failed'
       WHERE schema_path = $1
           ;

   END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- security issues covered here: https://www.cybertec-postgresql.com/en/abusing-security-definer-functions/
ALTER PROCEDURE main.cleanup
   SET search_path = pg_catalog,pg_temp;

REVOKE EXECUTE ON PROCEDURE main.cleanup FROM public;
GRANT EXECUTE ON PROCEDURE main.cleanup TO lcp_production_importer;


-- TODO
-- CREATE OR REPLACE PROCEDURE main.grant_permissions(db_user text, schema_path, text)
-- AS $$
-- $$

