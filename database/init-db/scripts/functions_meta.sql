\c lcp_production lcp_production_owner

CREATE OR REPLACE PROCEDURE main.update_corpus_meta(
   corpus_id         int
 , metadata_json     jsonb
)
AS $$
   BEGIN

    UPDATE main.corpus mc
        SET
            corpus_template = jsonb_set(
               mc.corpus_template,
               '{meta}',
               mc.corpus_template->'meta' || $2
            )
        WHERE mc.corpus_id = $1;
   END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

ALTER PROCEDURE main.update_corpus_meta
  SET search_path = pg_catalog,pg_temp;

REVOKE EXECUTE ON PROCEDURE main.update_corpus_meta FROM public;
GRANT EXECUTE ON PROCEDURE main.update_corpus_meta TO lcp_production_web_user;