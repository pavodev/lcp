# Glossary

## Layer

The term "layer" should always be qualified to clarify what it refers to. Most often, it will occur in the phrase "**annotation layer**", in which case it refers to a level of representation of the data that corpus creators can define arbitrarily. See [this page](model.md#layers) for more details.

Alternatively, the term "layer" could be understood as synonymous with "tier" or "track", as can be seen in tools such as ELAN, or in the timeline of VideoScope for example. Although the timeline can dedicate a single track to display the annotations of one annotation layer in the corpus, that need not be the case, and there is **no** systematic one-to-one correspondance between the annotation layers of a corpus and the tracks of a timeline.

## Track

The term "track", in this documentation, refers to a horizontal band that can report a variety of annotations in the timeline of a time-aligned corpus, as can be seen in VideoScope. For example, the timeline of a given document involving three speakers in a corpus could consist of three tracks, one track per speaker, which would report their respective sentences. Such a corpus need not define three corresponding _annotation layers_ (see above); instead, it most likely would have a single annotation layer grouping all the sentences of all the speaker, with an _attribute_ on that annotation layer serving to identify which speaker is associated with it.

## Entity

The term "entity" is used in the context of [DQD queries](dqd.md), and reflects the idea of [Entity-Relationship models](https://en.wikipedia.org/wiki/Entity%E2%80%93relationship_model). An entity is a unit that can have a _label_, constraints, and relate to other entities in the query. While most entities in DQD queries are directly associated to an _annotation layer_, the terms are not synonymous: for example, a DQD query can instantiate multiple entities on the same annotation layer (typically, multiple instances of the Token layer) and some entities do not match a single annotation layer unit: [sequences](sequence.md), [sets](set.md) or [groups](group.md) are entities in and of themselves (e.g. they can receive labels) but they contain _multiple_ units (for example, a sequence of several consecutive tokens).

## Unit

This term is used in the JSON representation of queries for to introduce entities that correspond to single annotation layer units: one token instance, one segment instance, etc.

## Metadata

There are at least two meaning of _meta(data)_ in LCP:

 1. The metadata of a **corpus**, as visible when clicking it from the homepage, and stored in the main database table
 2. The metadata on the **annotation layers** of a corpus, which need to be further distinguished:
    - outside of LCP, some people call "metadata" any non-standard annotation, such as optional comments associated with each token in an OCR corpus (as opposed to, say, _form_ and _lemma_, which are standard annotations for tokens); LCP has no such **pre**-conceived opposition between standard vs. metadata
    - on each annotation layer, the author of a corpus can decide to place attributes under a `meta` key, in which case the data is represented (and queried) differently in the database

