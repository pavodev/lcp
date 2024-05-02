Averb + Adjective + Noun + .

pseudo-CQL: `ADV^t1 ADJ^t2 NOUN^t3 .^t4`

```sql
WITH RECURSIVE
  vectorized AS (
    SELECT segment_id                                                          
      FROM sparcling1.fts_vector_enrest vec
      WHERE vec.vector @@ E'3ADV <1> 3ADJ <1> 3NOUN <1> 3.'
  ),
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t1.token_id AS t1,
          t2.token_id AS t2,
          t3.token_id AS t3,
          t4.token_id AS t4
    FROM
      vectorized s
    CROSS JOIN sparcling1.token_enrest t1
    CROSS JOIN sparcling1.token_enrest t2
    CROSS JOIN sparcling1.token_enrest t3
    CROSS JOIN sparcling1.token_enrest t4
    WHERE t1.segment_id = s.segment_id AND t1.upos = 'ADV'
        AND t2.segment_id = s.segment_id AND t2.upos = 'ADJ' AND t2.token_id - t1.token_id = 1
        AND t3.segment_id = s.segment_id AND t3.upos = 'NOUN' AND t3.token_id - t2.token_id = 1
        AND t4.segment_id = s.segment_id AND t4.upos = '.' AND t4.token_id - t3.token_id = 1
  )
SELECT s, t1,t2,t3,t4
FROM fixed_parts;
```


Verb followed by at least one (or more) occurrence of Determiner+Noun, followed by a dot

pseudo-CQL: `VERB^t1 (DET^t2 NOUN^t3[head=t3,dep=t2])+ .^t4`

SQL:
```sql
WITH            
  vectorized AS (
    SELECT segment_id                                                          
      FROM sparcling1.fts_vector_enrest vec
      WHERE vec.vector @@ E'3VERB <1> 3DET <1> 3NOUN' AND vec.vector @@ E'3DET <1> 3NOUN <1> 3.'
  ),
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t1.token_id AS t1,
          t2.token_id AS t2,
          t3.token_id AS t3,
          t4.token_id AS t4
    FROM
      vectorized s
    CROSS JOIN sparcling1.token_enrest t1
    CROSS JOIN sparcling1.token_enrest t2
    CROSS JOIN sparcling1.token_enrest t3
    CROSS JOIN sparcling1.token_enrest t4
    WHERE t1.segment_id = s.segment_id AND t1.upos = 'VERB'
        AND t2.segment_id = s.segment_id AND t2.upos = 'DET' AND t2.token_id = t1.token_id + 1
        AND t3.segment_id = s.segment_id AND t3.upos = 'NOUN' AND t3.token_id = t2.token_id + 1
        AND t4.segment_id = s.segment_id AND t4.upos = '.'
        AND t4.token_id - t1.token_id > 2
        AND (t4.token_id - t1.token_id - 1) % 2 = 0
        AND (true,true) = ALL(
          SELECT 
            t2a.upos = 'DET' AND deprel.dependent = t2a.token_id,
            t3a.upos = 'NOUN' AND deprel.head = t3a.token_id
          FROM sparcling1.token_enrest t2a
          CROSS JOIN sparcling1.token_enrest t3a
          LEFT JOIN sparcling1.deprel_en deprel ON deprel.head = t3a.token_id AND deprel.dependent = t2a.token_id
          WHERE t2a.segment_id = t1.segment_id AND t2a.token_id > t1.token_id AND (t2a.token_id - t1.token_id - 1) % 2 = 0
            AND t3a.segment_id = t1.segment_id AND t3a.token_id = t2a.token_id + 1 AND (t4.token_id - t3a.token_id - 1) % 2 = 0
        )
  )
SELECT s, t1, t4, t4-t1
FROM fixed_parts;
```



Verb followed by possibly no, but also maybe one or more occurrences of Determiner+Noun, followed by a dot

pseudo-CQL: `VERB^t1 (DET^t2 NOUN^t3[head=t3,dep=t2])* .^t4`

