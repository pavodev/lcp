# Importer

Imports the BNC (British National Corpus) into the database. Usage:

- in config.py, set (files provided by Jonathan [*]):

  - `PATH_BNC_SCRIPT_SCHEMA_SETUP`: path to psql-script, which createds the new schema
  - `PATH_BNC_DATA_DOCUMENTS`: csv-file «vert_documents.csv»
  - `PATH_BNC_DATA_SEGMENTS`: " «vert_segments.csv»
  - `PATH_BNC_DATA_TOKENS`: " «vert_tokens.csv»
- moreover (config.py), you need to provide some information about the database (`name`, `host`, `port`, `user`, `pw`)
- finally, execute "python setup.py" (adds new schema / imports data)

[*] alternatively, you may simply exchange the source-files in "data/bnc/" and "scripts/"


## PostgreSQL-Server (localhost)

Simple way to get a running PostgreSQL-Server (Mac):

$ `brew update`
$ `brew install postgresql` (--> default db-cluster at /opt/homebrew/var/postgresql@14)

$ `brew services start postgresql` (`brew services stop postgresql`, `brew services restart postgresql`)
$ `psql postgres`
