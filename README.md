# uplord

> uplord monorepository

First, install Python 3.11 (though anything from 3.9 onward should work).

Make sure you also have access to `abstract-query` and `lcp-upload` submodule repositories. Ask someone to grant you access if you need it.

Then clone this repo and its submodules:

```bash
git clone --recurse-submodules https://gitlab.uzh.ch/LiRI/projects/uplord.git 
cd uplord
pip install -r requirements.txt
````

This will also install the dependencies for `abstract-query` and `lcp-upload`. If they are not available in the `uplord` directory, you should remove the first two lines from `requirements.txt` before installing.

## Things that need to be running for uplord to work

* backend
* frontend
* LAMa
* Postgres
* Redis
* RQ worker

To start backend:

```bash
# optional:
# pip install mypy && mypyc run.py
python run.py
# or
python -m aiohttp.web -H localhost -P 9090 run:create_app
```

In another session, start as many RQ workers as you want. To start one:

```bash
python worker.py
````

For the LAMa connection to work, you might need to do:

```bash
ssh -L 18080:192.168.1.57:8080 berlit.liri
```

Start frontend:

```bash
cd frontend
# yarn build
yarn serve
```

## Development

When pulling latest code, you should also fetch the latest from the submodules. You can do it all in one command:

```bash
git pull --recurse-submodules
```

## Configuration

The defaults in `.env` should work for Postgres and LAMa. Default Redis is local, so you should have a Redis instance running as per host and port specified in `.env`.

Some `.env` values that might need adjusting for deployment:

> `QUERY_TIMEOUT`

In seconds, how long can a query be running until it gets stopped?

> `UPLOAD_TIMEOUT`

In seconds, how long can an upload job be running until it gets stopped (should be considerably longer!)

> `QUERY_TTL`

In seconds, how long should query data stay in Redis? If a user tries to change pages on a query older than this, the query needs to be rerun from the start. It should work, but the UX is much worse than fetching from Redis.

> `IMPORT_MAX_CONCURRENT`

When importing a new corpus, how many concurrent tasks can be spawned? Set to -1 or 0 for no limit, set to 1 for no concurrency, or larger to set the concurrency limit.

> `IMPORT_MAX_MEMORY_GB`

When processing concurrently, a lot of data can be read into memory for COPY tasks. If this amount of data is reached while building COPY tasks, we stop building tasks, execute the pending ones, and resume when they are done.

> `IMPORT_MAX_COPY_GB`

In GB, how much data can be read in one chunk for `COPY` tasks? Note that the limit can be exceeded by a few bytes in practice to complete an incomplete CSV line.

> `MAX_SIMULTANEOUS_JOBS_PER_USER`

Currently not used; in theory if there are free resources we could allow a user to query multiple batches simultaneously. If we end up allowing simultaneous mode, this value can be used to limit how many jobs (i.e. queries over batches) can be run at once.

## Testing

Once you have started a worker, our modest backend tests can be run with:

```bash
python -m unittest
# or:
pip install coverage  # if you don't have it
coverage run -m unittest
# produce an html report of test coverage:
coverage html
```

## mypy

Check app for type problems:

```bash
# pip install mypy
mypy run.py
mypy worker.py
```

Build C extension:


```bash
python setup.py build_ext --inplace
```

Run:

```bash
python -c "import run"
```

Still working on compiling `worker.py` with mypy...