SQL:
```sql
WITH
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t1.token_id AS t1,
          t4.token_id AS t4
    FROM
      sparcling1.segment_enrest s
    CROSS JOIN sparcling1.token_enrest t1
    CROSS JOIN sparcling1.token_enrest t4
    WHERE t1.segment_id = s.segment_id AND t1.upos = 'VERB'
        AND t4.segment_id = s.segment_id AND t4.upos = '.'
        AND t4.token_id - t1.token_id > 0
        AND (t4.token_id - t1.token_id - 1) % 2 = 0
        AND (true,true) = ALL(
          SELECT 
            t2a.upos = 'DET' AND deprel.dependent = t2a.token_id,
            t3a.upos = 'NOUN' AND deprel.head = t3a.token_id
          FROM sparcling1.token_enrest t2a
          CROSS JOIN sparcling1.token_enrest t3a
          LEFT JOIN sparcling1.deprel_en deprel ON deprel.head = t3a.token_id AND deprel.dependent = t2a.token_id
          WHERE t2a.segment_id = t1.segment_id AND t2a.token_id > t1.token_id AND (t2a.token_id - t1.token_id - 1) % 2 = 0
            AND t3a.segment_id = t1.segment_id AND t3a.token_id = t2a.token_id + 1 AND (t4.token_id - t3a.token_id - 1) % 2 = 0
        )
  )
SELECT s, t1, t4, t4-t1
FROM fixed_parts;
```


At least one (or more) occurrences of Determiner+Noun, followed by a dot

pseudo-CQL: `(DET^t2 NOUN^t3[head=t3,dep=t2])+ .^t4`

SQL:
```sql
WITH            
  vectorized AS (
    SELECT segment_id                                                          
      FROM sparcling1.fts_vector_enrest vec
      WHERE vec.vector @@ E'3DET <1> 3NOUN <1> 3.'
  ),
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t2.token_id AS t2,
          t3.token_id AS t3,
          t4.token_id AS t4
    FROM
      vectorized s
    CROSS JOIN sparcling1.token_enrest t2
    CROSS JOIN sparcling1.token_enrest t3
    CROSS JOIN sparcling1.token_enrest t4
    WHERE t2.segment_id = s.segment_id AND t2.upos = 'DET'
        AND t3.segment_id = s.segment_id AND t3.upos = 'NOUN' AND t3.token_id = t2.token_id + 1
        AND t4.segment_id = s.segment_id AND t4.upos = '.' AND t4.token_id - t3.token_id > 0
        AND (true,true) = ALL(
          SELECT 
            t2a.upos = 'DET' AND deprel.dependent = t2a.token_id,
            t3a.upos = 'NOUN' AND deprel.head = t3a.token_id
          FROM sparcling1.token_enrest t2a
          CROSS JOIN sparcling1.token_enrest t3a
          LEFT JOIN sparcling1.deprel_en deprel ON deprel.head = t3a.token_id AND deprel.dependent = t2a.token_id
          WHERE t2a.segment_id = t4.segment_id AND t2a.token_id - t2.token_id >= 0
            AND t3a.segment_id = t4.segment_id AND t3a.token_id = t2a.token_id + 1 AND (t4.token_id - t3a.token_id - 1) % 2 = 0
        )
  )
SELECT s, t2, t4, t4-t2
FROM fixed_parts;
```




A verb, fowllowed by one or more occurrences of Determiner+Noun

pseudo-CQL: `VERB^1 (DET^t2 NOUN^t3[head=t3,dep=t2])+`

SQL:
```sql
WITH            
  vectorized AS (
    SELECT segment_id                                                          
      FROM sparcling1.fts_vector_enrest vec
      WHERE vec.vector @@ E'3VERB'
  ),
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t1.token_id AS t1,
          t2.token_id AS t2,
          t3.token_id AS t3
    FROM
      vectorized s
    CROSS JOIN sparcling1.token_enrest t1
    CROSS JOIN sparcling1.token_enrest t2
    CROSS JOIN sparcling1.token_enrest t3
    WHERE t1.segment_id = s.segment_id AND t1.upos = 'VERB'
        AND t2.segment_id = s.segment_id AND t2.upos = 'DET' AND t2.token_id - t1.token_id > 0 AND (t2.token_id - t1.token_id - 1) % 2 = 0
        AND t3.segment_id = s.segment_id AND t3.upos = 'NOUN' AND t3.token_id = t2.token_id + 1
        AND (true,true) = ALL(
          SELECT 
            t2a.upos = 'DET' AND deprel.dependent = t2a.token_id,
            t3a.upos = 'NOUN' AND deprel.head = t3a.token_id
          FROM sparcling1.token_enrest t2a
          CROSS JOIN sparcling1.token_enrest t3a
          LEFT JOIN sparcling1.deprel_en deprel ON deprel.head = t3a.token_id AND deprel.dependent = t2a.token_id
          WHERE t2a.segment_id = t1.segment_id AND t2.token_id - t2a.token_id >= 0 AND (t2a.token_id - t1.token_id - 1) % 2 = 0
            AND t3a.segment_id = t1.segment_id AND t3a.token_id = t2a.token_id + 1
        )
  )
SELECT s, t1, t3, t3-t1
FROM fixed_parts;
```




