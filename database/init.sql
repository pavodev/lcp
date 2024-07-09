--
-- PostgreSQL database dump
--

-- Dumped from database version 16.3 (Homebrew)
-- Dumped by pg_dump version 16.3 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1;


ALTER SCHEMA free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1 OWNER TO postgres;

--
-- Name: main; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA main;


ALTER SCHEMA main OWNER TO postgres;

--
-- Name: rum; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS rum WITH SCHEMA public;


--
-- Name: EXTENSION rum; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION rum IS 'RUM index access method';


--
-- Name: namedentity_type; Type: TYPE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TYPE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity_type AS ENUM (
    'DATE',
    'DOC',
    'ORG'
);


ALTER TYPE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity_type OWNER TO postgres;

--
-- Name: shot_view; Type: TYPE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TYPE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.shot_view AS ENUM (
    'closeup',
    'face-cam',
    'high angle',
    'low angle',
    'medium closeup',
    'reverse',
    'wide angle'
);


ALTER TYPE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.shot_view OWNER TO postgres;

--
-- Name: token_xpos; Type: TYPE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TYPE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos AS ENUM (
    'A',
    'AP',
    'CC',
    'CS',
    'E',
    'FB',
    'FC',
    'FF',
    'FS',
    'N',
    'NO',
    'PART',
    'PE',
    'PR',
    'RD',
    'RI',
    'S',
    'SP',
    'V',
    'VA',
    'VM',
    'X'
);


ALTER TYPE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos OWNER TO postgres;

--
-- Name: lang; Type: TYPE; Schema: main; Owner: postgres
--

CREATE TYPE main.lang AS ENUM (
    'german',
    'english',
    'french',
    'italian',
    'swedish',
    'mixed'
);


ALTER TYPE main.lang OWNER TO postgres;

--
-- Name: media_type; Type: TYPE; Schema: main; Owner: postgres
--

CREATE TYPE main.media_type AS ENUM (
    'audio',
    'video',
    'image'
);


ALTER TYPE main.media_type OWNER TO postgres;

--
-- Name: new_upos; Type: TYPE; Schema: main; Owner: postgres
--

CREATE TYPE main.new_upos AS ENUM (
    'ADJ',
    'ADP',
    'ADV',
    'AUX',
    'CCONJ',
    'DET',
    'INTJ',
    'NOUN',
    'NUM',
    'PART',
    'PRON',
    'PROPN',
    'PUNCT',
    'SCONJ',
    'SYM',
    'VERB',
    'X'
);


ALTER TYPE main.new_upos OWNER TO postgres;

--
-- Name: old_upos; Type: TYPE; Schema: main; Owner: postgres
--

CREATE TYPE main.old_upos AS ENUM (
    '.',
    'ADJ',
    'ADP',
    'ADV',
    'CONJ',
    'DET',
    'NOUN',
    'NUM',
    'PRON',
    'PRT',
    'VERB',
    'X'
);


ALTER TYPE main.old_upos OWNER TO postgres;

--
-- Name: struct_type; Type: TYPE; Schema: main; Owner: postgres
--

CREATE TYPE main.struct_type AS ENUM (
    'article',
    'sentence'
);


ALTER TYPE main.struct_type OWNER TO postgres;

--
-- Name: udep; Type: TYPE; Schema: main; Owner: postgres
--

CREATE TYPE main.udep AS ENUM (
    'acl',
    'acl:adv',
    'acl:attr',
    'acl:cleft',
    'acl:cmpr',
    'acl:fixed',
    'acl:inf',
    'acl:relat',
    'acl:relcl',
    'acl:subj',
    'acl:tmod',
    'acl:tonp',
    'advcl',
    'advcl:abs',
    'advcl:cau',
    'advcl:cleft',
    'advcl:cmpr',
    'advcl:cond',
    'advcl:coverb',
    'advcl:eval',
    'advcl:lcl',
    'advcl:lto',
    'advcl:mcl',
    'advcl:objective',
    'advcl:pred',
    'advcl:relcl',
    'advcl:svc',
    'advcl:tcl',
    'advmod',
    'advmod:adj',
    'advmod:arg',
    'advmod:cau',
    'advmod:comp',
    'advmod:deg',
    'advmod:det',
    'advmod:df',
    'advmod:dir',
    'advmod:emph',
    'advmod:eval',
    'advmod:fixed',
    'advmod:foc',
    'advmod:freq',
    'advmod:lfrom',
    'advmod:lmod',
    'advmod:lmp',
    'advmod:loc',
    'advmod:locy',
    'advmod:lto',
    'advmod:mmod',
    'advmod:mode',
    'advmod:neg',
    'advmod:obl',
    'advmod:que',
    'advmod:tfrom',
    'advmod:tlocy',
    'advmod:tmod',
    'advmod:to',
    'advmod:tto',
    'amod',
    'amod:att',
    'amod:attlvc',
    'amod:flat',
    'appos',
    'appos:nmod',
    'appos:trans',
    'aux',
    'aux:aff',
    'aux:aspect',
    'aux:caus',
    'aux:clitic',
    'aux:cnd',
    'aux:ex',
    'aux:exhort',
    'aux:imp',
    'aux:nec',
    'aux:neg',
    'aux:opt',
    'aux:part',
    'aux:pass',
    'aux:pot',
    'aux:q',
    'aux:tense',
    'case',
    'case:acc',
    'case:adv',
    'case:aff',
    'case:det',
    'case:gen',
    'case:loc',
    'case:pred',
    'case:voc',
    'cc',
    'cc:nc',
    'ccomp',
    'ccomp:cleft',
    'ccomp:obj',
    'ccomp:obl',
    'ccomp:pmod',
    'ccomp:pred',
    'cc:preconj',
    'clf',
    'clf:det',
    'compound',
    'compound:a',
    'compound:adj',
    'compound:affix',
    'compound:amod',
    'compound:apr',
    'compound:atov',
    'compound:dir',
    'compound:ext',
    'compound:lvc',
    'compound:nn',
    'compound:preverb',
    'compound:pron',
    'compound:prt',
    'compound:quant',
    'compound:redup',
    'compound:smixut',
    'compound:svc',
    'compound:verbnoun',
    'compound:vmod',
    'compound:vo',
    'compound:vv',
    'compound:z',
    'conj',
    'conj:expl',
    'conj:extend',
    'conj:redup',
    'conj:svc',
    'cop',
    'cop:expl',
    'cop:locat',
    'cop:own',
    'csubj',
    'csubj:asubj',
    'csubj:cleft',
    'csubj:cop',
    'csubj:outer',
    'csubj:pass',
    'csubj:pred',
    'csubj:vsubj',
    'dep',
    'dep:aff',
    'dep:agr',
    'dep:alt',
    'dep:ana',
    'dep:aux',
    'dep:comp',
    'dep:conj',
    'dep:cop',
    'dep:emo',
    'dep:infl',
    'dep:mark',
    'dep:mod',
    'dep:pos',
    'dep:redup',
    'dep:ss',
    'det',
    'det:adj',
    'det:clf',
    'det:noun',
    'det:numgov',
    'det:nummod',
    'det:pmod',
    'det:poss',
    'det:predet',
    'det:pron',
    'det:rel',
    'discourse',
    'discourse:conn',
    'discourse:emo',
    'discourse:filler',
    'discourse:intj',
    'discourse:sp',
    'dislocated',
    'dislocated:cleft',
    'dislocated:csubj',
    'dislocated:nsubj',
    'dislocated:obj',
    'dislocated:subj',
    'dislocated:vo',
    'expl',
    'expl:comp',
    'expl:impers',
    'expl:pass',
    'expl:poss',
    'expl:pv',
    'expl:subj',
    'fixed',
    'flat',
    'flat:abs',
    'flat:date',
    'flat:dist',
    'flat:foreign',
    'flat:frac',
    'flat:gov',
    'flat:name',
    'flat:num',
    'flat:number',
    'flat:range',
    'flat:redup',
    'flat:repeat',
    'flat:sibl',
    'flat:time',
    'flat:title',
    'flat:vv',
    'goeswith',
    'iobj',
    'iobj:agent',
    'iobj:appl',
    'iobj:patient',
    'list',
    'mark',
    'mark:adv',
    'mark:advmod',
    'mark:aff',
    'mark:pcomp',
    'mark:plur',
    'mark:prt',
    'mark:q',
    'mark:rel',
    'nmod',
    'nmod:agent',
    'nmod:appos',
    'nmod:arg',
    'nmod:att',
    'nmod:attlvc',
    'nmod:attr',
    'nmod:bahuv',
    'nmod:cau',
    'nmod:comp',
    'nmod:det',
    'nmod:flat',
    'nmod:gen',
    'nmod:gobj',
    'nmod:gsubj',
    'nmod:lfrom',
    'nmod:lmod',
    'nmod:npmod',
    'nmod:obj',
    'nmod:obl',
    'nmod:part',
    'nmod:poss',
    'nmod:pred',
    'nmod:prep',
    'nmod:prp',
    'nmod:redup',
    'nmod:relat',
    'nmod:subj',
    'nmod:tmod',
    'nsubj',
    'nsubj:advmod',
    'nsubj:aff',
    'nsubj:bfoc',
    'nsubj:caus',
    'nsubj:cleft',
    'nsubj:cop',
    'nsubj:expl',
    'nsubj:ifoc',
    'nsubj:lfoc',
    'nsubj:lvc',
    'nsubj:nc',
    'nsubj:nn',
    'nsubj:obj',
    'nsubj:outer',
    'nsubj:pass',
    'nsubj:periph',
    'nsubj:pred',
    'nsubj:quasi',
    'nsubj:x',
    'nsubj:xsubj',
    'nummod',
    'nummod:det',
    'nummod:entity',
    'nummod:flat',
    'nummod:gov',
    'obj',
    'obj:advmod',
    'obj:advneg',
    'obj:agent',
    'obj:appl',
    'obj:caus',
    'obj:lvc',
    'obj:obl',
    'obj:periph',
    'obl',
    'obl:about',
    'obl:ad',
    'obl:adj',
    'obl:adv',
    'obl:advmod',
    'obl:agent',
    'obl:appl',
    'obl:arg',
    'obl:cau',
    'obl:cmp',
    'obl:cmpr',
    'obl:comp',
    'obl:dat',
    'obl:freq',
    'obl:inst',
    'obl:iobj',
    'obl:lfrom',
    'obl:lmod',
    'obl:lmp',
    'obl:lto',
    'obl:lvc',
    'obl:mcl',
    'obl:mod',
    'obl:npmod',
    'obl:obj',
    'obl:orphan',
    'obl:own',
    'obl:patient',
    'obl:pmod',
    'obl:poss',
    'obl:prep',
    'obl:sentcon',
    'obl:smod',
    'obl:subj',
    'obl:tmod',
    'obl:with',
    'orphan',
    'orphan:missing',
    'parataxis',
    'parataxis:appos',
    'parataxis:conj',
    'parataxis:coord',
    'parataxis:deletion',
    'parataxis:discourse',
    'parataxis:dislocated',
    'parataxis:hashtag',
    'parataxis:insert',
    'parataxis:mod',
    'parataxis:newsent',
    'parataxis:nsubj',
    'parataxis:obj',
    'parataxis:parenth',
    'parataxis:rel',
    'parataxis:rep',
    'parataxis:restart',
    'parataxis:rt',
    'parataxis:sentence',
    'parataxis:trans',
    'parataxis:url',
    'punct',
    'reparandum',
    'root',
    'vocative',
    'vocative:cl',
    'vocative:mention',
    'xcomp',
    'xcomp:adj',
    'xcomp:cleft',
    'xcomp:ds',
    'xcomp:obj',
    'xcomp:pred',
    'xcomp:subj',
    'xcomp:vcomp'
);


ALTER TYPE main.udep OWNER TO postgres;

--
-- Name: upos; Type: TYPE; Schema: main; Owner: postgres
--

CREATE TYPE main.upos AS ENUM (
    '.',
    'ADJ',
    'ADP',
    'ADV',
    'AUX',
    'CCONJ',
    'CONJ',
    'DET',
    'INTJ',
    'NOUN',
    'NUM',
    'PART',
    'PRON',
    'PROPN',
    'PRT',
    'PUNCT',
    'SCONJ',
    'SYM',
    'VERB',
    'X'
);


