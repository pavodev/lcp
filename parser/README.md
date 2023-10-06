## Guidelines to write the Lark file

 - All aliases end up as a named property
 - Rules whose name include `__` are rules that should never be direct properties: as such, no alias should ever end with `__`
 - If you need to repeat a disjunction inside a rule (eg `(rule_a|rule_b)+`) choose to define that disjunction as its own separate rule (and name it with a `__` if that disjunction should not correspond to a named property of `oneOf`'s)
 - Big disjunctions (multi-line rules using pipes `|`) are meant to represent exclusive **properties**, referenced elsewhere: as such, each line should either reference a single rule name, or define an alias
 - Rules whose name contains `<a-z>_<a-z>` correspond to properties named using `<a-z><A-Z>` (CamelCase, `string_comparison` -> property name -> `stringComparison`)
 - Rules whose name ends with `__` never create named properties, instead their own properties will be inherited by the parent. **Those rules should either be big disjunctions (->`oneOf`) or point to a terminal (->`type:string`)**
 - Rules whose name include `__<text>` that correspond to properties will have occurrences removed from the property names (`args__one` -> property name -> `args`)
 - At the moment, one cannot write rules with nested brackets of the same type (embedding parentheses inside square brackets or the other way around is ok though)
 - Repetitions should *not* be embedded: defining one rule as `SEQUENCE members` and another one as `members: statement__+` is *not* OK; instead, one should write `SEQUENCE members+` and `members: statement__`
 - Plain keywords should in general be included in a rule via the definition of a terminal: prefer `SEQUENCE members` over `"sequence" members`
 - Use indices on terminal rules to handle priority: using `3` in `GROUP.3 : /group/` vs `2` in `VARIABLE.2 : /[a-zA-Z_][a-zA-Z0-9_\.]*/` allows the parser to not rush to the more liberal regex when encountering `g` in the DQD query, thus preventing an crashing parse


 ## Generate the cobquec schema from the grammar

The grammar file must end in `.lark` and the json schema file (optional) nust end in `.json`

 `python lark_to_cobquec.py dqd_grammar.lark cobquec.auto.json`

Drop the JSON output into the left text box at https://www.jsonschemavalidator.net/ to check that it is a valid JSON schema

## Generate the JS file from the grammar

Install `lark-js` on your machine if you don't have it yet:

`pip install lark-js --upgrade`

Then run:

`lark-js dqd_grammar.lark -o dqd_parser.js`

Insert a new line at the top of the file: `/* eslint-disable */` 

If you get an error message complaining about `strict`, you need to remove it from the `options` defined in the js file (look for `"strict"`)

Replace `lcpvian/frontend/src/dqd_parser.js` with the new file

## Run the whole pipeline at once

Run `./update.sh`

## Convert a DQD query to its JSON representation

 `python -m lcpvian dqd test.dqd`

The script will use the first `.lark` and the first `.json` files it finds in `lcpvian/parser` as its grammar and schema files, respectively

Note that queries **must** close all their indentations, so make sure to include a line break at the bottom of the test dqd file as needed

Drop the JSON output into the right text box at https://www.jsonschemavalidator.net/ (along with the corresponding schema on the left) to check that the schema validates it