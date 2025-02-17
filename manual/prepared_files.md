# Prepared files

This page describes how to format the files of a corpus to be imported

## File Format

Except for the configuration JSON file, all the files should be Tab-Separated-Values (TSV) files

## Configuration file

The configuration file is a JSON file defining one key-value object, with three required keys:

 - `meta`: contains general infomration about the corpus, such as its name, its authors, etc.
 - `firstClass`: contains the name of the three special annotation layers of any LCP corpus:
    `document`, `segment` and `token`
- `layer`: this is where the annotation layer of the corpus are reported, along with their properties and attributes.
    The importer will look for TSV files whose names match the layers reported here. For example, if you have a key `"NamedEntity"` under `layer`, the importer will expect to find a file `namedentity.tsv` or else it will crash

There are two additional optional keys:

 - `globalAttributes`: defines complex attributes that are not specific to one annotation layer but are shared by multiple ones. For example, `speaker` is a typical global attribute (complex because it can have a collection of demographic information) that could apply to the segment layer and to another layer like "gesture" or "turn" 
 - `tracks`: for multimedia corpora, defines what information the timeline of soundscript/videoscope should display

### `meta`

 - `name`, `author`, `date`, and `corpusDescription` will be displayed in the corpus' details panel
 - `mediaSlots` (NOTE: this could be moved to a main key instead) concerns multimedia corpora. It's a key-value object where each key is an arbitrary name, and the value is an object with two keys:
    - `mediaType` can be either `video` or `audio`
    - `isOptional` can be either `true` or `false`
    When the `mediaSlots` key is present, the TSV file of the document layer should have a column named `media`. Each arbitrarily-named key under `mediaSlots` should have a correspondingly-named key in the jsonb object of the `media` column for each line that reports the filename corresponding to the document (could be ommitted if that media slot's `isOptional` key is `true`)

### `firstClass`

This always has exactly three keys:

 - `token`
 - `segment`
 - `document`

The values for each key is a string that reports the name of the annotation layer in this corpus. The keys listed under `layer` should at least contain those values: if `token` is `Word`, then there should be a key `Word` under `layer`; if there's no `Word` key under `layer` the import will crash, even if there's a key named `token` under `layer`

### `layer`

Each key under `layer` should be an annotation layer. The three annotation layers named in `firstClass` must have corresponding entries here

Each entry is a key-value object with the following keys:

 - `anchoring`: is a key-value object with three keys `location`, `stream` and `time` which can each be `true` or `false`. When `location` is true the file `{LAYER}.tsv` should have a column named `xy_box`, when `stream` is `true` it should have a column named `char_range` and when `time` is true is should have a column named `frame_range`. The token layer *must* define `anchoring` and `stream` *must* be set to `true`; layers that contain another layer defining anchorings automatically inherits those so `anchoring` can be ommitted (e.g. the segment and document layers need not define `anchoring`) but their TSV file should still contain the applicable columns (`xy_box`, `char_range`, `frame_range`)
 - `abstract`: can be `true` or `false` -- when `true`, the annotation layer puts other annotation layers in relation to one another (see `layerType=relation` below)
 - `contains`: should reference the name of another annotation layer,  when applicable (e.g. the segment layer reports the name of the token layer here) (NOTE: this could become an array for layers containing mutliple layers, e.g. segments could contain not only tokens but also named entities)
 - `layerType`: can be `unit`, `span` or `relation`
    - `unit` means that the annotation layer contains no child (e.g. the token layer)
    - `span` means that the annotation layer contains another annotation layer (e.g. the segment layer is a `span` because it necessarily contains another layer, the token layer)
    - `relation` means that the annotation layer puts two annotation layers in relation to each other. The `attributes` key (see below) must contain `source` and `target`
 - `attributes`: should report each attribute of the layer as an arbitrarily named key associated to an object with the following keys
    - `isGlobal`: can be `true` or `false` -- `true` only applies to enumerated values defined across corpora, such as upos or udep (from the universal dependencies standard)
    - `type`: can be `categorical`, `text`, `dict`, `number`
        - `categorical` means the possible values of this attribute are part of an enumarted list. When `isGlobal` is `false`, `attributes` should also have a key `values` listing the possible values (each 50 characters max). The file `{LAYER}.csv` should have a column named `{attribute}` directly listing the values of each row
        - `text` means the possible values are open. The importer will look for a file named `{LAYER}_{ATTRIBUTE}.tsv` reporting the indexed values in the corpus under `{attribute}_id` and the values under `{attribute}` (`{LAYER}.csv` should have a column named `{attribute}_id` not directly listing the text value, but instead reporting the corresponding index in `{LAYER}_{ATTRIBUTE}.tsv`)
        - `dict` means that the values are key-value objects. Just like `text`, the importer will look up `{LAYER}_{ATTRIBUTE}.tsv` to list the values. The values in the `{attribute}` column in that file should be jsonb objects
        - `number` means that the values are any integer or float values
    - `nullable`: can be `true` or `false` -- when `true` the TSV files can leave the corresponding cell empty
    - `name` and `entity` applies to two special attributes named `source` and `target` of layers of type `relation`. `name` is the name of the attribute, and `entity` is the name of the layer that the attribute points to. For example, a dependency-relation layer can put pairs of tokens in relation to each other, so `entity` would report the name of the token layer for both `source` and `target`
    - In addition to `source` and `target`, there is a third special key for `attributes` named `meta`, which lists further attributes using the same format. The difference is that `{LAYER}.tsv` will have a column named `meta` containing jsonb objects whose keys are the attribute names reported here, mapping to values. This should be reserved to less frequently used attributes, because using a jsonb objects prevents optimizing data storage and queries

### `tracks`

`tracks` has one mandatory key:

  - `layers` is a key-value object where each key is the name of a layer, and the values are (possibly empty) key-values objects. The only possible nested key is `split` whose value should be an array listing the layer's attributes used to create multiple lines for the layer in the timeline, one for each value of the attribute
  - `group_by` is an array listing global attributes used to group the lines in the timeline; the listed global attributes should be shared by all the layers in `layers`, otherwise displaying the timeline will crash

