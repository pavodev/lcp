# Importer

- CorpusData: requires a path to a corpus containing the files `vert_documents.csv`, `vert_segments.csv` and `vert_tokens.csv`
- CorpusTemplate (stub): requires a path to a sql-script to add the new corpus schema to the database
- Importer: provides functions (`add_schema(CorpusTemplate)`/`import_corpus(CorpusData)`) to add schema/data to the database

## PostgreSQL-Server (localhost)

Simple way to get a running PostgreSQL-Server (Mac):

$ `brew update`
$ `brew install postgresql` (--> default db-cluster at /opt/homebrew/var/postgresql@14)

$ `brew services start postgresql` (`brew services stop postgresql`, `brew services restart postgresql`)
$ `psql postgres`
