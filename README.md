# uplord

> uplord monorepository

First, install Python 3.11 (though anything from 3.9 onward should work) or setup a Python 3.11 virtual environment.

Make sure you also have access to `abstract-query` and `lcp-upload` submodule repositories. Ask someone to grant you access if you need it.

## Setup

Then clone this repo and its submodules:

```bash
git clone --recurse-submodules https://gitlab.uzh.ch/LiRI/projects/uplord.git 
cd uplord
````

This will also clone the `abstract-query` and `lcp-upload` submodules. If they are not available in the `uplord` directory, you should remove the first two lines from `requirements.txt` before installing.

## Things that need to be running for uplord to work

* The backend (`./uplord`)
* The frontend (`./frontend`)
* LAMa (local or remote)
* PostgreSQL (local or remote)
* Redis (local or remote)
* At least one RQ worker
￼
`.env` defaults point to a local Redis, so install and run Redis or reconfigure to our deployed instance.

To install backend (and `abstract-query`, which is also required):

```bash
pip install -e abstract-query -e .
```

To build optional `c` extensions for both repos:

```bash
cd abstract-query
python setup.py build_ext --inplace
cd ..
python setup.py build_ext --inplace
```
￼
To start backend for development, first edit `.env` so that it contains the correct config.

Then, start as many RQ workers as you want. To start one:

```bash
# uses c code if available, otherwise py:
python -m uplord worker
# to only use .py:
# python uplord/worker.py
````

In another session, start the app with:

```bash
python -m uplord
```

It will use C extension modules if they are available, or else straight Python.

For the LAMa connection to work, you might need to do:

```bash
ssh -L 18080:192.168.1.57:8080 berlit.liri
```

For the frontend, you need to install `Node.js`, `npm` and `yarn`. For Ubuntu, that would be something like:

```bash
sudo apt update
sudo apt install nodejs
sudo apt install npm
npm install --global yarn
```

Then, if you haven't before, install the frontend:

```bash
cd frontend
yarn install
```

Then you can start it with:

```bash
# in uplord/frontend:
yarn serve
```

The app will be available at `http://localhost:8080`.

## Development

When pulling latest code, you should also fetch the latest from the submodules. You can do it all in one command:

```bash
git pull --recurse-submodules
```

You might also want to configure `git` to push changes to submodules when you push to `uplord`:

```bash
git config --global push.recurseSubmodules "on-demand"
```

### Type checking

To check that typing is correct (do before commit/push/c-extension building):
```bash
mypy uplord
```

## Configuration

The defaults in `.env` should work for PostgreSQL and LAMa. Default Redis is local, so you should have a Redis instance running as per the URL specified in `.env`.

Some `.env` values that might need adjusting for deployment:

> `AIO_PORT`

The port that the backend runs on.

> `REDIS_DB_INDEX`

Setting as a positive integer allows us to switch between different Redis databases based on their index. `0` is fine for development.

> `QUERY_TIMEOUT`

In seconds, how long can a query be running until it gets stopped?

> `UPLOAD_TIMEOUT`

In seconds, how long can an upload job be running until it gets stopped (should be considerably longer!)

> `QUERY_TTL`

In seconds, how long should query data stay in Redis? If a user tries to change pages on a query older than this, the query needs to be rerun from the start. It should work, but the UX is much worse than fetching from Redis.

> `MAX_REMEMBERED_QUERIES`

We keep a `dict` of `{query_hash: job_id}`, with `MAX_REMEMBERED_QUERIES` as the max size of the `dict`. When a user prepares to submit a query/sentences job, we compare the hashes to see if the query/sentence query is already done, and then look it up in Redis. If the data is still there, we return it quickly. Because we hash the query, this object doesn't take up much memory space, so a large value is fine here, but the setting prevents the app from growing in size over time. Set to `-1` for no limit.

> `SQL_(QUERY|UPLOAD)_(USERNAME|PASSWORD)`

The app uses two SQL connections. The `QUERY` connection should not have write access. The `UPLOAD` connection should. Note that storing queries also requires write access.

> `IMPORT_MAX_CONCURRENT`

When importing a new corpus, how many concurrent tasks can be spawned? Set to `-1` or `0` for no limit, set to `1` for no concurrency, or larger to set the concurrency limit.

> `IMPORT_MAX_MEMORY_GB`

When processing concurrently, a lot of data can be read into memory for `COPY` tasks. If this amount of data is reached while building `COPY` tasks, we stop building tasks, execute the pending ones, and resume when they are done. Remember that if `IMPORT_MAX_CONCURRENT` is not `1`, the real memory usage could be multiplied by the number of concurrent tasks.

> `IMPORT_MAX_COPY_GB`

In GB, how much data can be read in one chunk for `COPY` tasks? Note that the limit can be exceeded by a few bytes in practice to complete an incomplete CSV line. Remember that if `IMPORT_MAX_CONCURRENT` is not 1, the real memory usage could be multiplied by the number of concurrent tasks.

> `UPLOAD_USE_POOL`

If truthy, a real connection pool will be used for the uploader (as well as any other jobs requiring write access to the DB). `IMPORT_MIN_NUM_CONNECTIONS` and `IMPORT_MAX_NUM_CONNECTIONS` will only be respected if this is switched on. If falsey, these values are ignored, as no connection pool is used for write jobs.

> `(QUERY|UPLOAD)_(MIN|MAX)_NUM_CONNECTIONS`

These four values control the number of connections in the connection pools. If `UPLOAD_USE_POOL` is `false`, these numbers are ignored for `UPLOAD`, because no pool exists.

> `POOL_NUM_WORKERS`

This number controls how many worker threads are spawned to perform setup/cleanup-type operations on connection pool(s). `3` is the default provided by `psycopg`.

> `SENTRY_DSN`

If set, exception logs are sent to Sentry. You probably want to leave it unset for development.

> `SENTRY_TRACES_SAMPLE_RATE`

A float value `1.0` or smaller, dictating the proportion of logs that get sent to sentry. Maybe we need to reduce this if one day our app is super popular, but `1.0` is fine for now.

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

## Deployment

1. Pull latest code
2. Edit `.env` as necessary
3. Build c extensions if you want (see above)
4. Start as many workers as necessary
5. Start app:

```bash
gunicorn --workers 3 --bind 127.0.0.1:9090 uplord.deploy:create_app --worker-class aiohttp.GunicornUVLoopWebWorker
```

## Count lines of code 😉

```bash
apt-get install cloc
cloc . --exclude-dir=dist,build,node_modules,uploads,.mypy_cache,htmlcov \
       --exclude-lang=JSON \
       --not-match-f=dqd_parser
```
