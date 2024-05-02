# abstract-query: JSON to SQL queries



> Note, this used to be a repo and is now inside the main LCP repository; references to installing it etc may remain.

## Usage

The module is used by `uplord` when users submit queries.

To use it without `uplord`, start a Python 3 session:

```python
import json
from lcpvian import json_to_sql

with open("query.json", "r") as fo:
	query_json = json.load(fo)

with open("config.json", "r") as fo:
	config_json = json.load(fo)

sql_query, meta_json = json_to_sql(query_json,
    schema="sparcling1",
    batch="token0",
    config=config_json,
    lang=None,
    vian=False
)
```

## Creating JSON queries

Use the DQD parser in `uplord`.

```

## Creating config JSON

This is tricky. You would first get the template and mapping from SQL `main.corpus` table. You then need to format it approximately like this:

```python
def make_config(template, mapping):
	return {
	    "document": template["firstClass"]["document"],
	    "segment": template["firstClass"]["segment"],
	    "token": template["firstClass"]["token"],
	    "mapping": mapping,
	    "uploaded": False,
	    **template
	}
```

## Development

This repository is a submodule of `uplord`. If you add the following git hook, and if this repository is a subdirectory of `uplord`, then commiting to this repo will also commit the change in `uplord`.

```bash
ln post-commit .git/hooks/post-commit
```

You might also want to set git to push submodules before pushing changes to `uplord`:

```bash
git config --global push.recurseSubmodules "on-demand"
```

You can remove the `--global` flag and do it locally on the `uplord` repo if you prefer.