A verb, possibly fowllowed by any number of any token, followed by a noun

pseudo-CQL: `VERB^1 []^2* NOUN^3`

SQL:
```sql
WITH
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t1.token_id AS t1,
          t3.token_id AS t3
    FROM
      sparcling1.segment_enrest s
    CROSS JOIN sparcling1.token_enrest t1
    CROSS JOIN sparcling1.token_enrest t3
    WHERE t1.segment_id = s.segment_id AND t1.upos = 'VERB'
        AND t3.segment_id = s.segment_id AND t3.upos = 'NOUN'
        AND t3.token_id - t1.token_id > 0
        AND true = ALL(
          SELECT 
            t2a.token_id > t1.token_id
          FROM sparcling1.token_enrest t2a
          WHERE t2a.segment_id = t1.segment_id AND t2a.token_id > t1.token_id AND t2a.token_id < t3.token_id
        )
  )
SELECT s, t1, t3, t3-t1
FROM fixed_parts;
```


A verb, possibly fowllowed by one determiner, followed by a noun

pseudo-CQL: `VERB^1 DET^2? NOUN^3`

SQL:
```sql
WITH
  vectorized AS (
    SELECT segment_id                                                          
      FROM sparcling1.fts_vector_enrest vec
      WHERE vec.vector @@ E'3VERB <1> (3DET <1> 3NOUN | 3NOUN)'
  ),
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t1.token_id AS t1,
          t3.token_id AS t3
    FROM
      vectorized s
    CROSS JOIN sparcling1.token_enrest t1
    CROSS JOIN sparcling1.token_enrest t3
    WHERE t1.segment_id = s.segment_id AND t1.upos = 'VERB'
        AND t3.segment_id = s.segment_id AND t3.upos = 'NOUN'
        AND t3.token_id - t1.token_id > 0
        AND t3.token_id - t1.token_id < 3
        AND true = ALL(
          SELECT 
            t2a.upos = 'DET'
          FROM sparcling1.token_enrest t2a
          WHERE t2a.segment_id = t1.segment_id AND t2a.token_id > t1.token_id AND t2a.token_id < t3.token_id
        )
  )
SELECT s, t1, t3, t3-t1
FROM fixed_parts;
```



A verb, possibly fowllowed by a dependency, followed by a dot

pseudo-CQL: `VERB^1 [head=t1,dep=t2]^2? .^3`

SQL:
```sql
WITH
  vectorized AS (
    SELECT segment_id                                                          
      FROM sparcling1.fts_vector_enrest vec
      WHERE vec.vector @@ E'3VERB <1> ((1a|!1a) <1> 3. | 3.)'
  ),
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t1.token_id AS t1,
          t3.token_id AS t3
    FROM
      vectorized s
    CROSS JOIN sparcling1.token_enrest t1
    CROSS JOIN sparcling1.token_enrest t3
    WHERE t1.segment_id = s.segment_id AND t1.upos = 'VERB'
        AND t3.segment_id = s.segment_id AND t3.upos = '.'
        AND t3.token_id - t1.token_id > 0
        AND t3.token_id - t1.token_id < 3
        AND true = ALL(
          SELECT 
            t2a.upos = 'DET' AND deprel.dependent = t2a.token_id
          FROM sparcling1.token_enrest t2a
          LEFT JOIN sparcling1.deprel_en deprel ON deprel.head = t1.token_id AND deprel.dependent = t2a.token_id
          WHERE t2a.segment_id = t1.segment_id AND t2a.token_id > t1.token_id AND t2a.token_id < t3.token_id
        )
  )
SELECT s, t1, t3, t3-t1
FROM fixed_parts;
```




A verb follow by a determiner or optionally by an arbitrarily long (possibly null) sequence of adverbs, followed by a noun

pseudo-CQL: `VERB^1 (3DET^2 | 3ADV^3*) 3NOUN^4`

