#!/bin/bash
xz -dc /docker-entrypoint-initdb.d/initdb.sql.xz | psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
touch /tmp/db.ready
