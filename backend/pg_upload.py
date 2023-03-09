async def pg_upload(conn, cur, corpus_data, corpus_id, config_data):

    return True

    schema_name = "u" + str(corpus_id).replace("-", "_")
    script = f"CREATE SCHEMA %s;"
    params = (schema_name,)

    await cur.execute(script, params)

    script = f"INSERT..."
    params = tuple()

    await cur.execute(script, params)

    script = f"CREATE INDEX..."
    params = tuple()

    await cur.execute(script, params)

    result = await cur.fetchall()
    return result