SQL:
```sql
WITH
  vectorized AS (
    SELECT segment_id                                                          
      FROM sparcling1.fts_vector_enrest vec
      WHERE vec.vector @@ E'3VERB <1> (3DET <1> 3NOUN | 3ADJ | 3NOUN)'
  ),
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t1.token_id AS t1,
          t4.token_id AS t4
    FROM
      vectorized s
    CROSS JOIN sparcling1.token_enrest t1
    CROSS JOIN sparcling1.token_enrest t4
    WHERE t1.segment_id = s.segment_id AND t1.upos = 'VERB'
        AND t4.segment_id = s.segment_id AND t4.upos = 'NOUN'
        AND t4.token_id - t1.token_id > 0
        AND true = ALL(
          SELECT 
            (t4.token_id - t1.token_id > 1 AND t2a.upos = 'DET' AND t2a.token_id = t1.token_id + 1 AND t4.token_id = t2a.token_id + 1)
            OR (t2a.upos = 'ADV' AND t2a.token_id = t1.token_id + 1 AND t4.token_id = t2a.token_id + 1)
          FROM sparcling1.token_enrest t2a
          WHERE t2a.segment_id = t1.segment_id AND t2a.token_id > t1.token_id AND t2a.token_id < t4.token_id
        )
  )
SELECT s, t1, t4, t4-t1
FROM fixed_parts;
```



A verb follow by a determiner or an arbitrarily long (but non-null) sequence of adverb+adjective, followed by a noun

pseudo-CQL: `VERB^1 (3DET^2 | (3ADV^3 3ADJ^4)+) 3NOUN^5`

SQL:
```sql
WITH
  vectorized AS (
    SELECT segment_id                                                          
      FROM sparcling1.fts_vector_enrest vec
      WHERE vec.vector @@ E'3VERB <1> (3DET <1> 3NOUN | 3ADV <1> 3ADJ)' AND vec.vector @@ E'(3DET | 3ADV <1> 3ADJ) <1> 3NOUN'
  ),
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t1.token_id AS t1,
          t5.token_id AS t5
    FROM
      vectorized s
    CROSS JOIN sparcling1.token_enrest t1
    CROSS JOIN sparcling1.token_enrest t5
    WHERE t1.segment_id = s.segment_id AND t1.upos = 'VERB'
        AND t5.segment_id = s.segment_id AND t5.upos = 'NOUN'
        AND t5.token_id - t1.token_id > 1
        AND (
          true = ALL(
            SELECT 
              t5.token_id - t1.token_id = 1 AND t2a.upos = 'DET' AND t2a.token_id = t1.token_id + 1 AND t5.token_id = t2a.token_id + 1
            FROM sparcling1.token_enrest t2a
            WHERE t2a.segment_id = t1.segment_id AND t2a.token_id > t1.token_id AND t2a.token_id < t5.token_id
          )
          OR
          (true,true) = ALL(
            SELECT 
              t5.token_id - t1.token_id > 2
              AND t3a.token_id - t1.token_id - 1 % 2 = 0 AND t3a.upos = 'ADV'
              AND t4a.token_id - t1.token_id - 1 % 2 = 1 AND t4a.upos = 'ADJ'
            FROM sparcling1.token_enrest t2a
            WHERE t3a.segment_id = t1.segment_id AND t3a.token_id > t1.token_id AND t3a.token_id < t5.token_id
              AND t4a.segment_id = t1.segment_id AND t4a.token_id > t1.token_id AND t4a.token_id < t5.token_id
          )
        )
  )
SELECT s, t1, t5, t5-t1
FROM fixed_parts;
```




A verb follow by a determiner or an arbitrarily long (but non-null) sequence of adverb+adjective, followed by a noun

pseudo-CQL: `VERB^1 (3DET^2 | (3ADV^3? 3ADJ^4)+) 3NOUN^5`

