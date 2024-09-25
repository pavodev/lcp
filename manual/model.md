# Model

## Dimensions

Annotations can be aligned along one of three dimension:

  - **Stream** --
  - **Time** --
  - **Space** --

## Entities

Entities are defined in the [Corpus Template](corpus-template.md). Though arbitrary names can be used, we use *Document* for documents, *Segment* for sentence segments and *Token* for tokens in the examples. Entities are expected to start with an uppercase character.


## Attributes

Attributes are also defined in the [Corpus Template](corpus-template.md) and thus their naming is free for a corpus creator to define. As a standard set, we use *form* for word forms, *lemma* for lemmas, *upos* for [Universal part-of-speech tags](https://universaldependencies.org/u/pos/all.html), and *morph* for [Universal features](https://universaldependencies.org/u/feat/all.html). Attributes stored as [Meta Data](meta-data.md) is mapped to entity attributes unless a native attribute with the same name exists. In that case, the meta attribute needs to be explicitely referenced.