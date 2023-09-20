## Guidelines to write the Lark file

 - All aliases end up as a named property
 - Rules whose name include `__` are rules that should never be direct properties: as such, no alias should ever end with `__`
 - If you need to repeat a disjunction inside a rule (eg `(rule_a|rule_b)+`) choose to define that disjunction as its own separate rule (and name it with a `__` if that disjunction should not correspond to a named property of `oneOf`'s)
 - Big disjunctions (multi-line rules using pipes `|`) are meant to represent exclusive **properties**, referenced elsewhere: as such, each line should either reference a single rule name, or define an alias
 - Rules whose name contains `<a-z>_<a-z>` correspond to properties named using `<a-z><A-Z>` (CamelCase, `string_comparison` -> property name -> `stringComparison`)
 - Rules whose name ends with `__` never create named properties, instead their own properties will be inherited by the parent. **Those rules should either be big disjunctions (->`oneOf`) or point to a terminal (->`type:string`)**
 - Rules whose name include `__<text>` that correspond to properties will have occurrences removed from the property names (`args__one` -> property name -> `args`)
 - At the moment, one cannot write rules with nested brackets of the same type (embedding parentheses inside square brackets or the other way around is ok though)