SQL:
```sql
WITH RECURSIVE
  vectorized AS (
    SELECT segment_id                                                          
      FROM sparcling1.fts_vector_enrest vec
      WHERE vec.vector @@ E'3VERB <1> (3DET <1> 3NOUN | 3ADV <1> 3ADJ | 3ADJ)' AND vec.vector @@ E'(3DET | 3ADJ) <1> 3NOUN'
  ),
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t1.token_id AS t1,
          t5.token_id AS t5
    FROM
      vectorized s
    CROSS JOIN sparcling1.token_enrest t1
    CROSS JOIN sparcling1.token_enrest t5
    WHERE t1.segment_id = s.segment_id AND t1.upos = 'VERB'
        AND t5.segment_id = s.segment_id AND t5.upos = 'NOUN'
        AND t5.token_id - t1.token_id > 1
  ),
  transition (source_state, dest_state, label) AS (
      VALUES
          (0, 1, 't2'),
          (0, 2, 't3'),
          (0, 3, 't4'),
          (1, 4, 't5'),
          (2, 3, 't4'),
          (3, 2, 't3'),
          (3, 3, 't4'),
          (3, 4, 't5')
  ),
  traversal AS (
    SELECT  fixed_parts.s            segment_id,
            fixed_parts.t1           left_token,
            fixed_parts.t5           right_token,
            token.token_id           id,
            transition.dest_state    state,
            ARRAY [token.token_id]   token_list,
            jsonb_build_object(transition.label, token.token_id)  map
    FROM fixed_parts
        JOIN sparcling1.token_enrest token ON token.segment_id = fixed_parts.s
        JOIN transition ON transition.source_state = 0
    WHERE token.token_id = fixed_parts.t1 + 1 AND (
            (transition.dest_state = 1 AND token.upos::text = 'DET' AND transition.label = 't2')
            OR (transition.dest_state = 3 AND token.upos::text = 'DET' AND transition.label = 't2')
            OR (transition.dest_state = 2 AND token.upos::text = 'ADV' AND transition.label = 't3')
            OR (transition.dest_state = 3 AND token.upos::text = 'ADJ' AND transition.label = 't4')
          )
    UNION ALL
    SELECT  traversal.segment_id,
            traversal.left_token,
            traversal.right_token,
            token.token_id   id,
            transition.dest_state,
            traversal.token_list || token.token_id,
            traversal.map || jsonb_build_object(transition.label, token.token_id)
    FROM traversal
      JOIN transition ON transition.source_state = traversal.state
      JOIN sparcling1.token_enrest token ON token.token_id = traversal.id + 1 AND token.segment_id = traversal.segment_id
    WHERE (transition.source_state = 1 AND transition.dest_state = 4 AND token.upos::text = 'NOUN' AND transition.label = 't5' AND token.token_id = traversal.right_token)
            OR (transition.source_state = 2 AND transition.dest_state = 3 AND token.upos::text = 'ADJ' AND transition.label = 't4')
            OR (transition.source_state = 3 AND transition.dest_state = 2 AND token.upos::text = 'ADV' AND transition.label = 't3')
            OR (transition.source_state = 3 AND transition.dest_state = 3 AND token.upos::text = 'ADJ' AND transition.label = 't4')
            OR (transition.source_state = 3 AND transition.dest_state = 4 AND token.upos::text = 'NOUN' AND transition.label = 't5' AND token.token_id = traversal.right_token)
  ) SEARCH DEPTH FIRST BY id SET ordercol
SELECT segment_id, left_token, id, id-left_token
FROM traversal
WHERE state IN (4)
ORDER BY ordercol;
```




No, one, or more occurrences of Determiner+Noun, followed by a dot

pseudo-CQL: `(ADV^t1 ADJ^t2)* NOUN^t3 .^t4`