ALTER TYPE main.upos OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: deprel; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.deprel (
    dependent integer,
    head integer,
    udep main.udep,
    left_anchor integer,
    right_anchor integer
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.deprel OWNER TO postgres;

--
-- Name: document; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.document (
    document_id integer NOT NULL,
    meta jsonb,
    media jsonb,
    name text,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.document OWNER TO postgres;

--
-- Name: fts_vector0; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 (
    segment_id uuid NOT NULL,
    vector tsvector
)
PARTITION BY RANGE (segment_id);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 OWNER TO postgres;

--
-- Name: fts_vector1; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector1 (
    segment_id uuid NOT NULL,
    vector tsvector
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector1 OWNER TO postgres;

--
-- Name: fts_vector2; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector2 (
    segment_id uuid NOT NULL,
    vector tsvector
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector2 OWNER TO postgres;

--
-- Name: fts_vector3; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector3 (
    segment_id uuid NOT NULL,
    vector tsvector
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector3 OWNER TO postgres;

--
-- Name: fts_vector4; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector4 (
    segment_id uuid NOT NULL,
    vector tsvector
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector4 OWNER TO postgres;

--
-- Name: fts_vector5; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector5 (
    segment_id uuid NOT NULL,
    vector tsvector
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector5 OWNER TO postgres;

--
-- Name: fts_vector6; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector6 (
    segment_id uuid NOT NULL,
    vector tsvector
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector6 OWNER TO postgres;

--
-- Name: fts_vector7; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector7 (
    segment_id uuid NOT NULL,
    vector tsvector
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector7 OWNER TO postgres;

--
-- Name: fts_vector8; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector8 (
    segment_id uuid NOT NULL,
    vector tsvector
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector8 OWNER TO postgres;

--
-- Name: fts_vector9; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector9 (
    segment_id uuid NOT NULL,
    vector tsvector
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector9 OWNER TO postgres;

--
-- Name: fts_vectorrest; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vectorrest (
    segment_id uuid NOT NULL,
    vector tsvector
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vectorrest OWNER TO postgres;

--
-- Name: token0; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 (
    token_id integer NOT NULL,
    form_id text,
    lemma_id text,
    upos main.upos,
    xpos free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos,
    ufeat_id integer,
    segment_id uuid NOT NULL,
    frame_range int4range,
    char_range int4range
)
PARTITION BY RANGE (segment_id);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 OWNER TO postgres;

--
-- Name: m_lemma_freq0; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq0 AS
 SELECT lemma_id,
    freq,
    sum(freq) OVER () AS total
   FROM ( SELECT token0.lemma_id,
            count(*) AS freq
           FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0
          GROUP BY token0.lemma_id) x
  ORDER BY freq DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq0 OWNER TO postgres;

--
-- Name: token1; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1 (
    token_id integer NOT NULL,
    form_id text,
    lemma_id text,
    upos main.upos,
    xpos free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos,
    ufeat_id integer,
    segment_id uuid NOT NULL,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1 OWNER TO postgres;

--
-- Name: m_lemma_freq1; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq1 AS
 SELECT lemma_id,
    freq,
    sum(freq) OVER () AS total
   FROM ( SELECT token1.lemma_id,
            count(*) AS freq
           FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1
          GROUP BY token1.lemma_id) x
  ORDER BY freq DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq1 OWNER TO postgres;

--
-- Name: token2; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2 (
    token_id integer NOT NULL,
    form_id text,
    lemma_id text,
    upos main.upos,
    xpos free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos,
    ufeat_id integer,
    segment_id uuid NOT NULL,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2 OWNER TO postgres;

--
-- Name: m_lemma_freq2; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq2 AS
 SELECT lemma_id,
    freq,
    sum(freq) OVER () AS total
   FROM ( SELECT token2.lemma_id,
            count(*) AS freq
           FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2
          GROUP BY token2.lemma_id) x
  ORDER BY freq DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq2 OWNER TO postgres;

--
-- Name: token3; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3 (
    token_id integer NOT NULL,
    form_id text,
    lemma_id text,
    upos main.upos,
    xpos free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos,
    ufeat_id integer,
    segment_id uuid NOT NULL,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3 OWNER TO postgres;

--
-- Name: m_lemma_freq3; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq3 AS
 SELECT lemma_id,
    freq,
    sum(freq) OVER () AS total
   FROM ( SELECT token3.lemma_id,
            count(*) AS freq
           FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3
          GROUP BY token3.lemma_id) x
  ORDER BY freq DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq3 OWNER TO postgres;

--
-- Name: token4; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4 (
    token_id integer NOT NULL,
    form_id text,
    lemma_id text,
    upos main.upos,
    xpos free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos,
    ufeat_id integer,
    segment_id uuid NOT NULL,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4 OWNER TO postgres;

--
-- Name: m_lemma_freq4; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq4 AS
 SELECT lemma_id,
    freq,
    sum(freq) OVER () AS total
   FROM ( SELECT token4.lemma_id,
            count(*) AS freq
           FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4
          GROUP BY token4.lemma_id) x
  ORDER BY freq DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq4 OWNER TO postgres;

--
-- Name: token5; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5 (
    token_id integer NOT NULL,
    form_id text,
    lemma_id text,
    upos main.upos,
    xpos free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos,
    ufeat_id integer,
    segment_id uuid NOT NULL,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5 OWNER TO postgres;

--
-- Name: m_lemma_freq5; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq5 AS
 SELECT lemma_id,
    freq,
    sum(freq) OVER () AS total
   FROM ( SELECT token5.lemma_id,
            count(*) AS freq
           FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5
          GROUP BY token5.lemma_id) x
  ORDER BY freq DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq5 OWNER TO postgres;

--
-- Name: token6; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6 (
    token_id integer NOT NULL,
    form_id text,
    lemma_id text,
    upos main.upos,
    xpos free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos,
    ufeat_id integer,
    segment_id uuid NOT NULL,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6 OWNER TO postgres;

--
-- Name: m_lemma_freq6; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq6 AS
 SELECT lemma_id,
    freq,
    sum(freq) OVER () AS total
   FROM ( SELECT token6.lemma_id,
            count(*) AS freq
           FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6
          GROUP BY token6.lemma_id) x
  ORDER BY freq DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq6 OWNER TO postgres;

--
-- Name: token7; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7 (
    token_id integer NOT NULL,
    form_id text,
    lemma_id text,
    upos main.upos,
    xpos free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos,
    ufeat_id integer,
    segment_id uuid NOT NULL,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7 OWNER TO postgres;

--
-- Name: m_lemma_freq7; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq7 AS
 SELECT lemma_id,
    freq,
    sum(freq) OVER () AS total
   FROM ( SELECT token7.lemma_id,
            count(*) AS freq
           FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7
          GROUP BY token7.lemma_id) x
  ORDER BY freq DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq7 OWNER TO postgres;

--
-- Name: token8; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8 (
    token_id integer NOT NULL,
    form_id text,
    lemma_id text,
    upos main.upos,
    xpos free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos,
    ufeat_id integer,
    segment_id uuid NOT NULL,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8 OWNER TO postgres;

--
-- Name: m_lemma_freq8; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq8 AS
 SELECT lemma_id,
    freq,
    sum(freq) OVER () AS total
   FROM ( SELECT token8.lemma_id,
            count(*) AS freq
           FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8
          GROUP BY token8.lemma_id) x
  ORDER BY freq DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq8 OWNER TO postgres;

--
-- Name: tokenrest; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest (
    token_id integer NOT NULL,
    form_id text,
    lemma_id text,
    upos main.upos,
    xpos free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos,
    ufeat_id integer,
    segment_id uuid NOT NULL,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest OWNER TO postgres;

--
-- Name: m_lemma_freqrest; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freqrest AS
 SELECT lemma_id,
    freq,
    sum(freq) OVER () AS total
   FROM ( SELECT tokenrest.lemma_id,
            count(*) AS freq
           FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest
          GROUP BY tokenrest.lemma_id) x
  ORDER BY freq DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freqrest OWNER TO postgres;

--
-- Name: namedentity; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity (
    namedentity_id integer NOT NULL,
    form_id text,
    type free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity_type,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity OWNER TO postgres;

--
-- Name: namedentity_form; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity_form (
    form_id text NOT NULL,
    form text
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity_form OWNER TO postgres;

--
-- Name: prepared_segment; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.prepared_segment (
    segment_id uuid NOT NULL,
    id_offset bigint,
    content jsonb,
    annotations jsonb
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.prepared_segment OWNER TO postgres;

--
-- Name: segment0; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 (
    segment_id uuid NOT NULL,
    meta jsonb,
    frame_range int4range,
    char_range int4range
)
PARTITION BY RANGE (segment_id);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 OWNER TO postgres;

--
-- Name: segment1; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1 (
    segment_id uuid NOT NULL,
    meta jsonb,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1 OWNER TO postgres;

--
-- Name: segment2; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2 (
    segment_id uuid NOT NULL,
    meta jsonb,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2 OWNER TO postgres;

--
-- Name: segment3; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3 (
    segment_id uuid NOT NULL,
    meta jsonb,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3 OWNER TO postgres;

--
-- Name: segment4; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4 (
    segment_id uuid NOT NULL,
    meta jsonb,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4 OWNER TO postgres;

--
-- Name: segment5; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5 (
    segment_id uuid NOT NULL,
    meta jsonb,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5 OWNER TO postgres;

--
-- Name: segment6; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6 (
    segment_id uuid NOT NULL,
    meta jsonb,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6 OWNER TO postgres;

--
-- Name: segment7; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7 (
    segment_id uuid NOT NULL,
    meta jsonb,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7 OWNER TO postgres;

--
-- Name: segment8; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8 (
    segment_id uuid NOT NULL,
    meta jsonb,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8 OWNER TO postgres;

--
-- Name: segment9; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9 (
    segment_id uuid NOT NULL,
    meta jsonb,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9 OWNER TO postgres;

--
-- Name: segmentrest; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest (
    segment_id uuid NOT NULL,
    meta jsonb,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest OWNER TO postgres;

--
-- Name: shot; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.shot (
    shot_id integer NOT NULL,
    view free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.shot_view,
    frame_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.shot OWNER TO postgres;

--
-- Name: token9; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9 (
    token_id integer NOT NULL,
    form_id text,
    lemma_id text,
    upos main.upos,
    xpos free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_xpos,
    ufeat_id integer,
    segment_id uuid NOT NULL,
    frame_range int4range,
    char_range int4range
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9 OWNER TO postgres;

--
-- Name: token_form; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_form (
    form_id text NOT NULL,
    form text
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_form OWNER TO postgres;

--
-- Name: token_freq; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_freq AS
 SELECT form_id,
    lemma_id,
    upos,
    xpos,
    ufeat_id,
    count(*) AS freq
   FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0
  GROUP BY CUBE(form_id, lemma_id, upos, xpos, ufeat_id)
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_freq OWNER TO postgres;

--
-- Name: token_lemma; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_lemma (
    lemma_id text NOT NULL,
    lemma text
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_lemma OWNER TO postgres;

--
-- Name: token_n; Type: MATERIALIZED VIEW; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_n AS
 SELECT count(*) AS freq
   FROM free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0
  WITH NO DATA;


ALTER MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_n OWNER TO postgres;

--
-- Name: token_ufeat; Type: TABLE; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_ufeat (
    ufeat_id integer NOT NULL,
    ufeat jsonb
);


ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_ufeat OWNER TO postgres;

--
-- Name: corpus; Type: TABLE; Schema: main; Owner: postgres
--

CREATE TABLE main.corpus (
    corpus_id integer NOT NULL,
    name text NOT NULL,
    current_version integer NOT NULL,
    version_history jsonb,
    description text,
    corpus_template jsonb NOT NULL,
    schema_path text NOT NULL,
    token_counts jsonb,
    mapping jsonb,
    enabled boolean DEFAULT true,
    sample_query text,
    project_id uuid
);


ALTER TABLE main.corpus OWNER TO postgres;

--
-- Name: corpus_corpus_id_seq; Type: SEQUENCE; Schema: main; Owner: postgres
--

ALTER TABLE main.corpus ALTER COLUMN corpus_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME main.corpus_corpus_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: corpus_language; Type: TABLE; Schema: main; Owner: postgres
--

CREATE TABLE main.corpus_language (
    corpus_id integer NOT NULL,
    iso character(2) NOT NULL
);


ALTER TABLE main.corpus_language OWNER TO postgres;

--
-- Name: fts_vector1; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector1 FOR VALUES FROM ('80000000-0000-0000-0000-000000000000') TO ('ffffffff-ffff-ffff-ffff-ffffffffffff');


--
-- Name: fts_vector2; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector2 FOR VALUES FROM ('40000000-0000-0000-0000-000000000000') TO ('80000000-0000-0000-0000-000000000000');


--
-- Name: fts_vector3; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector3 FOR VALUES FROM ('20000000-0000-0000-0000-000000000000') TO ('40000000-0000-0000-0000-000000000000');


--
-- Name: fts_vector4; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector4 FOR VALUES FROM ('10000000-0000-0000-0000-000000000000') TO ('20000000-0000-0000-0000-000000000000');


--
-- Name: fts_vector5; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector5 FOR VALUES FROM ('08000000-0000-0000-0000-000000000000') TO ('10000000-0000-0000-0000-000000000000');


--
-- Name: fts_vector6; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector6 FOR VALUES FROM ('04000000-0000-0000-0000-000000000000') TO ('08000000-0000-0000-0000-000000000000');


--
-- Name: fts_vector7; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector7 FOR VALUES FROM ('02000000-0000-0000-0000-000000000000') TO ('04000000-0000-0000-0000-000000000000');


--
-- Name: fts_vector8; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector8 FOR VALUES FROM ('01000000-0000-0000-0000-000000000000') TO ('02000000-0000-0000-0000-000000000000');


--
-- Name: fts_vector9; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector9 FOR VALUES FROM ('00800000-0000-0000-0000-000000000000') TO ('01000000-0000-0000-0000-000000000000');


--
-- Name: fts_vectorrest; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vectorrest FOR VALUES FROM ('00000000-0000-0000-0000-000000000000') TO ('00800000-0000-0000-0000-000000000000');


--
-- Name: segment1; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1 FOR VALUES FROM ('80000000-0000-0000-0000-000000000000') TO ('ffffffff-ffff-ffff-ffff-ffffffffffff');


--
-- Name: segment2; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2 FOR VALUES FROM ('40000000-0000-0000-0000-000000000000') TO ('80000000-0000-0000-0000-000000000000');


--
-- Name: segment3; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3 FOR VALUES FROM ('20000000-0000-0000-0000-000000000000') TO ('40000000-0000-0000-0000-000000000000');


--
-- Name: segment4; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4 FOR VALUES FROM ('10000000-0000-0000-0000-000000000000') TO ('20000000-0000-0000-0000-000000000000');


--
-- Name: segment5; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5 FOR VALUES FROM ('08000000-0000-0000-0000-000000000000') TO ('10000000-0000-0000-0000-000000000000');


--
-- Name: segment6; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6 FOR VALUES FROM ('04000000-0000-0000-0000-000000000000') TO ('08000000-0000-0000-0000-000000000000');


--
-- Name: segment7; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7 FOR VALUES FROM ('02000000-0000-0000-0000-000000000000') TO ('04000000-0000-0000-0000-000000000000');


--
-- Name: segment8; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8 FOR VALUES FROM ('01000000-0000-0000-0000-000000000000') TO ('02000000-0000-0000-0000-000000000000');


--
-- Name: segment9; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9 FOR VALUES FROM ('00800000-0000-0000-0000-000000000000') TO ('01000000-0000-0000-0000-000000000000');


--
-- Name: segmentrest; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest FOR VALUES FROM ('00000000-0000-0000-0000-000000000000') TO ('00800000-0000-0000-0000-000000000000');


--
-- Name: token1; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1 FOR VALUES FROM ('80000000-0000-0000-0000-000000000000') TO ('ffffffff-ffff-ffff-ffff-ffffffffffff');


--
-- Name: token2; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2 FOR VALUES FROM ('40000000-0000-0000-0000-000000000000') TO ('80000000-0000-0000-0000-000000000000');


--
-- Name: token3; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3 FOR VALUES FROM ('20000000-0000-0000-0000-000000000000') TO ('40000000-0000-0000-0000-000000000000');


--
-- Name: token4; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4 FOR VALUES FROM ('10000000-0000-0000-0000-000000000000') TO ('20000000-0000-0000-0000-000000000000');


--
-- Name: token5; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5 FOR VALUES FROM ('08000000-0000-0000-0000-000000000000') TO ('10000000-0000-0000-0000-000000000000');


--
-- Name: token6; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6 FOR VALUES FROM ('04000000-0000-0000-0000-000000000000') TO ('08000000-0000-0000-0000-000000000000');


--
-- Name: token7; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7 FOR VALUES FROM ('02000000-0000-0000-0000-000000000000') TO ('04000000-0000-0000-0000-000000000000');


--
-- Name: token8; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8 FOR VALUES FROM ('01000000-0000-0000-0000-000000000000') TO ('02000000-0000-0000-0000-000000000000');


--
-- Name: token9; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9 FOR VALUES FROM ('00800000-0000-0000-0000-000000000000') TO ('01000000-0000-0000-0000-000000000000');


--
-- Name: tokenrest; Type: TABLE ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest FOR VALUES FROM ('00000000-0000-0000-0000-000000000000') TO ('00800000-0000-0000-0000-000000000000');


--
-- Data for Name: deprel; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.deprel (dependent, head, udep, left_anchor, right_anchor) FROM stdin;
2	\N	root	1	12
1	2	amod	2	3
5	2	nmod	4	9
3	5	case	5	6
4	5	amod	7	8
6	2	punct	10	11
7	\N	root	13	46
9	7	conj	14	43
8	9	cc	15	16
13	9	obl	17	42
10	13	case	18	19
12	13	nmod	20	23
11	12	amod	21	22
14	13	nummod	24	33
15	14	dep	25	26
17	14	amod	27	32
16	17	punct	28	29
18	17	punct	30	31
20	13	nmod	34	41
19	20	case	35	36
21	20	flat	37	38
22	20	flat	39	40
23	7	punct	44	45
24	\N	root	47	50
25	24	punct	48	49
34	\N	root	51	160
26	34	mark	52	53
27	34	nsubj	54	65
29	27	conj	55	64
28	29	cc	56	57
32	29	nmod	58	63
30	32	case	59	60
31	32	amod	61	62
33	34	aux	66	67
37	34	obl	68	87
35	37	case	69	70
36	37	amod	71	72
40	37	acl:relcl	73	86
38	40	nsubj	74	75
39	40	aux	76	77
42	40	obj	78	85
41	42	det	79	80
44	42	nmod	81	84
43	44	case	82	83
71	34	conj	88	157
45	71	punct	89	90
46	71	cc	91	92
48	71	nsubj:pass	93	136
47	48	det	94	95
51	48	nmod	96	135
49	51	case	97	98
50	51	det	99	100
57	51	acl:relcl	101	134
53	57	obl	102	105
52	53	case	103	104
55	57	nsubj	106	109
54	55	amod	107	108
56	57	aux	110	111
58	57	obj	112	133
60	58	nmod	113	120
59	60	case	114	115
62	60	conj	116	119
61	62	cc	117	118
64	58	conj	121	132
63	64	cc	122	123
66	64	nmod	124	131
65	66	case	125	126
68	66	conj	127	130
67	68	cc	128	129
69	71	aux	137	138
70	71	aux:pass	139	140
75	71	obl	141	156
72	75	case	142	143
73	75	det	144	145
74	75	amod	146	147
79	75	nmod	148	155
76	79	case	149	150
77	79	det	151	152
78	79	amod	153	154
80	34	punct	158	159
84	\N	root	161	240
81	84	mark	162	163
82	84	expl	164	165
83	84	cop	166	167
85	84	punct	168	169
88	84	advcl	170	213
86	88	mark	171	172
87	88	nsubj	173	174
89	88	advmod	175	176
92	88	xcomp	177	212
90	92	mark	178	179
91	92	aux:pass	180	181
94	92	xcomp	182	211
93	94	mark	183	184
95	94	obj	185	210
96	95	punct	186	187
100	95	nmod	188	195
97	100	case	189	190
98	100	det	191	192
99	100	amod	193	194
101	95	punct	196	197
103	95	nmod	198	209
102	103	case	199	200
105	103	nmod	201	208
104	105	case	202	203
107	105	conj	204	207
106	107	cc	205	206
108	84	punct	214	215
114	84	csubj	216	237
109	114	mark	217	218
111	114	nsubj:pass	219	222
110	111	amod	220	221
112	114	aux	223	224
113	114	aux:pass	225	226
117	114	obl	227	236
115	117	case	228	229
116	117	det	230	231
119	117	nmod	232	235
118	119	case	233	234
120	84	punct	238	239
124	\N	root	241	268
121	124	mark	242	243
122	124	expl	244	245
123	124	cop	246	247
126	124	csubj	248	265
125	126	mark	249	250
128	126	obj	251	264
127	128	det	252	253
131	128	nmod	254	263
129	131	case	255	256
130	131	amod	257	258
133	131	nmod	259	262
132	133	case	260	261
134	124	punct	266	267
\.


--
-- Data for Name: document; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.document (document_id, meta, media, name, frame_range, char_range) FROM stdin;
1	{"end": "62.00", "name": "Bunny", "start": "0.00"}	{"video": "bunny.mp4"}	Bunny	[0,1537)	[1,1045)
\.


--
-- Data for Name: fts_vector1; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector1 (segment_id, vector) FROM stdin;
98c5a367-7235-4411-8a6b-adb705c956f0	'1.':6 '1Declaration':2 '1Human':4 '1Rights':5 '1Universal':1 '1of':3 '2.':6 '2declare':2 '2human':4 '2of':3 '2right':5 '2universal':1 '3ADJ':1,4 '3ADP':3 '3NOUN':2,5 '3PUNCT':6 '4A':1,4 '4E':3 '4FS':6 '4S':2,5 '5':2 '52':1,5,6 '55':3,4 '6':2 '62':1,5,6 '65':3,4 '7':2 '72':1,5,6 '75':3,4 '8':2 '82':1,5,6 '85':3,4
df57ef44-4c6d-470a-9eb3-13402efa0413	'1;':14 '1Whereas':1 '1between':12 '1development':8 '1essential':4 '1friendly':10 '1is':3 '1it':2 '1nations':13 '1of':9 '1promote':6 '1relations':11 '1the':7 '1to':5 '2;':14 '2be':3 '2between':12 '2development':8 '2essential':4 '2friendly':10 '2it':2 '2nation':13 '2of':9 '2promote':6 '2relation':11 '2the':7 '2to':5 '2whereas':1 '3ADJ':4,10 '3ADP':9,12 '3AUX':3 '3DET':7 '3NOUN':8,11,13 '3PART':5 '3PRON':2 '3PUNCT':14 '3SCONJ':1 '3VERB':6 '4A':4,10 '4CS':1 '4E':9,12 '4FC':14 '4PART':5 '4PE':2 '4RD':7 '4S':8,11,13 '4V':3,6 '5':4 '511':9,10,13 '513':12 '54':1,2,3,6,14 '56':5,8 '58':7,11 '6':4 '611':9,10,13 '613':12 '64':1,2,3,6,14 '66':5,8 '68':7,11 '7':4 '711':9,10,13 '713':12 '74':1,2,3,6,14 '76':5,8 '78':7,11 '8':4 '811':9,10,13 '813':12 '84':1,2,3,6,14 '86':5,8 '88':7,11
\.


--
-- Data for Name: fts_vector2; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector2 (segment_id, vector) FROM stdin;
49732404-e110-4108-a9df-03a1e00e9071	'1(':10 '1)':12 '1.':17 '110':14 '11948':16 '1217':8 '1A':9 '1Adopted':1 '1Assembly':6 '1December':15 '1General':5 '1III':11 '1and':2 '1by':4 '1of':13 '1proclaimed':3 '1resolution':7 '2(':10 '2)':12 '2.':17 '210':14 '21948':16 '2217':8 '2A':9 '2December':15 '2adopt':1 '2and':2 '2assembly':6 '2by':4 '2general':5 '2of':13 '2proclaim':3 '2resolution':7 '2third':11 '3ADJ':5,11 '3ADP':4,13 '3CCONJ':2 '3NOUN':6,7 '3NUM':8,14,16 '3PROPN':15 '3PUNCT':10,12,17 '3VERB':1,3 '3X':9 '4A':5 '4CC':2 '4E':4,13 '4FB':10,12 '4FS':17 '4N':8,14,16 '4NO':11 '4S':6,7 '4SP':15 '4V':1,3 '4X':9 '5':1 '51':3,17 '511':10,12 '514':13,15,16 '53':2,7 '56':5 '57':4,6,8,14 '58':9,11 '6':1 '61':3,17 '611':10,12 '614':13,15,16 '63':2,7 '66':5 '67':4,6,8,14 '68':9,11 '7':1 '71':3,17 '711':10,12 '714':13,15,16 '73':2,7 '76':5 '77':4,6,8,14 '78':9,11 '8':1 '81':3,17 '811':10,12 '814':13,15,16 '83':2,7 '86':5 '87':4,6,8,14 '88':9,11
74672be2-f834-48ed-8e7d-e68f2728302c	'1.':2 '1PREAMBLE':1 '2.':2 '2preamble':1 '3NOUN':1 '3PUNCT':2 '4FS':2 '4S':1 '5':1 '51':2 '6':1 '61':2 '7':1 '71':2 '8':1 '81':2
\.


--
-- Data for Name: fts_vector3; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector3 (segment_id, vector) FROM stdin;
235cde54-45f6-4262-922f-87b6ffe969ed	'1,':20 '1;':55 '1Whereas':1 '1a':25 '1acts':12 '1advent':23 '1and':3,21,36,38,42 '1as':47 '1aspiration':50 '1barbarous':11 '1been':45 '1beings':30 '1belief':37 '1common':53 '1conscience':17 '1contempt':4 '1disregard':2 '1enjoy':32 '1fear':41 '1for':5 '1freedom':33,39 '1from':40 '1has':44 '1have':8,14 '1highest':49 '1human':6,29 '1in':10,27 '1mankind':19 '1of':18,24,34,51 '1outraged':15 '1people':54 '1proclaimed':46 '1resulted':9 '1rights':7 '1shall':31 '1speech':35 '1the':16,22,48,52 '1want':43 '1which':13,28 '1world':26 '2,':20 '2;':55 '2a':25 '2act':12 '2advent':23 '2and':3,21,36,38,42 '2as':47 '2aspiration':50 '2barbarous':11 '2be':45 '2being':30 '2belief':37 '2common':53 '2conscience':17 '2contempt':4 '2disregard':2 '2enjoy':32 '2fear':41 '2for':5 '2freedom':33,39 '2from':40 '2have':8,14,44 '2highest':49 '2human':6,29 '2in':10,27 '2mankind':19 '2of':18,24,34,51 '2outrage':15 '2people':54 '2proclaim':46 '2result':9 '2right':7 '2shall':31 '2speech':35 '2the':16,22,48,52 '2want':43 '2whereas':1 '2which':13,28 '2world':26 '3ADJ':6,11,29,49,53 '3ADP':5,10,18,24,27,34,40,47,51 '3AUX':8,14,31,44,45 '3CCONJ':3,21,36,38,42 '3DET':16,22,25,48,52 '3NOUN':2,4,7,12,17,19,23,26,30,33,35,37,39,41,43,50,54 '3PRON':13,28 '3PUNCT':20,55 '3SCONJ':1 '3VERB':9,15,32,46 '4A':6,11,29,49,53 '4CC':3,21,36,38,42 '4CS':1 '4E':5,10,18,24,27,34,40,47,51 '4FC':55 '4FF':20 '4PR':13,28 '4RD':16,22,48,52 '4RI':25 '4S':2,4,7,12,17,19,23,26,30,33,35,37,39,41,43,50,54 '4V':9,15,32,46 '4VA':8,14,44,45 '4VM':31 '5':9 '512':10,11,15 '515':13,14,17 '517':16,19 '519':18 '52':4 '523':22,26 '526':24,25,32 '528':27 '530':29 '532':28,30,31,33 '533':35,39 '535':34,37 '537':36 '539':38,41 '54':3,7 '541':40,43 '543':42 '546':20,21,23,44,45,50 '550':47,48,49,54 '554':51,52,53 '57':5,6 '59':1,2,8,12,46,55 '6':9 '612':10,11,15 '615':13,14,17 '617':16,19 '619':18 '62':4 '623':22,26 '626':24,25,32 '628':27 '630':29 '632':28,30,31,33 '633':35,39 '635':34,37 '637':36 '639':38,41 '64':3,7 '641':40,43 '643':42 '646':20,21,23,44,45,50 '650':47,48,49,54 '654':51,52,53 '67':5,6 '69':1,2,8,12,46,55 '7':9 '712':10,11,15 '715':13,14,17 '717':16,19 '719':18 '72':4 '723':22,26 '726':24,25,32 '728':27 '730':29 '732':28,30,31,33 '733':35,39 '735':34,37 '737':36 '739':38,41 '74':3,7 '741':40,43 '743':42 '746':20,21,23,44,45,50 '750':47,48,49,54 '754':51,52,53 '77':5,6 '79':1,2,8,12,46,55 '8':9 '812':10,11,15 '815':13,14,17 '817':16,19 '819':18 '82':4 '823':22,26 '826':24,25,32 '828':27 '830':29 '832':28,30,31,33 '833':35,39 '835':34,37 '837':36 '839':38,41 '84':3,7 '841':40,43 '843':42 '846':20,21,23,44,45,50 '850':47,48,49,54 '854':51,52,53 '87':5,6 '89':1,2,8,12,46,55
3483cf23-56f3-48f0-9ce6-5b37f8022282	'1,':5,16,21,28 '1;':40 '1Whereas':1 '1a':18 '1against':24 '1and':26 '1as':17 '1be':11,33 '1by':35 '1compelled':12 '1essential':4 '1have':14 '1human':30 '1if':6 '1is':3,8 '1it':2 '1last':19 '1law':39 '1man':7 '1not':9 '1of':38 '1oppression':27 '1protected':34 '1rebellion':23 '1recourse':15 '1resort':20 '1rights':31 '1rule':37 '1should':32 '1that':29 '1the':36 '1to':10,13,22 '1tyranny':25 '2,':5,16,21,28 '2;':40 '2a':18 '2against':24 '2and':26 '2as':17 '2be':3,8,11,33 '2by':35 '2compel':12 '2essential':4 '2have':14 '2human':30 '2if':6 '2it':2 '2last':19 '2law':39 '2man':7 '2not':9 '2of':38 '2oppression':27 '2protect':34 '2rebellion':23 '2recourse':15 '2resort':20 '2right':31 '2rule':37 '2shall':32 '2that':29 '2the':36 '2to':10,13,22 '2tyranny':25 '2whereas':1 '3ADJ':4,19,30 '3ADP':17,22,24,35,38 '3AUX':3,11,32,33 '3CCONJ':26 '3DET':18,36 '3NOUN':7,15,20,23,25,27,31,37,39 '3PART':9,10,13 '3PRON':2 '3PUNCT':5,16,21,28,40 '3SCONJ':1,6,29 '3VERB':8,12,14,34 '4A':4,30 '4CC':26 '4CS':1,6,29 '4E':17,22,24,35,38 '4FC':40 '4FF':5,16,21,28 '4NO':19 '4PART':9,10,13 '4PE':2 '4RD':36 '4RI':18 '4S':7,15,20,23,25,27,31,37,39 '4V':3,8,12,14,34 '4VA':11,33 '4VM':32 '5':4 '512':10,11,14 '514':13,15 '515':16,20,21,23 '520':17,18,19 '523':22,25 '525':24,27 '527':26 '531':30 '534':29,31,32,33,37 '537':35,36,39 '539':38 '54':1,2,3,5,8,28,34,40 '58':6,7,9,12 '6':4 '612':10,11,14 '614':13,15 '615':16,20,21,23 '620':17,18,19 '623':22,25 '625':24,27 '627':26 '631':30 '634':29,31,32,33,37 '637':35,36,39 '639':38 '64':1,2,3,5,8,28,34,40 '68':6,7,9,12 '7':4 '712':10,11,14 '714':13,15 '715':16,20,21,23 '720':17,18,19 '723':22,25 '725':24,27 '727':26 '731':30 '734':29,31,32,33,37 '737':35,36,39 '739':38 '74':1,2,3,5,8,28,34,40 '78':6,7,9,12 '8':4 '812':10,11,14 '814':13,15 '815':16,20,21,23 '820':17,18,19 '823':22,25 '825':24,27 '827':26 '831':30 '834':29,31,32,33,37 '837':35,36,39 '839':38 '84':1,2,3,5,8,28,34,40 '88':6,7,9,12
2d673716-a575-438f-b3ff-dfe43a8c8bb3	'1,':19 '1;':53 '1Charter':11 '1Nations':7 '1United':6 '1Whereas':1 '1and':23,29,36,38,45 '1better':46 '1determined':40 '1dignity':22 '1equal':32 '1faith':14 '1freedom':52 '1fundamental':16 '1have':8,39 '1human':17,27 '1in':9,15,20,30,50 '1larger':51 '1life':49 '1men':35 '1of':4,25,34,48 '1peoples':3 '1person':28 '1progress':44 '1promote':42 '1reaffirmed':12 '1rights':18,33 '1social':43 '1standards':47 '1the':2,5,10,21,26,31 '1their':13 '1to':41 '1women':37 '1worth':24 '2,':19 '2;':53 '2Nations':7 '2United':6 '2and':23,29,36,38,45 '2better':46 '2charter':11 '2determine':40 '2dignity':22 '2equal':32 '2faith':14 '2freedom':52 '2fundamental':16 '2have':8,39 '2human':17,27 '2in':9,15,20,30,50 '2larger':51 '2life':49 '2man':35 '2of':4,25,34,48 '2people':3 '2person':28 '2progress':44 '2promote':42 '2reaffirm':12 '2right':18,33 '2social':43 '2standard':47 '2the':2,5,10,21,26,31 '2their':13 '2to':41 '2whereas':1 '2women':37 '2worth':24 '3ADJ':16,17,27,32,43,46,51 '3ADP':4,9,15,20,25,30,34,48,50 '3AUX':8,39 '3CCONJ':23,29,36,38,45 '3DET':2,5,10,13,21,26,31 '3NOUN':3,11,14,18,22,24,28,33,35,37,44,47,49,52 '3PART':41 '3PROPN':6,7 '3PUNCT':19,53 '3SCONJ':1 '3VERB':12,40,42 '4A':16,17,27,32,43,46,51 '4AP':13 '4CC':23,29,36,38,45 '4CS':1 '4E':4,9,15,20,25,30,34,48,50 '4FC':53 '4FF':19 '4PART':41 '4RD':2,5,10,21,26,31 '4S':3,11,14,18,22,24,28,33,35,37,44,47,49,52 '4SP':6,7 '4V':12,40,42 '4VA':8,39 '5':12 '511':9,10 '512':1,3,8,11,14,40,53 '514':13,18 '518':15,16,17,22,24,33 '522':19,20,21 '524':23,28 '528':25,26,27 '53':2,6 '533':29,30,31,32,35 '535':34,37 '537':36 '540':38,39,42 '542':41,44,52 '544':43,47 '547':45,46,49 '549':48 '552':50,51 '56':4,5,7 '6':12 '611':9,10 '612':1,3,8,11,14,40,53 '614':13,18 '618':15,16,17,22,24,33 '622':19,20,21 '624':23,28 '628':25,26,27 '63':2,6 '633':29,30,31,32,35 '635':34,37 '637':36 '640':38,39,42 '642':41,44,52 '644':43,47 '647':45,46,49 '649':48 '652':50,51 '66':4,5,7 '7':12 '711':9,10 '712':1,3,8,11,14,40,53 '714':13,18 '718':15,16,17,22,24,33 '722':19,20,21 '724':23,28 '728':25,26,27 '73':2,6 '733':29,30,31,32,35 '735':34,37 '737':36 '740':38,39,42 '742':41,44,52 '744':43,47 '747':45,46,49 '749':48 '752':50,51 '76':4,5,7 '8':12 '811':9,10 '812':1,3,8,11,14,40,53 '814':13,18 '818':15,16,17,22,24,33 '822':19,20,21 '824':23,28 '828':25,26,27 '83':2,6 '833':29,30,31,32,35 '835':34,37 '837':36 '840':38,39,42 '842':41,44,52 '844':43,47 '847':45,46,49 '849':48 '852':50,51 '86':4,5,7
\.


--
-- Data for Name: fts_vector4; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector4 (segment_id, vector) FROM stdin;
\.


--
-- Data for Name: fts_vector5; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector5 (segment_id, vector) FROM stdin;
\.


--
-- Data for Name: fts_vector6; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector6 (segment_id, vector) FROM stdin;
\.


--
-- Data for Name: fts_vector7; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector7 (segment_id, vector) FROM stdin;
\.


--
-- Data for Name: fts_vector8; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector8 (segment_id, vector) FROM stdin;
\.


--
-- Data for Name: fts_vector9; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector9 (segment_id, vector) FROM stdin;
\.


--
-- Data for Name: fts_vectorrest; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vectorrest (segment_id, vector) FROM stdin;
\.


--
-- Data for Name: namedentity; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity (namedentity_id, form_id, type, frame_range, char_range) FROM stdin;
1	1	ORG	[62,78)	[67,83)
2	2	DATE	[90,105)	[112,128)
3	3	ORG	[1302,1311)	[776,790)
4	4	DOC	[1326,1331)	[803,810)
\.


--
-- Data for Name: namedentity_form; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity_form (form_id, form) FROM stdin;
1	General Assembly
2	10 December 1948
3	United Nations
4	the Charter
\.


--
-- Data for Name: prepared_segment; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.prepared_segment (segment_id, id_offset, content, annotations) FROM stdin;
74672be2-f834-48ed-8e7d-e68f2728302c	24	[["PREAMBLE", "preamble", {"Number": "Sing"}, "NOUN", "S", null], [".", ".", null, "PUNCT", "FS", 24]]	{}
49732404-e110-4108-a9df-03a1e00e9071	7	[["Adopted", "adopt", {"Tense": "Past", "VerbForm": "Part"}, "VERB", "V", null], ["and", "and", null, "CCONJ", "CC", 9], ["proclaimed", "proclaim", {"Tense": "Past", "VerbForm": "Part"}, "VERB", "V", 7], ["by", "by", null, "ADP", "E", 13], ["General", "general", {"Degree": "Pos"}, "ADJ", "A", 12], ["Assembly", "assembly", {"Number": "Sing"}, "NOUN", "S", 13], ["resolution", "resolution", {"Number": "Sing"}, "NOUN", "S", 9], ["217", "217", {"NumType": "Card"}, "NUM", "N", 13], ["A", "A", null, "X", "X", 14], ["(", "(", null, "PUNCT", "FB", 17], ["III", "third", {"Degree": "Pos", "NumType": "Ord"}, "ADJ", "NO", 14], [")", ")", null, "PUNCT", "FB", 17], ["of", "of", null, "ADP", "E", 20], ["10", "10", {"NumType": "Card"}, "NUM", "N", 13], ["December", "December", null, "PROPN", "SP", 20], ["1948", "1948", {"NumType": "Card"}, "NUM", "N", 20], [".", ".", null, "PUNCT", "FS", 7]]	{"NamedEntity": [[11, 2, {"form": "General Assembly", "type": "ORG"}], [20, 3, {"form": "10 December 1948", "type": "DATE"}]]}
98c5a367-7235-4411-8a6b-adb705c956f0	1	[["Universal", "universal", {"Degree": "Pos"}, "ADJ", "A", 2], ["Declaration", "declare", {"Number": "Sing"}, "NOUN", "S", null], ["of", "of", null, "ADP", "E", 5], ["Human", "human", {"Degree": "Pos"}, "ADJ", "A", 5], ["Rights", "right", {"Number": "Plur"}, "NOUN", "S", 2], [".", ".", null, "PUNCT", "FS", 2]]	{}
df57ef44-4c6d-470a-9eb3-13402efa0413	121	[["Whereas", "whereas", null, "SCONJ", "CS", 124], ["it", "it", {"Number": "Sing", "Person": "3", "PronType": "Prs"}, "PRON", "PE", 124], ["is", "be", {"Mood": "Ind", "Tense": "Pres", "Number": "Sing", "Person": "3", "VerbForm": "Fin"}, "AUX", "V", 124], ["essential", "essential", {"Degree": "Pos"}, "ADJ", "A", null], ["to", "to", null, "PART", "PART", 126], ["promote", "promote", {"VerbForm": "Inf"}, "VERB", "V", 124], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", 128], ["development", "development", {"Number": "Sing"}, "NOUN", "S", 126], ["of", "of", null, "ADP", "E", 131], ["friendly", "friendly", {"Degree": "Pos"}, "ADJ", "A", 131], ["relations", "relation", {"Number": "Plur"}, "NOUN", "S", 128], ["between", "between", null, "ADP", "E", 133], ["nations", "nation", {"Number": "Plur"}, "NOUN", "S", 131], [";", ";", null, "PUNCT", "FC", 124]]	{}
235cde54-45f6-4262-922f-87b6ffe969ed	26	[["Whereas", "whereas", null, "SCONJ", "CS", 34], ["disregard", "disregard", {"Number": "Sing"}, "NOUN", "S", 34], ["and", "and", null, "CCONJ", "CC", 29], ["contempt", "contempt", {"Number": "Sing"}, "NOUN", "S", 27], ["for", "for", null, "ADP", "E", 32], ["human", "human", {"Degree": "Pos"}, "ADJ", "A", 32], ["rights", "right", {"Number": "Plur"}, "NOUN", "S", 29], ["have", "have", {"Mood": "Ind", "Tense": "Pres", "Number": "Plur", "VerbForm": "Fin"}, "AUX", "VA", 34], ["resulted", "result", {"Tense": "Past", "VerbForm": "Part"}, "VERB", "V", null], ["in", "in", null, "ADP", "E", 37], ["barbarous", "barbarous", {"Degree": "Pos"}, "ADJ", "A", 37], ["acts", "act", {"Number": "Plur"}, "NOUN", "S", 34], ["which", "which", {"PronType": "Rel"}, "PRON", "PR", 40], ["have", "have", {"Mood": "Ind", "Tense": "Pres", "Number": "Plur", "VerbForm": "Fin"}, "AUX", "VA", 40], ["outraged", "outrage", {"Tense": "Past", "VerbForm": "Part"}, "VERB", "V", 37], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", 42], ["conscience", "conscience", {"Number": "Sing"}, "NOUN", "S", 40], ["of", "of", null, "ADP", "E", 44], ["mankind", "mankind", {"Number": "Sing"}, "NOUN", "S", 42], [",", ",", null, "PUNCT", "FF", 71], ["and", "and", null, "CCONJ", "CC", 71], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", 48], ["advent", "advent", {"Number": "Sing"}, "NOUN", "S", 71], ["of", "of", null, "ADP", "E", 51], ["a", "a", {"Number": "Sing", "Definite": "Ind", "PronType": "Art"}, "DET", "RI", 51], ["world", "world", {"Number": "Sing"}, "NOUN", "S", 48], ["in", "in", null, "ADP", "E", 53], ["which", "which", {"PronType": "Rel"}, "PRON", "PR", 57], ["human", "human", {"Degree": "Pos"}, "ADJ", "A", 55], ["beings", "being", {"Number": "Plur"}, "NOUN", "S", 57], ["shall", "shall", {"Mood": "Ind", "Tense": "Pres", "Person": "3", "VerbForm": "Fin"}, "AUX", "VM", 57], ["enjoy", "enjoy", {"VerbForm": "Inf"}, "VERB", "V", 51], ["freedom", "freedom", {"Number": "Sing"}, "NOUN", "S", 57], ["of", "of", null, "ADP", "E", 60], ["speech", "speech", {"Number": "Sing"}, "NOUN", "S", 58], ["and", "and", null, "CCONJ", "CC", 62], ["belief", "belief", {"Number": "Sing"}, "NOUN", "S", 60], ["and", "and", null, "CCONJ", "CC", 64], ["freedom", "freedom", {"Number": "Sing"}, "NOUN", "S", 58], ["from", "from", null, "ADP", "E", 66], ["fear", "fear", {"Number": "Sing"}, "NOUN", "S", 64], ["and", "and", null, "CCONJ", "CC", 68], ["want", "want", {"Number": "Sing"}, "NOUN", "S", 66], ["has", "have", {"Mood": "Ind", "Tense": "Pres", "Number": "Sing", "Person": "3", "VerbForm": "Fin"}, "AUX", "VA", 71], ["been", "be", {"Tense": "Past", "VerbForm": "Part"}, "AUX", "VA", 71], ["proclaimed", "proclaim", {"Tense": "Past", "VerbForm": "Part"}, "VERB", "V", 34], ["as", "as", null, "ADP", "E", 75], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", 75], ["highest", "highest", {"Degree": "Sup"}, "ADJ", "A", 75], ["aspiration", "aspiration", {"Number": "Sing"}, "NOUN", "S", 71], ["of", "of", null, "ADP", "E", 79], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", 79], ["common", "common", {"Degree": "Pos"}, "ADJ", "A", 79], ["people", "people", {"Number": "Plur"}, "NOUN", "S", 75], [";", ";", null, "PUNCT", "FC", 34]]	{}
3483cf23-56f3-48f0-9ce6-5b37f8022282	81	[["Whereas", "whereas", null, "SCONJ", "CS", 84], ["it", "it", {"Number": "Sing", "Person": "3", "PronType": "Prs"}, "PRON", "PE", 84], ["is", "be", {"Mood": "Ind", "Tense": "Pres", "Number": "Sing", "Person": "3", "VerbForm": "Fin"}, "AUX", "V", 84], ["essential", "essential", {"Degree": "Pos"}, "ADJ", "A", null], [",", ",", null, "PUNCT", "FF", 84], ["if", "if", null, "SCONJ", "CS", 88], ["man", "man", {"Gender": "Masc", "Number": "Sing"}, "NOUN", "S", 88], ["is", "be", {"Mood": "Ind", "Tense": "Pres", "Number": "Sing", "Person": "3", "VerbForm": "Fin"}, "VERB", "V", 84], ["not", "not", {"Polarity": "Neg"}, "PART", "PART", 88], ["to", "to", null, "PART", "PART", 92], ["be", "be", {"VerbForm": "Inf"}, "AUX", "VA", 92], ["compelled", "compel", {"Tense": "Past", "VerbForm": "Part"}, "VERB", "V", 88], ["to", "to", null, "PART", "PART", 94], ["have", "have", {"VerbForm": "Inf"}, "VERB", "V", 92], ["recourse", "recourse", {"Number": "Sing"}, "NOUN", "S", 94], [",", ",", null, "PUNCT", "FF", 95], ["as", "as", null, "ADP", "E", 100], ["a", "a", {"Number": "Sing", "Definite": "Ind", "PronType": "Art"}, "DET", "RI", 100], ["last", "last", {"Degree": "Pos", "NumType": "Ord"}, "ADJ", "NO", 100], ["resort", "resort", {"Number": "Sing"}, "NOUN", "S", 95], [",", ",", null, "PUNCT", "FF", 95], ["to", "to", null, "ADP", "E", 103], ["rebellion", "rebellion", {"Number": "Sing"}, "NOUN", "S", 95], ["against", "against", null, "ADP", "E", 105], ["tyranny", "tyranny", {"Number": "Sing"}, "NOUN", "S", 103], ["and", "and", null, "CCONJ", "CC", 107], ["oppression", "oppression", {"Number": "Sing"}, "NOUN", "S", 105], [",", ",", null, "PUNCT", "FF", 84], ["that", "that", null, "SCONJ", "CS", 114], ["human", "human", {"Degree": "Pos"}, "ADJ", "A", 111], ["rights", "right", {"Number": "Plur"}, "NOUN", "S", 114], ["should", "shall", {"Mood": "Ind", "Tense": "Past", "Person": "3", "VerbForm": "Fin"}, "AUX", "VM", 114], ["be", "be", {"VerbForm": "Inf"}, "AUX", "VA", 114], ["protected", "protect", {"Tense": "Past", "VerbForm": "Part"}, "VERB", "V", 84], ["by", "by", null, "ADP", "E", 117], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", 117], ["rule", "rule", {"Number": "Sing"}, "NOUN", "S", 114], ["of", "of", null, "ADP", "E", 119], ["law", "law", {"Number": "Sing"}, "NOUN", "S", 117], [";", ";", null, "PUNCT", "FC", 84]]	{}
2d673716-a575-438f-b3ff-dfe43a8c8bb3	135	[["Whereas", "whereas", null, "SCONJ", "CS", null], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", null], ["peoples", "people", {"Number": "Plur"}, "NOUN", "S", null], ["of", "of", null, "ADP", "E", null], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", null], ["United", "United", null, "PROPN", "SP", null], ["Nations", "Nations", null, "PROPN", "SP", null], ["have", "have", {"Mood": "Ind", "Tense": "Pres", "Number": "Plur", "VerbForm": "Fin"}, "AUX", "VA", null], ["in", "in", null, "ADP", "E", null], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", null], ["Charter", "charter", {"Number": "Sing"}, "NOUN", "S", null], ["reaffirmed", "reaffirm", {"Tense": "Past", "VerbForm": "Part"}, "VERB", "V", null], ["their", "their", {"Poss": "Yes", "PronType": "Prs"}, "DET", "AP", null], ["faith", "faith", {"Number": "Sing"}, "NOUN", "S", null], ["in", "in", null, "ADP", "E", null], ["fundamental", "fundamental", {"Degree": "Pos"}, "ADJ", "A", null], ["human", "human", {"Degree": "Pos"}, "ADJ", "A", null], ["rights", "right", {"Number": "Plur"}, "NOUN", "S", null], [",", ",", null, "PUNCT", "FF", null], ["in", "in", null, "ADP", "E", null], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", null], ["dignity", "dignity", {"Number": "Sing"}, "NOUN", "S", null], ["and", "and", null, "CCONJ", "CC", null], ["worth", "worth", {"Number": "Sing"}, "NOUN", "S", null], ["of", "of", null, "ADP", "E", null], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", null], ["human", "human", {"Degree": "Pos"}, "ADJ", "A", null], ["person", "person", {"Number": "Sing"}, "NOUN", "S", null], ["and", "and", null, "CCONJ", "CC", null], ["in", "in", null, "ADP", "E", null], ["the", "the", {"Definite": "Def", "PronType": "Art"}, "DET", "RD", null], ["equal", "equal", {"Degree": "Pos"}, "ADJ", "A", null], ["rights", "right", {"Number": "Plur"}, "NOUN", "S", null], ["of", "of", null, "ADP", "E", null], ["men", "man", {"Gender": "Masc", "Number": "Plur"}, "NOUN", "S", null], ["and", "and", null, "CCONJ", "CC", null], ["women", "women", {"Gender": "Fem", "Number": "Sing"}, "NOUN", "S", null], ["and", "and", null, "CCONJ", "CC", null], ["have", "have", {"Mood": "Ind", "Tense": "Pres", "Number": "Plur", "Person": "3", "VerbForm": "Fin"}, "AUX", "VA", null], ["determined", "determine", {"Tense": "Past", "VerbForm": "Part"}, "VERB", "V", null], ["to", "to", null, "PART", "PART", null], ["promote", "promote", {"VerbForm": "Inf"}, "VERB", "V", null], ["social", "social", {"Degree": "Pos"}, "ADJ", "A", null], ["progress", "progress", {"Number": "Sing"}, "NOUN", "S", null], ["and", "and", null, "CCONJ", "CC", null], ["better", "better", {"Degree": "Cmp"}, "ADJ", "A", null], ["standards", "standard", {"Number": "Plur"}, "NOUN", "S", null], ["of", "of", null, "ADP", "E", null], ["life", "life", {"Number": "Sing"}, "NOUN", "S", null], ["in", "in", null, "ADP", "E", null], ["larger", "larger", {"Degree": "Cmp"}, "ADJ", "A", null], ["freedom", "freedom", {"Number": "Sing"}, "NOUN", "S", null], [";", ";", null, "PUNCT", "FC", null]]	{"NamedEntity": [[140, 2, {"form": "United Nations", "type": "ORG"}], [145, 1, {"form": "the Charter", "type": "DOC"}]]}
\.


--
-- Data for Name: segment1; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1 (segment_id, meta, frame_range, char_range) FROM stdin;
98c5a367-7235-4411-8a6b-adb705c956f0	{"end": "1.50", "text": "Universal Declaration of Human Rights.", "start": "0.50"}	[12,37)	[1,40)
df57ef44-4c6d-470a-9eb3-13402efa0413	{"end": "50.20", "text": "Whereas it is essential to promote the development of friendly relations between nations;", "start": "44.33"}	[1108,1255)	[658,748)
\.


--
-- Data for Name: segment2; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2 (segment_id, meta, frame_range, char_range) FROM stdin;
49732404-e110-4108-a9df-03a1e00e9071	{"end": "4.25", "text": "Adopted and proclaimed by General Assembly resolution 217A (III) of 10 December 1948.", "start": "2.20"}	[55,107)	[41,130)
74672be2-f834-48ed-8e7d-e68f2728302c	{"end": "5.00", "text": "PREAMBLE.", "start": "4.75"}	[118,125)	[131,141)
\.


--
-- Data for Name: segment3; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3 (segment_id, meta, frame_range, char_range) FROM stdin;
235cde54-45f6-4262-922f-87b6ffe969ed	{"end": "22.50", "text": "Whereas disregard and contempt for human rights have resulted in barbarous acts which have outraged the conscience of mankind, and the advent of a world in which human beings shall enjoy freedom of speech and belief and freedom from fear and want has been proclaimed as the highest aspiration of the common people;", "start": "7.00"}	[175,562)	[142,458)
3483cf23-56f3-48f0-9ce6-5b37f8022282	{"end": "42.40", "text": "Whereas it is essential, if man is not to be compelled to have recourse, as a last resort, to rebellion against tyranny and oppression, that human rights should be protected by the rule of law;", "start": "28.00"}	[700,1060)	[459,657)
2d673716-a575-438f-b3ff-dfe43a8c8bb3	{"end": "61.50", "text": "Whereas the peoples of the United Nations have in the Charter reaffirmed their faith in fundamental human rights, in the dignity and worth of the human person and in the equal rights of men and women and have determined to promote social progress and better standards of life in larger freedom;", "start": "51.10"}	[1277,1537)	[749,1045)
\.


--
-- Data for Name: segment4; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4 (segment_id, meta, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: segment5; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5 (segment_id, meta, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: segment6; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6 (segment_id, meta, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: segment7; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7 (segment_id, meta, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: segment8; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8 (segment_id, meta, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: segment9; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9 (segment_id, meta, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: segmentrest; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest (segment_id, meta, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: shot; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.shot (shot_id, view, frame_range) FROM stdin;
1	wide angle	[0,200)
2	low angle	[201,312)
3	face-cam	[318,400)
4	closeup	[405,518)
5	reverse	[525,575)
6	high angle	[576,622)
7	closeup	[625,687)
8	high angle	[688,801)
9	wide angle	[802,1047)
10	low angle	[1051,1076)
11	wide angle	[1077,1293)
12	high angle	[1297,1375)
13	medium closeup	[1377,1550)
\.


--
-- Data for Name: token1; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1 (token_id, form_id, lemma_id, upos, xpos, ufeat_id, segment_id, frame_range, char_range) FROM stdin;
1	1	1	ADJ	A	1	98c5a367-7235-4411-8a6b-adb705c956f0	[12,18)	[1,10)
2	2	2	NOUN	S	2	98c5a367-7235-4411-8a6b-adb705c956f0	[19,23)	[11,22)
3	3	3	ADP	E	3	98c5a367-7235-4411-8a6b-adb705c956f0	[25,28)	[23,25)
4	4	4	ADJ	A	1	98c5a367-7235-4411-8a6b-adb705c956f0	[30,33)	[26,31)
5	5	5	NOUN	S	4	98c5a367-7235-4411-8a6b-adb705c956f0	[33,36)	[32,38)
6	6	6	PUNCT	FS	3	98c5a367-7235-4411-8a6b-adb705c956f0	[36,37)	[39,40)
121	23	23	SCONJ	CS	3	df57ef44-4c6d-470a-9eb3-13402efa0413	[1108,1118)	[658,665)
122	60	57	PRON	PE	16	df57ef44-4c6d-470a-9eb3-13402efa0413	[1118,1129)	[666,668)
123	61	50	AUX	V	14	df57ef44-4c6d-470a-9eb3-13402efa0413	[1129,1139)	[669,671)
124	62	58	ADJ	A	1	df57ef44-4c6d-470a-9eb3-13402efa0413	[1139,1150)	[672,681)
125	66	62	PART	PART	3	df57ef44-4c6d-470a-9eb3-13402efa0413	[1150,1160)	[682,684)
126	81	75	VERB	V	13	df57ef44-4c6d-470a-9eb3-13402efa0413	[1160,1171)	[685,692)
127	36	34	DET	RD	10	df57ef44-4c6d-470a-9eb3-13402efa0413	[1171,1181)	[693,696)
128	82	76	NOUN	S	2	df57ef44-4c6d-470a-9eb3-13402efa0413	[1181,1192)	[697,708)
129	3	3	ADP	E	3	df57ef44-4c6d-470a-9eb3-13402efa0413	[1192,1202)	[709,711)
130	83	77	ADJ	A	1	df57ef44-4c6d-470a-9eb3-13402efa0413	[1202,1213)	[712,720)
131	84	78	NOUN	S	4	df57ef44-4c6d-470a-9eb3-13402efa0413	[1213,1223)	[721,730)
132	85	79	ADP	E	3	df57ef44-4c6d-470a-9eb3-13402efa0413	[1223,1234)	[731,738)
133	86	80	NOUN	S	4	df57ef44-4c6d-470a-9eb3-13402efa0413	[1234,1244)	[739,746)
134	59	56	PUNCT	FC	3	df57ef44-4c6d-470a-9eb3-13402efa0413	[1244,1255)	[747,748)
\.


--
-- Data for Name: token2; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2 (token_id, form_id, lemma_id, upos, xpos, ufeat_id, segment_id, frame_range, char_range) FROM stdin;
7	7	7	VERB	V	5	49732404-e110-4108-a9df-03a1e00e9071	[55,57)	[41,48)
8	8	8	CCONJ	CC	3	49732404-e110-4108-a9df-03a1e00e9071	[57,58)	[49,52)
9	9	9	VERB	V	5	49732404-e110-4108-a9df-03a1e00e9071	[59,61)	[53,63)
10	10	10	ADP	E	3	49732404-e110-4108-a9df-03a1e00e9071	[61,62)	[64,66)
11	11	11	ADJ	A	1	49732404-e110-4108-a9df-03a1e00e9071	[63,68)	[67,74)
12	12	12	NOUN	S	2	49732404-e110-4108-a9df-03a1e00e9071	[71,78)	[75,83)
13	13	13	NOUN	S	2	49732404-e110-4108-a9df-03a1e00e9071	[80,81)	[84,94)
14	14	14	NUM	N	6	49732404-e110-4108-a9df-03a1e00e9071	[81,85)	[95,98)
15	15	15	X	X	3	49732404-e110-4108-a9df-03a1e00e9071	[85,86)	[99,100)
16	16	16	PUNCT	FB	3	49732404-e110-4108-a9df-03a1e00e9071	[86,87)	[101,102)
17	17	17	ADJ	NO	7	49732404-e110-4108-a9df-03a1e00e9071	[86,88)	[103,106)
18	18	18	PUNCT	FB	3	49732404-e110-4108-a9df-03a1e00e9071	[88,89)	[107,108)
19	3	3	ADP	E	3	49732404-e110-4108-a9df-03a1e00e9071	[88,90)	[109,111)
20	19	19	NUM	N	6	49732404-e110-4108-a9df-03a1e00e9071	[93,101)	[112,114)
21	20	20	PROPN	SP	3	49732404-e110-4108-a9df-03a1e00e9071	[102,103)	[115,123)
22	21	21	NUM	N	6	49732404-e110-4108-a9df-03a1e00e9071	[103,105)	[124,128)
23	6	6	PUNCT	FS	3	49732404-e110-4108-a9df-03a1e00e9071	[106,107)	[129,130)
24	22	22	NOUN	S	2	74672be2-f834-48ed-8e7d-e68f2728302c	[118,124)	[131,139)
25	6	6	PUNCT	FS	3	74672be2-f834-48ed-8e7d-e68f2728302c	[124,125)	[140,141)
\.


--
-- Data for Name: token3; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3 (token_id, form_id, lemma_id, upos, xpos, ufeat_id, segment_id, frame_range, char_range) FROM stdin;
26	23	23	SCONJ	CS	3	235cde54-45f6-4262-922f-87b6ffe969ed	[175,182)	[142,149)
27	24	24	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[182,189)	[150,159)
28	8	8	CCONJ	CC	3	235cde54-45f6-4262-922f-87b6ffe969ed	[189,196)	[160,163)
29	25	25	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[196,202)	[164,172)
30	26	26	ADP	E	3	235cde54-45f6-4262-922f-87b6ffe969ed	[202,210)	[173,176)
31	27	4	ADJ	A	1	235cde54-45f6-4262-922f-87b6ffe969ed	[210,217)	[177,182)
32	28	5	NOUN	S	4	235cde54-45f6-4262-922f-87b6ffe969ed	[217,224)	[183,189)
33	29	27	AUX	VA	8	235cde54-45f6-4262-922f-87b6ffe969ed	[224,231)	[190,194)
34	30	28	VERB	V	5	235cde54-45f6-4262-922f-87b6ffe969ed	[231,238)	[195,203)
35	31	29	ADP	E	3	235cde54-45f6-4262-922f-87b6ffe969ed	[238,245)	[204,206)
36	32	30	ADJ	A	1	235cde54-45f6-4262-922f-87b6ffe969ed	[245,252)	[207,216)
37	33	31	NOUN	S	4	235cde54-45f6-4262-922f-87b6ffe969ed	[252,259)	[217,221)
38	34	32	PRON	PR	9	235cde54-45f6-4262-922f-87b6ffe969ed	[259,266)	[222,227)
39	29	27	AUX	VA	8	235cde54-45f6-4262-922f-87b6ffe969ed	[266,273)	[228,232)
40	35	33	VERB	V	5	235cde54-45f6-4262-922f-87b6ffe969ed	[273,280)	[233,241)
41	36	34	DET	RD	10	235cde54-45f6-4262-922f-87b6ffe969ed	[280,287)	[242,245)
42	37	35	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[287,294)	[246,256)
43	3	3	ADP	E	3	235cde54-45f6-4262-922f-87b6ffe969ed	[294,301)	[257,259)
44	38	36	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[301,308)	[260,267)
45	39	37	PUNCT	FF	3	235cde54-45f6-4262-922f-87b6ffe969ed	[308,315)	[268,269)
46	8	8	CCONJ	CC	3	235cde54-45f6-4262-922f-87b6ffe969ed	[315,322)	[270,273)
47	36	34	DET	RD	10	235cde54-45f6-4262-922f-87b6ffe969ed	[322,330)	[274,277)
48	40	38	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[330,337)	[278,284)
49	3	3	ADP	E	3	235cde54-45f6-4262-922f-87b6ffe969ed	[337,344)	[285,287)
50	41	39	DET	RI	11	235cde54-45f6-4262-922f-87b6ffe969ed	[344,351)	[288,289)
51	42	40	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[351,358)	[290,295)
52	31	29	ADP	E	3	235cde54-45f6-4262-922f-87b6ffe969ed	[358,365)	[296,298)
53	34	32	PRON	PR	9	235cde54-45f6-4262-922f-87b6ffe969ed	[365,372)	[299,304)
54	27	4	ADJ	A	1	235cde54-45f6-4262-922f-87b6ffe969ed	[372,379)	[305,310)
55	43	41	NOUN	S	4	235cde54-45f6-4262-922f-87b6ffe969ed	[379,386)	[311,317)
56	44	42	AUX	VM	12	235cde54-45f6-4262-922f-87b6ffe969ed	[386,393)	[318,323)
57	45	43	VERB	V	13	235cde54-45f6-4262-922f-87b6ffe969ed	[393,400)	[324,329)
58	46	44	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[400,407)	[330,337)
59	3	3	ADP	E	3	235cde54-45f6-4262-922f-87b6ffe969ed	[407,414)	[338,340)
60	47	45	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[414,421)	[341,347)
61	8	8	CCONJ	CC	3	235cde54-45f6-4262-922f-87b6ffe969ed	[421,428)	[348,351)
62	48	46	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[428,435)	[352,358)
63	8	8	CCONJ	CC	3	235cde54-45f6-4262-922f-87b6ffe969ed	[435,442)	[359,362)
64	46	44	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[442,449)	[363,370)
65	49	47	ADP	E	3	235cde54-45f6-4262-922f-87b6ffe969ed	[449,456)	[371,375)
66	50	48	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[456,463)	[376,380)
67	8	8	CCONJ	CC	3	235cde54-45f6-4262-922f-87b6ffe969ed	[463,470)	[381,384)
68	51	49	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[470,477)	[385,389)
69	52	27	AUX	VA	14	235cde54-45f6-4262-922f-87b6ffe969ed	[477,484)	[390,393)
70	53	50	AUX	VA	5	235cde54-45f6-4262-922f-87b6ffe969ed	[484,492)	[394,398)
71	9	9	VERB	V	5	235cde54-45f6-4262-922f-87b6ffe969ed	[492,499)	[399,409)
72	54	51	ADP	E	3	235cde54-45f6-4262-922f-87b6ffe969ed	[499,505)	[410,412)
73	36	34	DET	RD	10	235cde54-45f6-4262-922f-87b6ffe969ed	[505,513)	[413,416)
74	55	52	ADJ	A	15	235cde54-45f6-4262-922f-87b6ffe969ed	[513,520)	[417,424)
75	56	53	NOUN	S	2	235cde54-45f6-4262-922f-87b6ffe969ed	[520,527)	[425,435)
76	3	3	ADP	E	3	235cde54-45f6-4262-922f-87b6ffe969ed	[527,534)	[436,438)
77	36	34	DET	RD	10	235cde54-45f6-4262-922f-87b6ffe969ed	[534,541)	[439,442)
78	57	54	ADJ	A	1	235cde54-45f6-4262-922f-87b6ffe969ed	[541,548)	[443,449)
79	58	55	NOUN	S	4	235cde54-45f6-4262-922f-87b6ffe969ed	[548,555)	[450,456)
80	59	56	PUNCT	FC	3	235cde54-45f6-4262-922f-87b6ffe969ed	[555,562)	[457,458)
81	23	23	SCONJ	CS	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[700,709)	[459,466)
82	60	57	PRON	PE	16	3483cf23-56f3-48f0-9ce6-5b37f8022282	[709,718)	[467,469)
83	61	50	AUX	V	14	3483cf23-56f3-48f0-9ce6-5b37f8022282	[718,727)	[470,472)
84	62	58	ADJ	A	1	3483cf23-56f3-48f0-9ce6-5b37f8022282	[727,736)	[473,482)
85	39	37	PUNCT	FF	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[736,745)	[483,484)
86	63	59	SCONJ	CS	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[745,754)	[485,487)
87	64	60	NOUN	S	17	3483cf23-56f3-48f0-9ce6-5b37f8022282	[754,763)	[488,491)
88	61	50	VERB	V	14	3483cf23-56f3-48f0-9ce6-5b37f8022282	[763,772)	[492,494)
89	65	61	PART	PART	18	3483cf23-56f3-48f0-9ce6-5b37f8022282	[772,781)	[495,498)
90	66	62	PART	PART	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[781,790)	[499,501)
91	67	50	AUX	VA	13	3483cf23-56f3-48f0-9ce6-5b37f8022282	[790,799)	[502,504)
92	68	63	VERB	V	5	3483cf23-56f3-48f0-9ce6-5b37f8022282	[799,808)	[505,514)
93	66	62	PART	PART	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[808,817)	[515,517)
94	29	27	VERB	V	13	3483cf23-56f3-48f0-9ce6-5b37f8022282	[817,826)	[518,522)
95	69	64	NOUN	S	2	3483cf23-56f3-48f0-9ce6-5b37f8022282	[826,835)	[523,531)
96	39	37	PUNCT	FF	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[835,844)	[532,533)
97	54	51	ADP	E	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[844,852)	[534,536)
98	41	39	DET	RI	11	3483cf23-56f3-48f0-9ce6-5b37f8022282	[852,861)	[537,538)
99	70	65	ADJ	NO	7	3483cf23-56f3-48f0-9ce6-5b37f8022282	[861,870)	[539,543)
100	71	66	NOUN	S	2	3483cf23-56f3-48f0-9ce6-5b37f8022282	[870,880)	[544,550)
101	39	37	PUNCT	FF	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[880,889)	[551,552)
102	66	62	ADP	E	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[889,898)	[553,555)
103	72	67	NOUN	S	2	3483cf23-56f3-48f0-9ce6-5b37f8022282	[898,907)	[556,565)
104	73	68	ADP	E	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[907,916)	[566,573)
105	74	69	NOUN	S	2	3483cf23-56f3-48f0-9ce6-5b37f8022282	[916,925)	[574,581)
106	8	8	CCONJ	CC	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[925,934)	[582,585)
107	75	70	NOUN	S	2	3483cf23-56f3-48f0-9ce6-5b37f8022282	[934,943)	[586,596)
108	39	37	PUNCT	FF	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[943,952)	[597,598)
109	76	71	SCONJ	CS	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[952,961)	[599,603)
110	27	4	ADJ	A	1	3483cf23-56f3-48f0-9ce6-5b37f8022282	[961,969)	[604,609)
111	28	5	NOUN	S	4	3483cf23-56f3-48f0-9ce6-5b37f8022282	[969,978)	[610,616)
112	77	42	AUX	VM	19	3483cf23-56f3-48f0-9ce6-5b37f8022282	[978,987)	[617,623)
113	67	50	AUX	VA	13	3483cf23-56f3-48f0-9ce6-5b37f8022282	[987,996)	[624,626)
114	78	72	VERB	V	5	3483cf23-56f3-48f0-9ce6-5b37f8022282	[996,1005)	[627,636)
115	10	10	ADP	E	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[1005,1014)	[637,639)
116	36	34	DET	RD	10	3483cf23-56f3-48f0-9ce6-5b37f8022282	[1014,1024)	[640,643)
117	79	73	NOUN	S	2	3483cf23-56f3-48f0-9ce6-5b37f8022282	[1024,1033)	[644,648)
118	3	3	ADP	E	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[1033,1042)	[649,651)
119	80	74	NOUN	S	2	3483cf23-56f3-48f0-9ce6-5b37f8022282	[1042,1051)	[652,655)
120	59	56	PUNCT	FC	3	3483cf23-56f3-48f0-9ce6-5b37f8022282	[1051,1060)	[656,657)
135	23	23	SCONJ	CS	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1277,1282)	[749,756)
136	36	34	DET	RD	10	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1282,1287)	[757,760)
137	87	55	NOUN	S	4	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1287,1292)	[761,768)
138	3	3	ADP	E	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1292,1297)	[769,771)
139	36	34	DET	RD	10	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1297,1302)	[772,775)
140	88	81	PROPN	SP	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1302,1306)	[776,782)
141	89	82	PROPN	SP	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1306,1311)	[783,790)
142	29	27	AUX	VA	8	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1311,1316)	[791,795)
143	31	29	ADP	E	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1316,1321)	[796,798)
144	36	34	DET	RD	10	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1321,1326)	[799,802)
145	90	83	NOUN	S	2	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1326,1331)	[803,810)
146	91	84	VERB	V	5	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1331,1336)	[811,821)
147	92	85	DET	AP	20	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1336,1341)	[822,827)
148	93	86	NOUN	S	2	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1341,1346)	[828,833)
149	31	29	ADP	E	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1346,1351)	[834,836)
150	94	87	ADJ	A	1	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1351,1355)	[837,848)
151	27	4	ADJ	A	1	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1355,1360)	[849,854)
152	28	5	NOUN	S	4	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1360,1365)	[855,861)
153	39	37	PUNCT	FF	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1365,1370)	[862,863)
154	31	29	ADP	E	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1370,1375)	[864,866)
155	36	34	DET	RD	10	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1375,1380)	[867,870)
156	95	88	NOUN	S	2	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1380,1385)	[871,878)
157	8	8	CCONJ	CC	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1385,1390)	[879,882)
158	96	89	NOUN	S	2	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1390,1395)	[883,888)
159	3	3	ADP	E	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1395,1400)	[889,891)
160	36	34	DET	RD	10	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1400,1405)	[892,895)
161	27	4	ADJ	A	1	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1405,1409)	[896,901)
162	97	90	NOUN	S	2	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1409,1414)	[902,908)
163	8	8	CCONJ	CC	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1414,1419)	[909,912)
164	31	29	ADP	E	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1419,1424)	[913,915)
165	36	34	DET	RD	10	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1424,1429)	[916,919)
166	98	91	ADJ	A	1	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1429,1434)	[920,925)
167	28	5	NOUN	S	4	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1434,1439)	[926,932)
168	3	3	ADP	E	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1439,1444)	[933,935)
169	99	60	NOUN	S	21	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1444,1449)	[936,939)
170	8	8	CCONJ	CC	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1449,1454)	[940,943)
171	100	92	NOUN	S	22	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1454,1459)	[944,949)
172	8	8	CCONJ	CC	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1459,1463)	[950,953)
173	29	27	AUX	VA	23	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1463,1468)	[954,958)
174	101	93	VERB	V	5	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1468,1473)	[959,969)
175	66	62	PART	PART	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1473,1478)	[970,972)
176	81	75	VERB	V	13	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1478,1483)	[973,980)
177	102	94	ADJ	A	1	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1483,1488)	[981,987)
178	103	95	NOUN	S	2	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1488,1493)	[988,996)
179	8	8	CCONJ	CC	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1493,1498)	[997,1000)
180	104	96	ADJ	A	24	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1498,1503)	[1001,1007)
181	105	97	NOUN	S	4	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1503,1508)	[1008,1017)
182	3	3	ADP	E	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1508,1512)	[1018,1020)
183	106	98	NOUN	S	2	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1512,1517)	[1021,1025)
184	31	29	ADP	E	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1517,1522)	[1026,1028)
185	107	99	ADJ	A	24	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1522,1527)	[1029,1035)
186	46	44	NOUN	S	2	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1527,1532)	[1036,1043)
187	59	56	PUNCT	FC	3	2d673716-a575-438f-b3ff-dfe43a8c8bb3	[1532,1537)	[1044,1045)
\.


