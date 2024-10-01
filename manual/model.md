# Model

## Dimensions

Annotations must be aligned along at least one of three dimension:

  - **Stream** --
  - **Time** --
  - **Space** --

An entity being aligned to the stream dimension simply means that the entity has a textual representation - e.g. tokens in a conventional text corpus: In a flattened text corpus (= all text is concatenated into one large "string"), a single *Token* occupied a single, unambiguous spot, that can be described by means of a start and end position in that text stream.

Entities that can be temporally located, are aligned relative to the time axis. E.g. in a video corpus with annotated gestures, each *Gesture* has an unambiguous start and end time point relative to the video.

Lastly, entities can occupy a section on a 2-dimensional plane: E.g. on a scanned medieval document, each *Token* can be unambiguously located by its x- and y-coordinate.

## Entities

Entities are defined in the [Corpus Template](corpus-template.md). Though arbitrary names can be used, we use *Document* for documents, *Segment* for sentence segments and *Token* for tokens in the examples. As a convention to distinguish between Entities and e.g. variables in DQD queries, Entities are expected to start with an uppercase character.


## Attributes

Attributes are also defined in the [Corpus Template](corpus-template.md) and thus their naming is free for a corpus creator to define. As a standard set, we use *form* for word forms, *lemma* for lemmas, *upos* for [Universal part-of-speech tags](https://universaldependencies.org/u/pos/all.html), and *morph* for [Universal features](https://universaldependencies.org/u/feat/all.html). Attributes stored as [Meta Data](meta-data.md) is mapped to entity attributes unless a native attribute with the same name exists. In that case, the meta attribute needs to be explicitely referenced.