```sql
WITH RECURSIVE
  vectorized AS (
    SELECT segment_id                                                          
      FROM sparcling1.fts_vector_enrest vec
      WHERE vec.vector @@ E'3NOUN <1> 3.'
  ),
  transition (source_state, dest_state, label) AS (
      VALUES
            (0, 1, 't1'),
            (0, 3, 't3'),
            (1, 2, 't2'),
            (2, 1, 't1'),
            (2, 3, 't3')
  ),
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t3.token_id AS t3,
          t4.token_id AS t4
    FROM
      vectorized s
    CROSS JOIN sparcling1.token_enrest t3
    CROSS JOIN sparcling1.token_enrest t4
    WHERE t3.segment_id = s.segment_id AND t3.upos = 'NOUN'
        AND t4.segment_id = s.segment_id AND t4.upos = '.'
        AND t4.token_id - t3.token_id = 1
  ),
  traversal AS (
    SELECT  fixed_parts.s            segment_id,
            token.token_id           left_token,
            fixed_parts.t3           right_token,
            token.token_id           id,
            transition.dest_state    state,
            ARRAY [token.token_id]   token_list,
            jsonb_build_object(transition.label, token.token_id)  map
    FROM fixed_parts
        JOIN sparcling1.token_enrest token ON token.segment_id = fixed_parts.s
        JOIN transition ON transition.source_state = 0
    WHERE (transition.dest_state = 1 AND token.upos::text = 'ADV' AND transition.label = 't1')
          OR (transition.dest_state = 3 AND token.upos::text = 'NOUN' AND transition.label = 't3' AND token.token_id = fixed_parts.t3)
    UNION ALL
    SELECT  traversal.segment_id,
            traversal.left_token,
            traversal.right_token,
            token.token_id   id,
            transition.dest_state,
            traversal.token_list || token.token_id,
            traversal.map || jsonb_build_object(transition.label, token.token_id)
    FROM traversal
      JOIN transition ON transition.source_state = traversal.state
      JOIN sparcling1.token_enrest token ON token.token_id = traversal.id + 1 AND token.segment_id = traversal.segment_id
    WHERE (transition.source_state = 1 AND transition.dest_state = 2 AND token.upos::text = 'ADJ' AND transition.label = 't2')
            OR (transition.source_state = 2 AND transition.dest_state = 1 AND token.upos::text = 'ADV' AND transition.label = 't1')
            OR (transition.source_state = 2 AND transition.dest_state = 3 AND token.upos::text = 'NOUN' AND transition.label = 't3' AND token.token_id = traversal.right_token)
  ) SEARCH DEPTH FIRST BY id SET ordercol
SELECT segment_id, left_token, id, id-left_token
FROM traversal
WHERE state IN (3)
ORDER BY ordercol;
```





A determiner follow by arbitrarily many (possibly no) occurrences of (possibly absent) Adverb + Adjective, followed by a Noun

pseudo-CQL: `DET^1 (ADV^t2? ADJ^t3)* NOUN^t4 VERB^t5 DET^6 (ADV^t7? ADJ^t8)* NOUN^t9`

