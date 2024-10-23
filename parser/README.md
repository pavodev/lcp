## Guidelines to write the Lark file

 - Add `// skip: rule_name` to remove it from the json schema
 - Add `// rename: rule_name1>new_name1 rule_name2>new_name2` to change the property name in the json schema

 ## Generate the cobquec schema from the grammar

The grammar file must end in `.lark` and the json schema file (optional) nust end in `.json`

 `python lark_to_cobquec.py dqd_grammar.lark cobquec.auto.json`

Drop the JSON output into the left text box at https://www.jsonschemavalidator.net/ to check that it is a valid JSON schema

## Generate the JS file from the grammar

`lark-js` does not currently support Earley grammars; for now, we need to use an old js file generated from a previous lalr grammar

Possible solution: do syntax coloring/validation on the BE (using Python) and send it back to the FE?

~~Install `lark-js` on your machine if you don't have it yet:~~

~~`pip install lark-js --upgrade`~~

~~Then run:~~

~~`lark-js dqd_grammar.lark -o dqd_parser.js`~~

~~Insert a new line at the top of the file: `/* eslint-disable */` ~~

~~If you get an error message complaining about `strict`, you need to remove it from the `options` defined in the js file (look for `"strict"`)~~

~~Replace `lcpvian/frontend/src/dqd_parser.js` with the new file~~

## Run the whole pipeline at once

See note above

~~Run `./update.sh`~~

## Convert a DQD query to its JSON representation

 `python -m lcpvian dqd test.dqd`

The script will use the first `.lark` and the first `.json` files it finds in `lcpvian/parser` as its grammar and schema files, respectively

Note that queries **must** close all their indentations, so make sure to include a line break at the bottom of the test dqd file as needed

Drop the JSON output into the right text box at https://www.jsonschemavalidator.net/ (along with the corresponding schema on the left) to check that the schema validates it