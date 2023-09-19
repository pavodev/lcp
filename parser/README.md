## Guidelines to write the Lark file

 - All aliases represent end up as a named property in the cobquec file
 - Rules whose name include `__` are rules that should never be direct properties: as such, no alias should ever end with `__`
 - If you need to repeat a disjunction inside a rule (eg `(rule_a|rule_b)+`) choose to define that disjunction as its own separate rule (and name it with a `__` if that disjunction should not correspond to a named property of `oneOf`'s)
 - Big disjunctions (multi-line rules using pipes `|`) are meant to represent exclusive **properties**, referenced elsewhere: as such, each line should have an alias

 - Rules whose name contains `<a-z>_<a-z>` will be referenced as `<a-z><A-Z>` in cobquec (CamelCase)
 - Rules whose name ends with `__` are forwarding rules: they will never create a named property in cobquec, instead their own properties will be inherited as oneOf's. **They should either be big disjunctions whose disjuncts are named rules (->`oneOf`), or point to a terminal (->`type:string`)**
 - Occurrences of `__<text>` will be deleted form a rule's name when referenced in cobquec
 - At the moment, one cannot write rules with nested brackets of the same type (embedding parentheses inside square brackets or the other way around is ok though)