# uplord

> uplord monorepository

First, install Python 3.11 (though anything from 3.8 onward should work).

Then, install the following dependencies:

```bash
git clone https://gitlab.uzh.ch/LiRI/projects/abstract-query
cd abstract-query
python setup.py develop

git clone https://gitlab.uzh.ch/LiRI/projects/corpert
cd corpert
python setup.py develop
```

Then clone this repo and do `pip install -r requirements.txt`

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

In another session, start RQ worker:

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

The defaults in `.env` should work for Postgres and LAMa. Default Redis is local, so you should have a Redis instance running as per host and port specified in `.env`.

### mypy

Check app for type problems:

```bash
# pip install mypy
mypy run.py
mypy worker.py
```

Build C extension:


```bash
mypyc run.py
```

Run:

```bash
python -c "import run"
```

Still working on compiling `worker.py`...