--
-- Data for Name: token4; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4 (token_id, form_id, lemma_id, upos, xpos, ufeat_id, segment_id, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: token5; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5 (token_id, form_id, lemma_id, upos, xpos, ufeat_id, segment_id, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: token6; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6 (token_id, form_id, lemma_id, upos, xpos, ufeat_id, segment_id, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: token7; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7 (token_id, form_id, lemma_id, upos, xpos, ufeat_id, segment_id, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: token8; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8 (token_id, form_id, lemma_id, upos, xpos, ufeat_id, segment_id, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: token9; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9 (token_id, form_id, lemma_id, upos, xpos, ufeat_id, segment_id, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: token_form; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_form (form_id, form) FROM stdin;
1	Universal
2	Declaration
3	of
4	Human
5	Rights
6	.
7	Adopted
8	and
9	proclaimed
10	by
11	General
12	Assembly
13	resolution
14	217
15	A
16	(
17	III
18	)
19	10
20	December
21	1948
22	PREAMBLE
23	Whereas
24	disregard
25	contempt
26	for
27	human
28	rights
29	have
30	resulted
31	in
32	barbarous
33	acts
34	which
35	outraged
36	the
37	conscience
38	mankind
39	,
40	advent
41	a
42	world
43	beings
44	shall
45	enjoy
46	freedom
47	speech
48	belief
49	from
50	fear
51	want
52	has
53	been
54	as
55	highest
56	aspiration
57	common
58	people
59	;
60	it
61	is
62	essential
63	if
64	man
65	not
66	to
67	be
68	compelled
69	recourse
70	last
71	resort
72	rebellion
73	against
74	tyranny
75	oppression
76	that
77	should
78	protected
79	rule
80	law
81	promote
82	development
83	friendly
84	relations
85	between
86	nations
87	peoples
88	United
89	Nations
90	Charter
91	reaffirmed
92	their
93	faith
94	fundamental
95	dignity
96	worth
97	person
98	equal
99	men
100	women
101	determined
102	social
103	progress
104	better
105	standards
106	life
107	larger
\.


--
-- Data for Name: token_lemma; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_lemma (lemma_id, lemma) FROM stdin;
1	universal
2	declare
3	of
4	human
5	right
6	.
7	adopt
8	and
9	proclaim
10	by
11	general
12	assembly
13	resolution
14	217
15	A
16	(
17	third
18	)
19	10
20	December
21	1948
22	preamble
23	whereas
24	disregard
25	contempt
26	for
27	have
28	result
29	in
30	barbarous
31	act
32	which
33	outrage
34	the
35	conscience
36	mankind
37	,
38	advent
39	a
40	world
41	being
42	shall
43	enjoy
44	freedom
45	speech
46	belief
47	from
48	fear
49	want
50	be
51	as
52	highest
53	aspiration
54	common
55	people
56	;
57	it
58	essential
59	if
60	man
61	not
62	to
63	compel
64	recourse
65	last
66	resort
67	rebellion
68	against
69	tyranny
70	oppression
71	that
72	protect
73	rule
74	law
75	promote
76	development
77	friendly
78	relation
79	between
80	nation
81	United
82	Nations
83	charter
84	reaffirm
85	their
86	faith
87	fundamental
88	dignity
89	worth
90	person
91	equal
92	women
93	determine
94	social
95	progress
96	better
97	standard
98	life
99	larger
\.


--
-- Data for Name: token_ufeat; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_ufeat (ufeat_id, ufeat) FROM stdin;
1	{"Degree": "Pos"}
2	{"Number": "Sing"}
3	\N
4	{"Number": "Plur"}
5	{"Tense": "Past", "VerbForm": "Part"}
6	{"NumType": "Card"}
7	{"Degree": "Pos", "NumType": "Ord"}
8	{"Mood": "Ind", "Tense": "Pres", "Number": "Plur", "VerbForm": "Fin"}
9	{"PronType": "Rel"}
10	{"Definite": "Def", "PronType": "Art"}
11	{"Number": "Sing", "Definite": "Ind", "PronType": "Art"}
12	{"Mood": "Ind", "Tense": "Pres", "Person": "3", "VerbForm": "Fin"}
13	{"VerbForm": "Inf"}
14	{"Mood": "Ind", "Tense": "Pres", "Number": "Sing", "Person": "3", "VerbForm": "Fin"}
15	{"Degree": "Sup"}
16	{"Number": "Sing", "Person": "3", "PronType": "Prs"}
17	{"Gender": "Masc", "Number": "Sing"}
18	{"Polarity": "Neg"}
19	{"Mood": "Ind", "Tense": "Past", "Person": "3", "VerbForm": "Fin"}
20	{"Poss": "Yes", "PronType": "Prs"}
21	{"Gender": "Masc", "Number": "Plur"}
22	{"Gender": "Fem", "Number": "Sing"}
23	{"Mood": "Ind", "Tense": "Pres", "Number": "Plur", "Person": "3", "VerbForm": "Fin"}
24	{"Degree": "Cmp"}
\.


--
-- Data for Name: tokenrest; Type: TABLE DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

COPY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest (token_id, form_id, lemma_id, upos, xpos, ufeat_id, segment_id, frame_range, char_range) FROM stdin;
\.


--
-- Data for Name: corpus; Type: TABLE DATA; Schema: main; Owner: postgres
--

COPY main.corpus (corpus_id, name, current_version, version_history, description, corpus_template, schema_path, token_counts, mapping, enabled, sample_query, project_id) FROM stdin;
195	Free Single-Video Corpus	1	\N	\N	{"meta": {"date": "2024-06-13", "name": "Free Single-Video Corpus", "author": "LiRI", "version": 1, "mediaSlots": {"video": {"mediaType": "video", "isOptional": false}}, "corpusDescription": "Single, open-source video with annotated shots and a placeholder text stream from the Universal Declaration of Human Rights annotated with named entities"}, "layer": {"Shot": {"abstract": false, "anchoring": {"time": true, "stream": false, "location": false}, "layerType": "span", "attributes": {"view": {"type": "categorical", "values": ["wide angle", "low angle", "face-cam", "closeup", "reverse", "high angle", "medium closeup"], "isGlobal": false, "nullable": false}}}, "Token": {"abstract": false, "anchoring": {"time": true, "stream": true, "location": false}, "layerType": "unit", "attributes": {"form": {"type": "text", "isGlobal": false, "nullable": true}, "upos": {"type": "categorical", "isGlobal": true, "nullable": true}, "xpos": {"type": "categorical", "values": ["AP", "CC", "VM", "FF", "SP", "V", "N", "FS", "PE", "A", "PART", "CS", "X", "FB", "RI", "RD", "VA", "E", "PR", "FC", "S", "NO"], "isGlobal": false, "nullable": true}, "lemma": {"type": "text", "isGlobal": false, "nullable": false}, "ufeat": {"type": "dict", "isGlobal": false, "nullable": true}}}, "DepRel": {"abstract": true, "layerType": "relation", "attributes": {"udep": {"type": "categorical", "isGlobal": true, "nullable": false}, "source": {"name": "dependent", "entity": "Token", "nullable": false}, "target": {"name": "head", "entity": "Token", "nullable": true}}}, "Segment": {"abstract": false, "contains": "Token", "layerType": "span", "attributes": {"meta": {"end": {"type": "text"}, "text": {"type": "text"}, "start": {"type": "text"}}}}, "Document": {"abstract": false, "contains": "Segment", "layerType": "span", "attributes": {"meta": {"end": {"type": "number"}, "name": {"type": "text"}, "audio": {"type": "text", "isOptional": true}, "start": {"type": "number"}, "video": {"type": "text", "isOptional": true}}}}, "NamedEntity": {"abstract": false, "contains": "Token", "layerType": "span", "attributes": {"form": {"type": "text", "isGlobal": false, "nullable": false}, "type": {"type": "categorical", "values": ["ORG", "DATE", "DOC"], "isGlobal": false, "nullable": true}}}}, "tracks": {"layers": {"Shot": {}, "Segment": {}, "NamedEntity": {}}}, "project": "848c1f0f-a1e3-4f6b-93da-4a7b26c6c6d9", "projects": ["848c1f0f-a1e3-4f6b-93da-4a7b26c6c6d9"], "uploaded": true, "firstClass": {"token": "Token", "segment": "Segment", "document": "Document"}, "schema_name": "free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1"}	free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1	{"token0": 187, "token1": 20, "token2": 19, "token3": 148, "token4": 0, "token5": 0, "token6": 0, "token7": 0, "token8": 0, "tokenrest": 0}	{"layer": {"Shot": {"relation": "shot"}, "Token": {"batches": 10, "relation": "token<batch>", "attributes": {"form": {"key": "form", "name": "token_form", "type": "relation"}, "lemma": {"key": "lemma", "name": "token_lemma", "type": "relation"}, "ufeat": {"name": "token_ufeat", "type": "relation"}}}, "DepRel": {"relation": "deprel"}, "Segment": {"hasMeta": true, "prepared": {"relation": "prepared_Segment", "columnHeaders": ["form", "lemma", "ufeat", "upos", "xpos", "head"]}, "relation": "segment<batch>"}, "Document": {"hasMeta": true, "relation": "document"}, "NamedEntity": {"relation": "namedentity", "attributes": {"form": {"key": "form", "name": "namedentity_form", "type": "relation"}}}}, "hasFTS": true, "FTSvectorCols": {"1": "form", "2": "lemma", "3": "upos", "4": "xpos", "5": "ufeat"}}	t	Segment s\n\nKWIC => plain\n    context\n        s\n    entities\n        s	848c1f0f-a1e3-4f6b-93da-4a7b26c6c6d9
\.


--
-- Data for Name: corpus_language; Type: TABLE DATA; Schema: main; Owner: postgres
--

COPY main.corpus_language (corpus_id, iso) FROM stdin;
\.


--
-- Name: corpus_corpus_id_seq; Type: SEQUENCE SET; Schema: main; Owner: postgres
--

SELECT pg_catalog.setval('main.corpus_corpus_id_seq', 197, true);


--
-- Name: document document_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.document
    ADD CONSTRAINT document_pkey PRIMARY KEY (document_id);


--
-- Name: fts_vector0 fts_vector0_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0
    ADD CONSTRAINT fts_vector0_pkey PRIMARY KEY (segment_id);


--
-- Name: fts_vector1 fts_vector1_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector1
    ADD CONSTRAINT fts_vector1_pkey PRIMARY KEY (segment_id);


--
-- Name: fts_vector2 fts_vector2_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector2
    ADD CONSTRAINT fts_vector2_pkey PRIMARY KEY (segment_id);


--
-- Name: fts_vector3 fts_vector3_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector3
    ADD CONSTRAINT fts_vector3_pkey PRIMARY KEY (segment_id);


--
-- Name: fts_vector4 fts_vector4_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector4
    ADD CONSTRAINT fts_vector4_pkey PRIMARY KEY (segment_id);


--
-- Name: fts_vector5 fts_vector5_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector5
    ADD CONSTRAINT fts_vector5_pkey PRIMARY KEY (segment_id);


--
-- Name: fts_vector6 fts_vector6_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector6
    ADD CONSTRAINT fts_vector6_pkey PRIMARY KEY (segment_id);


--
-- Name: fts_vector7 fts_vector7_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector7
    ADD CONSTRAINT fts_vector7_pkey PRIMARY KEY (segment_id);


--
-- Name: fts_vector8 fts_vector8_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector8
    ADD CONSTRAINT fts_vector8_pkey PRIMARY KEY (segment_id);


--
-- Name: fts_vector9 fts_vector9_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector9
    ADD CONSTRAINT fts_vector9_pkey PRIMARY KEY (segment_id);


--
-- Name: fts_vectorrest fts_vectorrest_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vectorrest
    ADD CONSTRAINT fts_vectorrest_pkey PRIMARY KEY (segment_id);


--
-- Name: namedentity_form namedentity_form_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity_form
    ADD CONSTRAINT namedentity_form_pkey PRIMARY KEY (form_id);


--
-- Name: namedentity namedentity_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity
    ADD CONSTRAINT namedentity_pkey PRIMARY KEY (namedentity_id);


--
-- Name: prepared_segment prepared_segment_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.prepared_segment
    ADD CONSTRAINT prepared_segment_pkey PRIMARY KEY (segment_id);


--
-- Name: segment0 segment0_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0
    ADD CONSTRAINT segment0_pkey PRIMARY KEY (segment_id);


--
-- Name: segment1 segment1_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1
    ADD CONSTRAINT segment1_pkey PRIMARY KEY (segment_id);


--
-- Name: segment2 segment2_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2
    ADD CONSTRAINT segment2_pkey PRIMARY KEY (segment_id);


--
-- Name: segment3 segment3_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3
    ADD CONSTRAINT segment3_pkey PRIMARY KEY (segment_id);


--
-- Name: segment4 segment4_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4
    ADD CONSTRAINT segment4_pkey PRIMARY KEY (segment_id);


--
-- Name: segment5 segment5_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5
    ADD CONSTRAINT segment5_pkey PRIMARY KEY (segment_id);


--
-- Name: segment6 segment6_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6
    ADD CONSTRAINT segment6_pkey PRIMARY KEY (segment_id);


--
-- Name: segment7 segment7_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7
    ADD CONSTRAINT segment7_pkey PRIMARY KEY (segment_id);


--
-- Name: segment8 segment8_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8
    ADD CONSTRAINT segment8_pkey PRIMARY KEY (segment_id);


--
-- Name: segment9 segment9_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9
    ADD CONSTRAINT segment9_pkey PRIMARY KEY (segment_id);


--
-- Name: segmentrest segmentrest_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest
    ADD CONSTRAINT segmentrest_pkey PRIMARY KEY (segment_id);


--
-- Name: shot shot_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.shot
    ADD CONSTRAINT shot_pkey PRIMARY KEY (shot_id);


--
-- Name: token0 token0_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0
    ADD CONSTRAINT token0_pkey PRIMARY KEY (segment_id, token_id);


--
-- Name: token1 token1_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1
    ADD CONSTRAINT token1_pkey PRIMARY KEY (segment_id, token_id);


--
-- Name: token2 token2_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2
    ADD CONSTRAINT token2_pkey PRIMARY KEY (segment_id, token_id);


--
-- Name: token3 token3_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3
    ADD CONSTRAINT token3_pkey PRIMARY KEY (segment_id, token_id);


--
-- Name: token4 token4_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4
    ADD CONSTRAINT token4_pkey PRIMARY KEY (segment_id, token_id);


--
-- Name: token5 token5_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5
    ADD CONSTRAINT token5_pkey PRIMARY KEY (segment_id, token_id);


--
-- Name: token6 token6_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6
    ADD CONSTRAINT token6_pkey PRIMARY KEY (segment_id, token_id);


--
-- Name: token7 token7_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7
    ADD CONSTRAINT token7_pkey PRIMARY KEY (segment_id, token_id);


--
-- Name: token8 token8_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8
    ADD CONSTRAINT token8_pkey PRIMARY KEY (segment_id, token_id);


--
-- Name: token9 token9_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9
    ADD CONSTRAINT token9_pkey PRIMARY KEY (segment_id, token_id);


--
-- Name: token_form token_form_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_form
    ADD CONSTRAINT token_form_pkey PRIMARY KEY (form_id);


--
-- Name: token_lemma token_lemma_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_lemma
    ADD CONSTRAINT token_lemma_pkey PRIMARY KEY (lemma_id);


--
-- Name: token_ufeat token_ufeat_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_ufeat
    ADD CONSTRAINT token_ufeat_pkey PRIMARY KEY (ufeat_id);


--
-- Name: token_ufeat token_ufeat_ufeat_key; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_ufeat
    ADD CONSTRAINT token_ufeat_ufeat_key UNIQUE (ufeat);


--
-- Name: tokenrest tokenrest_pkey; Type: CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest
    ADD CONSTRAINT tokenrest_pkey PRIMARY KEY (segment_id, token_id);


--
-- Name: corpus_language corpus_language_pkey; Type: CONSTRAINT; Schema: main; Owner: postgres
--

ALTER TABLE ONLY main.corpus_language
    ADD CONSTRAINT corpus_language_pkey PRIMARY KEY (corpus_id, iso);


--
-- Name: corpus corpus_name_current_version_project_id_key; Type: CONSTRAINT; Schema: main; Owner: postgres
--

ALTER TABLE ONLY main.corpus
    ADD CONSTRAINT corpus_name_current_version_project_id_key UNIQUE (name, current_version, project_id);


--
-- Name: corpus corpus_pkey; Type: CONSTRAINT; Schema: main; Owner: postgres
--

ALTER TABLE ONLY main.corpus
    ADD CONSTRAINT corpus_pkey PRIMARY KEY (corpus_id);


--
-- Name: deprel_dependent_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX deprel_dependent_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.deprel USING btree (dependent);


--
-- Name: deprel_head_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX deprel_head_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.deprel USING btree (head);


--
-- Name: deprel_left_anchor_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX deprel_left_anchor_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.deprel USING btree (left_anchor);


--
-- Name: deprel_right_anchor_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX deprel_right_anchor_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.deprel USING btree (right_anchor);


--
-- Name: deprel_udep_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX deprel_udep_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.deprel USING btree (udep);


--
-- Name: document_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX document_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.document USING gist (char_range);


--
-- Name: document_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX document_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.document USING gist (frame_range);


--
-- Name: document_media_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX document_media_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.document USING btree (media);


--
-- Name: document_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX document_meta_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.document USING btree (meta);


--
-- Name: document_name_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX document_name_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.document USING btree (name);


--
-- Name: fts_vector0_vector_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX fts_vector0_vector_idx ON ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0 USING rum (vector);


--
-- Name: fts_vector1_vector_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX fts_vector1_vector_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector1 USING rum (vector);


--
-- Name: fts_vector2_vector_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX fts_vector2_vector_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector2 USING rum (vector);


--
-- Name: fts_vector3_vector_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX fts_vector3_vector_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector3 USING rum (vector);


--
-- Name: fts_vector4_vector_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX fts_vector4_vector_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector4 USING rum (vector);


--
-- Name: fts_vector5_vector_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX fts_vector5_vector_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector5 USING rum (vector);


--
-- Name: fts_vector6_vector_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX fts_vector6_vector_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector6 USING rum (vector);


--
-- Name: fts_vector7_vector_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX fts_vector7_vector_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector7 USING rum (vector);


--
-- Name: fts_vector8_vector_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX fts_vector8_vector_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector8 USING rum (vector);


--
-- Name: fts_vector9_vector_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX fts_vector9_vector_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector9 USING rum (vector);


--
-- Name: fts_vectorrest_vector_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX fts_vectorrest_vector_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vectorrest USING rum (vector);


--
-- Name: namedentity_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX namedentity_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity USING gist (char_range);


--
-- Name: namedentity_form_form_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX namedentity_form_form_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity_form USING btree (form);


--
-- Name: namedentity_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX namedentity_form_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity USING btree (form_id);


--
-- Name: namedentity_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX namedentity_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity USING gist (frame_range);


--
-- Name: namedentity_type_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX namedentity_type_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity USING btree (type);


--
-- Name: segment0_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment0_char_range_idx ON ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 USING gist (char_range);


--
-- Name: segment0_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment0_frame_range_idx ON ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 USING gist (frame_range);


--
-- Name: segment0_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment0_meta_idx ON ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0 USING btree (meta);


--
-- Name: segment1_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment1_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1 USING gist (char_range);


--
-- Name: segment1_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment1_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1 USING gist (frame_range);


--
-- Name: segment1_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment1_meta_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1 USING btree (meta);


--
-- Name: segment2_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment2_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2 USING gist (char_range);


--
-- Name: segment2_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment2_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2 USING gist (frame_range);


--
-- Name: segment2_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment2_meta_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2 USING btree (meta);


--
-- Name: segment3_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment3_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3 USING gist (char_range);


--
-- Name: segment3_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment3_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3 USING gist (frame_range);


--
-- Name: segment3_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment3_meta_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3 USING btree (meta);


--
-- Name: segment4_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment4_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4 USING gist (char_range);


--
-- Name: segment4_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment4_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4 USING gist (frame_range);


--
-- Name: segment4_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment4_meta_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4 USING btree (meta);


--
-- Name: segment5_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment5_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5 USING gist (char_range);


--
-- Name: segment5_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment5_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5 USING gist (frame_range);


--
-- Name: segment5_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment5_meta_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5 USING btree (meta);


--
-- Name: segment6_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment6_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6 USING gist (char_range);


--
-- Name: segment6_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment6_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6 USING gist (frame_range);


--
-- Name: segment6_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment6_meta_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6 USING btree (meta);


--
-- Name: segment7_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment7_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7 USING gist (char_range);


--
-- Name: segment7_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment7_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7 USING gist (frame_range);


--
-- Name: segment7_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment7_meta_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7 USING btree (meta);


--
-- Name: segment8_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment8_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8 USING gist (char_range);


--
-- Name: segment8_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment8_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8 USING gist (frame_range);


--
-- Name: segment8_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment8_meta_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8 USING btree (meta);


--
-- Name: segment9_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment9_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9 USING gist (char_range);


--
-- Name: segment9_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment9_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9 USING gist (frame_range);


--
-- Name: segment9_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segment9_meta_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9 USING btree (meta);


--
-- Name: segmentrest_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segmentrest_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest USING gist (char_range);


--
-- Name: segmentrest_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segmentrest_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest USING gist (frame_range);


--
-- Name: segmentrest_meta_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX segmentrest_meta_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest USING btree (meta);


--
-- Name: shot_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX shot_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.shot USING gist (frame_range);


--
-- Name: shot_view_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX shot_view_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.shot USING btree (view);


--
-- Name: token0_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token0_char_range_idx ON ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 USING gist (char_range);


--
-- Name: token0_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token0_form_id_idx ON ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 USING btree (form_id);


--
-- Name: token0_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token0_frame_range_idx ON ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 USING gist (frame_range);


--
-- Name: token0_lemma_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token0_lemma_id_idx ON ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 USING btree (lemma_id);


--
-- Name: token0_ufeat_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token0_ufeat_id_idx ON ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 USING btree (ufeat_id);


--
-- Name: token0_upos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token0_upos_idx ON ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 USING btree (upos);


--
-- Name: token0_xpos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token0_xpos_idx ON ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0 USING btree (xpos);


--
-- Name: token1_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token1_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1 USING gist (char_range);


--
-- Name: token1_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token1_form_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1 USING btree (form_id);


--
-- Name: token1_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token1_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1 USING gist (frame_range);


--
-- Name: token1_lemma_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token1_lemma_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1 USING btree (lemma_id);


--
-- Name: token1_ufeat_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token1_ufeat_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1 USING btree (ufeat_id);


--
-- Name: token1_upos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token1_upos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1 USING btree (upos);


--
-- Name: token1_xpos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token1_xpos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1 USING btree (xpos);


--
-- Name: token2_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token2_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2 USING gist (char_range);


--
-- Name: token2_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token2_form_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2 USING btree (form_id);


--
-- Name: token2_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token2_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2 USING gist (frame_range);


--
-- Name: token2_lemma_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token2_lemma_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2 USING btree (lemma_id);


--
-- Name: token2_ufeat_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token2_ufeat_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2 USING btree (ufeat_id);


--
-- Name: token2_upos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token2_upos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2 USING btree (upos);


--
-- Name: token2_xpos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token2_xpos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2 USING btree (xpos);


--
-- Name: token3_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token3_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3 USING gist (char_range);


--
-- Name: token3_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token3_form_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3 USING btree (form_id);


--
-- Name: token3_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token3_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3 USING gist (frame_range);


--
-- Name: token3_lemma_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token3_lemma_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3 USING btree (lemma_id);


--
-- Name: token3_ufeat_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token3_ufeat_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3 USING btree (ufeat_id);


--
-- Name: token3_upos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token3_upos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3 USING btree (upos);


--
-- Name: token3_xpos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token3_xpos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3 USING btree (xpos);


--
-- Name: token4_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token4_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4 USING gist (char_range);


--
-- Name: token4_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token4_form_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4 USING btree (form_id);


--
-- Name: token4_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token4_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4 USING gist (frame_range);


--
-- Name: token4_lemma_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token4_lemma_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4 USING btree (lemma_id);


--
-- Name: token4_ufeat_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token4_ufeat_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4 USING btree (ufeat_id);


--
-- Name: token4_upos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token4_upos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4 USING btree (upos);


--
-- Name: token4_xpos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token4_xpos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4 USING btree (xpos);


--
-- Name: token5_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token5_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5 USING gist (char_range);


--
-- Name: token5_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token5_form_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5 USING btree (form_id);


--
-- Name: token5_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token5_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5 USING gist (frame_range);


--
-- Name: token5_lemma_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token5_lemma_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5 USING btree (lemma_id);


--
-- Name: token5_ufeat_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token5_ufeat_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5 USING btree (ufeat_id);


--
-- Name: token5_upos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token5_upos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5 USING btree (upos);


--
-- Name: token5_xpos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token5_xpos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5 USING btree (xpos);


--
-- Name: token6_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token6_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6 USING gist (char_range);


--
-- Name: token6_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token6_form_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6 USING btree (form_id);


--
-- Name: token6_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token6_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6 USING gist (frame_range);


--
-- Name: token6_lemma_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token6_lemma_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6 USING btree (lemma_id);


--
-- Name: token6_ufeat_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token6_ufeat_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6 USING btree (ufeat_id);


--
-- Name: token6_upos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token6_upos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6 USING btree (upos);


--
-- Name: token6_xpos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token6_xpos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6 USING btree (xpos);


--
-- Name: token7_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token7_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7 USING gist (char_range);


--
-- Name: token7_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token7_form_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7 USING btree (form_id);


--
-- Name: token7_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token7_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7 USING gist (frame_range);


--
-- Name: token7_lemma_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token7_lemma_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7 USING btree (lemma_id);


--
-- Name: token7_ufeat_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token7_ufeat_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7 USING btree (ufeat_id);


--
-- Name: token7_upos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token7_upos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7 USING btree (upos);


--
-- Name: token7_xpos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token7_xpos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7 USING btree (xpos);


--
-- Name: token8_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token8_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8 USING gist (char_range);


--
-- Name: token8_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token8_form_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8 USING btree (form_id);


--
-- Name: token8_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token8_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8 USING gist (frame_range);


--
-- Name: token8_lemma_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token8_lemma_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8 USING btree (lemma_id);


--
-- Name: token8_ufeat_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token8_ufeat_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8 USING btree (ufeat_id);


--
-- Name: token8_upos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token8_upos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8 USING btree (upos);


--
-- Name: token8_xpos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token8_xpos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8 USING btree (xpos);


--
-- Name: token9_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token9_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9 USING gist (char_range);


--
-- Name: token9_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token9_form_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9 USING btree (form_id);


--
-- Name: token9_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token9_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9 USING gist (frame_range);


--
-- Name: token9_lemma_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token9_lemma_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9 USING btree (lemma_id);


--
-- Name: token9_ufeat_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token9_ufeat_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9 USING btree (ufeat_id);


--
-- Name: token9_upos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token9_upos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9 USING btree (upos);


--
-- Name: token9_xpos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token9_xpos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9 USING btree (xpos);


--
-- Name: token_form_form_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token_form_form_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_form USING btree (form);


--
-- Name: token_lemma_lemma_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token_lemma_lemma_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_lemma USING btree (lemma);


--
-- Name: token_ufeat_ufeat_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX token_ufeat_ufeat_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_ufeat USING btree (ufeat);


--
-- Name: tokenrest_char_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX tokenrest_char_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest USING gist (char_range);


--
-- Name: tokenrest_form_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX tokenrest_form_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest USING btree (form_id);


--
-- Name: tokenrest_frame_range_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX tokenrest_frame_range_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest USING gist (frame_range);


--
-- Name: tokenrest_lemma_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX tokenrest_lemma_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest USING btree (lemma_id);


--
-- Name: tokenrest_ufeat_id_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX tokenrest_ufeat_id_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest USING btree (ufeat_id);


--
-- Name: tokenrest_upos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX tokenrest_upos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest USING btree (upos);


--
-- Name: tokenrest_xpos_idx; Type: INDEX; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

CREATE INDEX tokenrest_xpos_idx ON free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest USING btree (xpos);


--
-- Name: fts_vector1_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector1_pkey;


--
-- Name: fts_vector1_vector_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_vector_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector1_vector_idx;


--
-- Name: fts_vector2_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector2_pkey;


--
-- Name: fts_vector2_vector_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_vector_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector2_vector_idx;


--
-- Name: fts_vector3_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector3_pkey;


--
-- Name: fts_vector3_vector_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_vector_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector3_vector_idx;


--
-- Name: fts_vector4_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector4_pkey;


--
-- Name: fts_vector4_vector_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_vector_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector4_vector_idx;


--
-- Name: fts_vector5_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector5_pkey;


--
-- Name: fts_vector5_vector_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_vector_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector5_vector_idx;


--
-- Name: fts_vector6_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector6_pkey;


--
-- Name: fts_vector6_vector_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_vector_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector6_vector_idx;


--
-- Name: fts_vector7_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector7_pkey;


--
-- Name: fts_vector7_vector_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_vector_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector7_vector_idx;


--
-- Name: fts_vector8_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector8_pkey;


--
-- Name: fts_vector8_vector_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_vector_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector8_vector_idx;


--
-- Name: fts_vector9_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector9_pkey;


--
-- Name: fts_vector9_vector_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_vector_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector9_vector_idx;


--
-- Name: fts_vectorrest_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vectorrest_pkey;


--
-- Name: fts_vectorrest_vector_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0_vector_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vectorrest_vector_idx;


--
-- Name: segment1_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1_char_range_idx;


--
-- Name: segment1_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1_frame_range_idx;


--
-- Name: segment1_meta_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_meta_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1_meta_idx;


--
-- Name: segment1_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment1_pkey;


--
-- Name: segment2_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2_char_range_idx;


--
-- Name: segment2_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2_frame_range_idx;


--
-- Name: segment2_meta_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_meta_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2_meta_idx;


--
-- Name: segment2_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment2_pkey;


--
-- Name: segment3_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3_char_range_idx;


--
-- Name: segment3_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3_frame_range_idx;


--
-- Name: segment3_meta_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_meta_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3_meta_idx;


--
-- Name: segment3_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment3_pkey;


--
-- Name: segment4_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4_char_range_idx;


--
-- Name: segment4_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4_frame_range_idx;


--
-- Name: segment4_meta_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_meta_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4_meta_idx;


--
-- Name: segment4_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment4_pkey;


--
-- Name: segment5_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5_char_range_idx;


--
-- Name: segment5_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5_frame_range_idx;


--
-- Name: segment5_meta_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_meta_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5_meta_idx;


--
-- Name: segment5_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment5_pkey;


--
-- Name: segment6_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6_char_range_idx;


--
-- Name: segment6_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6_frame_range_idx;


--
-- Name: segment6_meta_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_meta_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6_meta_idx;


--
-- Name: segment6_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment6_pkey;


--
-- Name: segment7_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7_char_range_idx;


--
-- Name: segment7_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7_frame_range_idx;


--
-- Name: segment7_meta_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_meta_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7_meta_idx;


--
-- Name: segment7_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment7_pkey;


--
-- Name: segment8_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8_char_range_idx;


--
-- Name: segment8_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8_frame_range_idx;


--
-- Name: segment8_meta_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_meta_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8_meta_idx;


--
-- Name: segment8_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment8_pkey;


--
-- Name: segment9_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9_char_range_idx;


--
-- Name: segment9_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9_frame_range_idx;


--
-- Name: segment9_meta_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_meta_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9_meta_idx;


--
-- Name: segment9_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment9_pkey;


--
-- Name: segmentrest_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest_char_range_idx;


--
-- Name: segmentrest_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest_frame_range_idx;


--
-- Name: segmentrest_meta_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_meta_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest_meta_idx;


--
-- Name: segmentrest_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segmentrest_pkey;


--
-- Name: token1_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1_char_range_idx;


--
-- Name: token1_form_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_form_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1_form_id_idx;


--
-- Name: token1_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1_frame_range_idx;


--
-- Name: token1_lemma_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_lemma_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1_lemma_id_idx;


--
-- Name: token1_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1_pkey;


--
-- Name: token1_ufeat_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_ufeat_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1_ufeat_id_idx;


--
-- Name: token1_upos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_upos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1_upos_idx;


--
-- Name: token1_xpos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_xpos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token1_xpos_idx;


--
-- Name: token2_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2_char_range_idx;


--
-- Name: token2_form_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_form_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2_form_id_idx;


--
-- Name: token2_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2_frame_range_idx;


--
-- Name: token2_lemma_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_lemma_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2_lemma_id_idx;


--
-- Name: token2_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2_pkey;


--
-- Name: token2_ufeat_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_ufeat_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2_ufeat_id_idx;


--
-- Name: token2_upos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_upos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2_upos_idx;


--
-- Name: token2_xpos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_xpos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token2_xpos_idx;


--
-- Name: token3_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3_char_range_idx;


--
-- Name: token3_form_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_form_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3_form_id_idx;


--
-- Name: token3_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3_frame_range_idx;


--
-- Name: token3_lemma_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_lemma_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3_lemma_id_idx;


--
-- Name: token3_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3_pkey;


--
-- Name: token3_ufeat_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_ufeat_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3_ufeat_id_idx;


--
-- Name: token3_upos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_upos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3_upos_idx;


--
-- Name: token3_xpos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_xpos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token3_xpos_idx;


--
-- Name: token4_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4_char_range_idx;


--
-- Name: token4_form_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_form_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4_form_id_idx;


--
-- Name: token4_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4_frame_range_idx;


--
-- Name: token4_lemma_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_lemma_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4_lemma_id_idx;


--
-- Name: token4_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4_pkey;


--
-- Name: token4_ufeat_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_ufeat_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4_ufeat_id_idx;


--
-- Name: token4_upos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_upos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4_upos_idx;


--
-- Name: token4_xpos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_xpos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token4_xpos_idx;


--
-- Name: token5_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5_char_range_idx;


--
-- Name: token5_form_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_form_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5_form_id_idx;


--
-- Name: token5_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5_frame_range_idx;


--
-- Name: token5_lemma_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_lemma_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5_lemma_id_idx;


--
-- Name: token5_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5_pkey;


--
-- Name: token5_ufeat_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_ufeat_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5_ufeat_id_idx;


--
-- Name: token5_upos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_upos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5_upos_idx;


--
-- Name: token5_xpos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_xpos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token5_xpos_idx;


--
-- Name: token6_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6_char_range_idx;


--
-- Name: token6_form_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_form_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6_form_id_idx;


--
-- Name: token6_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6_frame_range_idx;


--
-- Name: token6_lemma_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_lemma_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6_lemma_id_idx;


--
-- Name: token6_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6_pkey;


--
-- Name: token6_ufeat_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_ufeat_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6_ufeat_id_idx;


--
-- Name: token6_upos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_upos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6_upos_idx;


--
-- Name: token6_xpos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_xpos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token6_xpos_idx;


--
-- Name: token7_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7_char_range_idx;


--
-- Name: token7_form_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_form_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7_form_id_idx;


--
-- Name: token7_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7_frame_range_idx;


--
-- Name: token7_lemma_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_lemma_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7_lemma_id_idx;


--
-- Name: token7_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7_pkey;


--
-- Name: token7_ufeat_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_ufeat_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7_ufeat_id_idx;


--
-- Name: token7_upos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_upos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7_upos_idx;


--
-- Name: token7_xpos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_xpos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token7_xpos_idx;


--
-- Name: token8_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8_char_range_idx;


--
-- Name: token8_form_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_form_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8_form_id_idx;


--
-- Name: token8_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8_frame_range_idx;


--
-- Name: token8_lemma_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_lemma_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8_lemma_id_idx;


--
-- Name: token8_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8_pkey;


--
-- Name: token8_ufeat_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_ufeat_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8_ufeat_id_idx;


--
-- Name: token8_upos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_upos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8_upos_idx;


--
-- Name: token8_xpos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_xpos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token8_xpos_idx;


--
-- Name: token9_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9_char_range_idx;


--
-- Name: token9_form_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_form_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9_form_id_idx;


--
-- Name: token9_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9_frame_range_idx;


--
-- Name: token9_lemma_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_lemma_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9_lemma_id_idx;


--
-- Name: token9_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9_pkey;


--
-- Name: token9_ufeat_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_ufeat_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9_ufeat_id_idx;


--
-- Name: token9_upos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_upos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9_upos_idx;


--
-- Name: token9_xpos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_xpos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token9_xpos_idx;


--
-- Name: tokenrest_char_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_char_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest_char_range_idx;


--
-- Name: tokenrest_form_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_form_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest_form_id_idx;


--
-- Name: tokenrest_frame_range_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_frame_range_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest_frame_range_idx;


--
-- Name: tokenrest_lemma_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_lemma_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest_lemma_id_idx;


--
-- Name: tokenrest_pkey; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_pkey ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest_pkey;


--
-- Name: tokenrest_ufeat_id_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_ufeat_id_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest_ufeat_id_idx;


--
-- Name: tokenrest_upos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_upos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest_upos_idx;


--
-- Name: tokenrest_xpos_idx; Type: INDEX ATTACH; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER INDEX free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0_xpos_idx ATTACH PARTITION free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.tokenrest_xpos_idx;


--
-- Name: fts_vector0 fts_vector0_segment_id_fkey; Type: FK CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.fts_vector0
    ADD CONSTRAINT fts_vector0_segment_id_fkey FOREIGN KEY (segment_id) REFERENCES free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0(segment_id);


--
-- Name: namedentity namedentity_form_id_fkey; Type: FK CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity
    ADD CONSTRAINT namedentity_form_id_fkey FOREIGN KEY (form_id) REFERENCES free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.namedentity_form(form_id);


--
-- Name: prepared_segment prepared_segment_segment_id_fkey; Type: FK CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE ONLY free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.prepared_segment
    ADD CONSTRAINT prepared_segment_segment_id_fkey FOREIGN KEY (segment_id) REFERENCES free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0(segment_id);


--
-- Name: token0 token0_form_id_fkey; Type: FK CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0
    ADD CONSTRAINT token0_form_id_fkey FOREIGN KEY (form_id) REFERENCES free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_form(form_id);


--
-- Name: token0 token0_lemma_id_fkey; Type: FK CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0
    ADD CONSTRAINT token0_lemma_id_fkey FOREIGN KEY (lemma_id) REFERENCES free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_lemma(lemma_id);


--
-- Name: token0 token0_segment_id_fkey; Type: FK CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0
    ADD CONSTRAINT token0_segment_id_fkey FOREIGN KEY (segment_id) REFERENCES free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.segment0(segment_id);


--
-- Name: token0 token0_ufeat_id_fkey; Type: FK CONSTRAINT; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

ALTER TABLE free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token0
    ADD CONSTRAINT token0_ufeat_id_fkey FOREIGN KEY (ufeat_id) REFERENCES free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_ufeat(ufeat_id);


--
-- Name: corpus_language corpus_language_corpus_id_fkey; Type: FK CONSTRAINT; Schema: main; Owner: postgres
--

ALTER TABLE ONLY main.corpus_language
    ADD CONSTRAINT corpus_language_corpus_id_fkey FOREIGN KEY (corpus_id) REFERENCES main.corpus(corpus_id) ON DELETE CASCADE;


--
-- Name: m_lemma_freq0; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq0;


--
-- Name: m_lemma_freq1; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq1;


--
-- Name: m_lemma_freq2; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq2;


--
-- Name: m_lemma_freq3; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq3;


--
-- Name: m_lemma_freq4; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq4;


--
-- Name: m_lemma_freq5; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq5;


--
-- Name: m_lemma_freq6; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq6;


--
-- Name: m_lemma_freq7; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq7;


--
-- Name: m_lemma_freq8; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freq8;


--
-- Name: m_lemma_freqrest; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.m_lemma_freqrest;


--
-- Name: token_freq; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_freq;


--
-- Name: token_n; Type: MATERIALIZED VIEW DATA; Schema: free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1; Owner: postgres
--

REFRESH MATERIALIZED VIEW free_single_video_corpus__db519c9aa5e2491b8970fa363eeab249_1.token_n;


--
-- PostgreSQL database dump complete
--
