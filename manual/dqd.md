# The DQD Query Language

LCP's query language _DQD_ (**D**escriptive **Q**uery **D**efinition) follows the idea of [Entity-Relationship models](https://en.wikipedia.org/wiki/Entity%E2%80%93relationship_model). A DQD query defines sets of entities by listing logical constraints on their properties and on their relations to one another. The query engine then searches for those constellations of entities inside the selected corpus or corpora. Along the lines of first order logic, DQD includes quantors, which can be employed to enforce the existence or non-existence of constellations.

In addition to the declaration of sets of entities and their constraints, every query needs to specify at least one result set, which is either a (plain) list of entities comprising the query matches, a statistical or a collocational analysis.


## Introduction

In a text corpus with standard annotations (viz the [CoNLL-U format](https://universaldependencies.org/format.html)), a simple query for the occurrence of the word "dogs" would look like this:
```
Segment s

Token@s t
    form = "dogs"

Result => plain
    context
        s
    entities
        t
```

We proceed to explain this simple query below.

### Instantiation and Scopes

Entities are instantiated by providing the name of their [annotation layer](model.md#layers), followed by a (unique) label, which can be used to reference the entitiy later on.
An entity is by default existantially quantified, and its scope ranges from its instanciation to the end of the query. Exceptions are negative existential quantification and entities inside sequences with repetitions (see below).

### `Segment s`

An entity on the annotation layer "Segment" (modeling sentences) is instantiated, with the label "s" assigned to it. 

### `Token@s t`

An entity on the annotation layer "Token" is instantiated, with the label "t" assigned to it. 
The part-of operator `@` requires the current entity to be part of the entity whose label comes to the right of the operator. In this case, the Token entity `t` is required to be part of the segment `s`.


## Constraints

Simple constraints usually use the format `left operator right`. The constraint in the example above respects this schema, where `left` is `form`, `operator` is `=` and `right` is `"dogs"`.

### Regular expressions

In addition to plain strings, DQD supports references to regular expressions by enclosing a string in forward slashes (`/`). For example, the constraint `upos = /^(VERB|AD[JV])$` expresses that the value of the `upos` attribute should either one of `VERB`, `ADJ` or `ADV`.

### `sequence`

One can use the keyword `sequence` to look for consecutive entities. The query below, for example, looks for artciles that are _immediately_ followed by the word "dogs". Note that `sequence` also accepts the `@` operator (all entities defined in the sequence must then be part of the referenced entity) and labels for future references to the sequence.

```
Segment s

sequence@s seq
    Token t1
        upos = "DET"
    Token t2
        form = "dogs"
```

#### Repetitions and nesting

The `sequence` keyword also accepts a _repetition_ operator of the form `n..m` to look for `n` to `m` occurrences of the defined sequence. Use `0` for `n` to make the sequence optional, and `*` for `m` to allow for an arbitrary number of repetitions.

The repetition operator would normally only prove useful when a sequence is _nested_ within another sequence, as in:

```
Segment s

sequence@s seq
    Token t1
        upos = "DET"
    sequence 0..*
        sequence 0..1
            Token
                upos = "ADV"
        Token
            upos = "ADJ"
    Token t2
        form = "dogs"
```

This query looks for sequences (labeled `seq`) which start with a determiner and end with the word "dogs"; between these two tokens can _optionally_ appear a subsequence any number of times (`sequence 0..*`). That subsequence ends with an adjective, which can be optionally preceded by at most one adverb (`sequence 0..1`). As a result, this query would match not only `the dogs`, but also `some cute dogs` or even `the almost extinct wild dogs`.

Note that subsequences in the scope of a main `sequence` keyword that is already bound by the `@` oeprator necessarily inherit that scope, so we don't need to repeat the `@` operator on the nested `sequence` keywords. We also decided not to give a label to the sub-sequences, for we did not need to reference them anywhere; moreoever, because these subsequences are quantified expressions (cf. their repetition operators) the tokens they contain are bound variables and, as such, cannot be referenced outside of the scope of those subsequences (accordingly, we didn't label those tokens either).

### `set`

By default, each block matches one corresponding occurrence at a time. This means that the query below will match each possible pair of a verb with any of its (possibly many) dependencies as a separate result.

```
Segment s

Token@s tv
    upos = "VERB"

Token@s to
    DepRel
        head = tv
        dep = to
```

Say your corpus contains a segment with this sequence of tokens: `Moisha gave you something`. Assuming standard dependency relations, the query will match `s = <Moisha gave you something>, tv = <gave>, to = <you>`, but it will also match `s = <Moisha gave you something>, tv = <gave>, to = <something>` as a separate result; indeed, the latter triplet is different from the former and, as such, it constitutes a distinct match, even though the segment and the first token are the same in both matches

If you'd rather capture all possible dependencies of the verb as part of the same, single match, you can declare the corresponding `Token` block inside a `set` block:

```
Segment s

Token@s tv
    upos = "VERB"

set tos
    Token@s to
        DepRel
            head = tv
            dep = to
```

This query will now match `Moisha gave you something` with `s = <Moisha gave you something>, tv = <gave>, tos = [<you>,<something>]`, and that's it!

One way to understand this behavior is that blocks that start with a name of a layer, such as a `Token` block, are existentially bound and implicitly conjoined. Having two successive `Token` blocks roughly means "//any// token such that {this} **and** //any// token such that {that}". The keyword `set`, however, can be seen as carrying a universal force, so that when a `Token` block is embedded inside a `set` block, it becomes bound by the universal quantification. The `set` block above would then roughly translate as "//all// the entities that correspond to [//any// token that depends on the verb]"

## Results

There is no formal separation between the query part and the results part of a DQD script, other than the convention of writing the results part after the query part. Results blocks always start with a variable name, a fat arrow (`=>`) and one of the three keywords `plain`, `analysis` or `collocation`.

1. `plain`

The `plain` keyword will give you back matching entities in the context in which they occur. It is formed of two sub-blocks defined by the keywords `context` and `entities`. `entities` should reference variable names of the matching entities you are interested in, and `context` should reference a variable name of a matching entity that contains the ones in `entities`.

The example below repeats the query part from the [[#DepRel|DepRel]] section and adds a simple `plain` results part, which asks to show each possible pair of the (possibly inflected) verb //take// with an object of its, shown in the context of the segment that contains them

```
Segment s

Token@s t1
    upos = "VERB"
    lemma = "take"
      
Token@s tx
    DepRel
        head = t1
        dep = tx
        label = "dobj"


myKWIC1 => plain
    context
        s
    entities
        t1
        tx
```

The LCP will display the results in a tab named //myKWIC1//, as specified by the variable name before the fat arrow. That tab will show one segment per row, in which the instances of //take// and its object will be highlighted

2. `analysis`

The `analysis` keyword will give you back a statistical transformation of attributes, optionally filtered. It is formed of two (optionally three) sub-blocks defined by the keywords `attributes` and `functions` (and optionally `filter`). `attributes` should reference attributes of entities, using the format `entity_variable.attribute`, that the statistical transformations will be applied to. `functions` should reference one or more function names that apply a statistical transformation: `frequency`, `minimum`, `maximum`, `average` or `stddev`. Finally, the optional `filter` block lets you exclude some lines from the results; for example, specifying `frequency > 5` in the `filter` block below has the effect of excluding lemmas that appear less than 6 times from the `myStat1` table

Example:

```
myStat1 => analysis
    attributes
        tv.lemma
        to.lemma
    functions
        frequency
    filter
        frequency > 5
```

The LCP will display the results in a tab named //myStat1//, as specified by the variable name before the fat arrow. That tab will show one lemma per row, along with how many times that lemma occurs in the queried corpus (as long as it occurs at least 6 times).


3. `collocation`

The `collocation` keyword will give you back a table listing how often entities appear near the referenced entity/entities. It comes in two different formats:

  - One option is to provide a `center` sub-block and a `window` sub-block. `center` should reference an entity variable (eg `t1`) and `window` should specify how many entities ahead and behind of that reference entity the collocation measure should be performed (eg `-2..2`)
  - Another option is to provide a `space` sub-block which should reference a set variable, in which case the collocation measure will be performed between the first and the last entity in the set.

Example:

```
myColl1 => collocation
    center
        t1
    window
        -2..+2
    attribute
        lemma
```

The LCP will display the results in a tab named //myColl1//, as specified by the variable name before the fat arrow. That tab will show one lemma per row, along with how many times that lemma co-occurs within 2 tokens ahead and 2 tokens behind the `t1` matches.

## Advanced features

### DepRel

Corpora can model universal dependency relations (as is standard in CoNLL-U) on a dedicated annotation layer. For example, the query below will look for all pairs of tokens that belong to the same segment, where one is a form of the verb _take_ and the other is the object of that verb (in this example the annotation layer _DepRel_ uses the label `%%"dobj"%%` to tag direct objects, but that may vary from corpus to corpus).

```
Segment s

Token@s t1
    upos = "VERB"
    lemma = "take"
      
Token@s tx
    DepRel
        head = t1
        dep = tx
        label = "dobj"
```