```sql
WITH RECURSIVE
  vectorized AS (
    SELECT segment_id                                                          
      FROM sparcling1.fts_vector_enrest vec
      WHERE vec.vector @@ E'(3DET | 3ADJ) <1> 3NOUN <1> 3VERB <1> 3DET <1> (3ADV | 3ADJ | 3NOUN)' 
  ),
  fixed_parts AS (
    SELECT s.segment_id AS s,
          t1.token_id AS t1,
          t4.token_id AS t4,
          t5.token_id AS t5,
          t6.token_id AS t6,
          t9.token_id AS t9
    FROM
      vectorized s
    CROSS JOIN sparcling1.token_enrest t1
    CROSS JOIN sparcling1.token_enrest t4
    CROSS JOIN sparcling1.token_enrest t5
    CROSS JOIN sparcling1.token_enrest t6
    CROSS JOIN sparcling1.token_enrest t9
    WHERE t1.segment_id = s.segment_id AND t1.upos = 'DET'
        AND t4.segment_id = s.segment_id AND t4.upos = 'NOUN' AND t4.token_id > t1.token_id
        AND t5.segment_id = s.segment_id AND t5.upos = 'VERB' AND t5.token_id - t4.token_id = 1
        AND t6.segment_id = s.segment_id AND t6.upos = 'DET' AND t6.token_id - t5.token_id = 1
        AND t9.segment_id = s.segment_id AND t9.upos = 'NOUN' AND t9.token_id - t6.token_id > 0
  ),
  transition1 (source_state, dest_state, label) AS (
      VALUES
            (0, 1, 't2'),
            (0, 3, 't4'),
            (1, 2, 't3'),
            (2, 1, 't2'),
            (2, 3, 't4')
  ),
  traversal1 AS (
    SELECT  fixed_parts.s            segment_id,
            fixed_parts.t1           left_token,
            fixed_parts.t4           right_token,
            fixed_parts.t5           t5,
            fixed_parts.t6           t6,
            fixed_parts.t9           t9,
            token.token_id           id,
            transition1.dest_state    state,
            ARRAY [token.token_id]   token_list,
            jsonb_build_object(transition1.label, token.token_id)  map
    FROM fixed_parts
        JOIN sparcling1.token_enrest token ON token.segment_id = fixed_parts.s
        JOIN transition1 ON transition1.source_state = 0
    WHERE token.token_id = fixed_parts.t1 + 1 AND
          ( (transition1.dest_state = 1 AND token.upos::text = 'ADV' AND transition1.label = 't2')
          OR (transition1.dest_state = 3 AND token.upos::text = 'NOUN' AND transition1.label = 't4' AND token.token_id = fixed_parts.t4) )
    UNION ALL
    SELECT  traversal1.segment_id,
            traversal1.left_token,
            traversal1.right_token,
            traversal1.t5,
            traversal1.t6,
            traversal1.t9,
            token.token_id   id,
            transition1.dest_state,
            traversal1.token_list || token.token_id,
            traversal1.map || jsonb_build_object(transition1.label, token.token_id)
    FROM traversal1
      JOIN transition1 ON transition1.source_state = traversal1.state
      JOIN sparcling1.token_enrest token ON token.token_id = traversal1.id + 1 AND token.segment_id = traversal1.segment_id
    WHERE (transition1.source_state = 1 AND transition1.dest_state = 2 AND token.upos::text = 'ADJ' AND transition1.label = 't3')
            OR (transition1.source_state = 2 AND transition1.dest_state = 1 AND token.upos::text = 'ADV' AND transition1.label = 't2')
            OR (transition1.source_state = 2 AND transition1.dest_state = 3 AND token.upos::text = 'NOUN' AND transition1.label = 't4' AND token.token_id = traversal1.right_token)
  ) SEARCH DEPTH FIRST BY id SET ordercol,
  transition2 (source_state, dest_state, label) AS (
      VALUES
            (0, 1, 't7'),
            (0, 3, 't9'),
            (1, 2, 't8'),
            (2, 1, 't7'),
            (2, 3, 't9')
  ),
  traversal2 AS (
    SELECT  tr1.segment_id           segment_id,
            tr1.t6                   left_token,
            tr1.t9                   right_token,
            tr1.left_token           t1,
            tr1.right_token          t4,
            tr1.t5                   t5,
            tr1.t6                   t6,
            tr1.t9                   t9,
            token.token_id           id,
            transition2.dest_state    state,
            ARRAY [token.token_id]   token_list,
            jsonb_build_object(transition2.label, token.token_id)  map
    FROM (
      SELECT *
        FROM traversal1
        WHERE traversal1.state IN (3)
        ORDER BY ordercol
      ) tr1
        JOIN sparcling1.token_enrest token ON token.segment_id = tr1.segment_id
        JOIN transition2 ON transition2.source_state = 0
    WHERE token.token_id = tr1.t6 + 1 AND
          ( (transition2.dest_state = 1 AND token.upos::text = 'ADV' AND transition2.label = 't7')
          OR (transition2.dest_state = 3 AND token.upos::text = 'NOUN' AND transition2.label = 't9' AND token.token_id = tr1.t9) )
    UNION ALL
    SELECT  traversal2.segment_id,
            traversal2.left_token,
            traversal2.right_token,
            traversal2.t1            t1,
            traversal2.t4            t4,
            traversal2.t5            t5,
            traversal2.t6            t6,
            traversal2.t9            t9,
            token.token_id   id,
            transition2.dest_state,
            traversal2.token_list || token.token_id,
            traversal2.map || jsonb_build_object(transition2.label, token.token_id)
    FROM traversal2
      JOIN transition2 ON transition2.source_state = traversal2.state
      JOIN sparcling1.token_enrest token ON token.token_id = traversal2.id + 1 AND token.segment_id = traversal2.segment_id
    WHERE (transition2.source_state = 1 AND transition2.dest_state = 2 AND token.upos::text = 'ADJ' AND transition2.label = 't8')
            OR (transition2.source_state = 2 AND transition2.dest_state = 1 AND token.upos::text = 'ADV' AND transition2.label = 't7')
            OR (transition2.source_state = 2 AND transition2.dest_state = 3 AND token.upos::text = 'NOUN' AND transition2.label = 't9' AND token.token_id = traversal2.right_token)
  ) 
  SEARCH DEPTH FIRST BY id SET ordercol
SELECT *
FROM traversal2
WHERE traversal2.state IN (3)
ORDER BY ordercol;
```





pseudo-CQL: `3DET^1 3ADV^2* 3ADJ^3{2} 3PREP^4? 3NOUN^5`

pseudo-CQL: `3DET^1 3ADV^2* (3ADJ^3{2} 3PREP^4?){3} 3NOUN^5? 3NOUN^6`

