# LCP/VIAN

> Boths apps together in one monorepository!

First, install Python 3.11+ or setup a Python 3.11+ virtual environment.

Make sure you also have access to `abstract-query` and `lcp-upload` submodule repositories. Ask someone to grant you access if you need it.

## Setup

Then clone this repo and its submodules:

```bash
git clone --recurse-submodules https://gitlab.uzh.ch/LiRI/projects/lcpvian.git
cd lcpvian
````

This will also clone the `abstract-query` and `lcp-upload` submodules. If they are not available in the `lcpvian` directory, you should remove the first two lines from `requirements.txt` before installing.

You will also need to copy the `.env` config template to the path it needs to be at in order to be read:

```bash
cp .env.dev .env
```

## Virtual Environment

Skip this section if you don't want/need to set up a virtual environment for Python 3.11

Install `virtualenv` for Python:

```bash
pip install virtualenv
```

Create a virtual environment for lcpvian:

```bash
# Make sure you are out of lcpvian so you don't include the virtual environment as part of your commits
cd ~
virtualenv -p $(which python3.11) lcpvian-environment
```

Finally set your session to run commands from that environment:

```bash
source ~/lcpvian-environment/bin/activate
```

## Things that need to be running for lcpvian to work

* The backend (`./lcpvian`)
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

If you get an error saying that site-packages is not writeable, it probably means that you are not running in a virtual environment; see [Virtual Environment](#virtual-environment) for instructions on how to set up a virtual environment for Python


To start backend for development, first edit `.env` so that it contains the correct config. Comment out the `SSH_` variables if not using, or you'll get an SSH gateway error

Then, start as many RQ workers as you want. To start one:

```bash
# uses c code if available, otherwise py:
python -m lcpvian worker
# to only use .py:
# python lcpvian/worker.py
````

In another session, start the app with:

```bash
python -m lcpvian
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

You might need to install a specific version of node for compatibility concerns. As of August 9, 2023 the module `node-ipc` is incompatible with node 20+, so a sensible target version is 19. If you don't have `nvm` installed yet, you can install it from the `nvm-sh` github repo:

```bash
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.4/install.sh | bash
```

Close then reopen the terminal to install node 19:

```bash
nvm install 19
```

You can now go back to lcpvian and use node 19:

```bash
cd lcpvian
nvm use 19
```

Then, if you haven't before, install the frontend:

```bash
cd vian-eventdrops
yarn install
cd ../frontend
yarn install
```

Then you can start it with:

```bash
# in ./frontend:
# for LCP frontend
yarn serve:lcp
# for VIAN frontend
yarn serve:vian
```

The app will be available at `http://localhost:8080`.

## Development

When pulling latest code, you should also fetch the latest from the submodules. You can do it all in one command:

```bash
git pull --recurse-submodules
```

You might also want to configure `git` to push changes to submodules when you push to `lcpvian`:

```bash
git config --global push.recurseSubmodules "on-demand"
```

### Type checking

To check that typing is correct (do before commit/push/c-extension building):
```bash
mypy lcpvian
```

### C extensions

To build optional `c` extensions for both `abstract-query` and `lcpvian` repos:

```bash
cd abstract-query
python setup.py build_ext --inplace
cd ..
python setup.py build_ext --inplace
```

When these are built, the C code will be used instead of the Python, so changes to the repos won't be reflected in your development version until you rebuild or delete the C data with:

```bash
cd abstract-query
rm *.so; rm abstract_query/*.so; rm -r -f build
cd ..
rm *.so; rm lcpvian/*.so; rm -r -f build
```

## Configuration

The defaults in `.env` should work for PostgreSQL and LAMa. Default Redis is local, so you should have a Redis instance running as per the URL specified in `.env`.

Some `.env` values that might need adjusting for deployment:

> `DEBUG`

When this is truthy (`true`, `1`), certain sensitive info can be passed to frontend for display in error messages or console. Usually, this is error tracebacks or SQL scripts. When `debug` is falsey, sensitive values are sanitised.

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

> `USE_CACHE`

Queries are stored by a key in Redis, and this key is a hash of the data needed to generate the query. Therefore, when a new query is created, we hash it to check that it hasn't already been performed. If it has, and if `USE_CACHE` is truthy, we retrieve the earlier data from Redis and send that to the user (whio may be different from the one who generated the original query). You can disable this for debugging if the cache doesn't seem to be working correctly, but ideally it is switched on in production, as it provides a lot of performance benefit for common queries!

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

## Command line interface

Once `lcpvian` is installed you can run a variety of commands via `python -m lcpvian`

Start backend:

```bash
python -m lcpvian
```

Start worker:

```bash
python -m lcpvian worker
```

Convert DQD to JSON:

```bash
python -m lcpvian dqd file.dqd
```

Convert corpus tempate to DDL:

```bash
python -m lcpvian ddl file.json --tabwidth 4
```

List corpora and their configs:

```bash
python -m lcpvian corpora
```

Run query on corpus with id `1` (i.e. `sparcling`):

```bash
python -m lcpvian query 1 query.dqd
```

You can pass the query as a string, or as a filepath. If the filepath ends with `.json`, a JSON query is expected. Otherwise, DQD format is expected.

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
gunicorn --workers 3 --bind 127.0.0.1:9090 lcpvian.deploy:create_app --worker-class aiohttp.GunicornUVLoopWebWorker
```

## Count lines of code 😉

```bash
apt-get install cloc
cloc . --exclude-dir=dist,build,node_modules,uploads,.mypy_cache,htmlcov \
       --exclude-lang=JSON \
       --not-match-f=dqd_parser
```
