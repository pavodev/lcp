# Part 2: Processing the data

## No time alignment

For the sake of illustration, we will start by generating non-time-aligned files. We will write a script that increments a counter for each character in the transcript, such that:

 - if the character is **not** among `,`, ` `, `.`, `?` or `!`, it goes into a string buffer and the counter is incremented by 1
 - if the character **is** `,` or ` ` (<span style="color:lightblue">**blue**</span> and <span style="color:orange">**orange**</span> lines below): we have a full token in the buffer, we add a line to `token.csv` along with its span on the character axis and a form ID; we also add a line to `token_form.csv` that reports the form ID + form string association
 - if the character is `.`, `?` or `!` (<span style="color:red">**red**</span> lines below): we have reached the end of a sentence, we add a new line to `segment.csv` along with its span on the character axis
 - if the character is a linebreak at the start of a new line we ignore the next two line (block number and time stamps)


<p>
  <img src="images/tuto_scan.png" alt="Character by character steps" width="1252"/>
</p>

A python script that implements this logic (across two SRT files) can be found [here](https://github.com/liri-uzh/lcp_tutorial/blob/main/text_no_lemma/convert.py).

### Configuration file

Before we can upload our files, we need to create a configuration file to let LCP know how to handle the tables. The configuration file is a JSON file which reports some metadata information about the corpus (its name, its authors, etc.) the annotation layers present in the corpus and their attributes. The information is used not only to create entries in the database, but also to inform the engine about what data in the corpus can be queried, and how.

In our case, things are pretty simple, let us see what the configuration file needs to look like:

```json
{
    "meta": {
        "name": "Test Corpus",
        "author": "LCP tutorial",
        "date": "2025-03-26",
        "version": 1,
        "corpusDescription": "Test corpus from the tutorial"
    },
    "firstClass": {
        "document": "Document",
        "segment": "Segment",
        "token": "Token"
    },
    "layer": {
        "Document": {
            "layerType": "span",
            "contains": "Segment",
            "attributes": {}
        },
        "Segment": {
            "layerType": "span",
            "contains": "Token",
            "attributes": {}
        },
        "Token": {
            "layerType": "unit",
            "anchoring": {
                "stream": true,
                "time": false,
                "location": false
            },
            "attributes": {
                "form": {
                    "type": "text",
                    "nullable": false
                }
            }
        }
    }
}
```

The first key, `firstClass`, simply defines the names your corpus uses for the three basic annotation layers, as shown to the end-user, and in this case we use straightforward names.

Under `layer` should be reported one key for each annotation layer in the corpus. In this case, we work with a very basic corpus, so we only define the three basic annotation layers. Note that for the basic layers, the names need to match exactly the values defined in `firstClass` (i.e. the names start with an uppercase character, not a lowercase one). The names of the CSV files also need to match those names, although the filenames should use lowercase characters exclusively; this is also true of the column names (`document_id`, `segment_id`, `token_id`). For example, had we reported `"segment": "Sentence"` in `firstClass`, we would have used `"Sentence"` as key instead of `"Segment"` in `layer`, `sentence.csv` instead of `segment.csv` as a filename and the column's name would have been `sentence_id`.

The `Document` and `Segment` layers are straightforward: they are spans of segments and token units, respectively, and have no attributes exposed to the user (their IDs and character ranges exist for database-related purposes only and, as such, are not considered attributes here).

The `Token` layer is of type `"unit"` because it is parent to no further annotation layer. The token layer of any corpus must always define `anchoring`: it tells LCP whether the table has a `char_range` column (i.e. `stream` is set to `true`) and whether it has other types of ranges, for timestamps (`time` -- more about this later in this tutorial) or for XY coordinates (`location` -- not covered in this tutorial). Finally, `attributes` lists the attributes of the tokens, in this case only `form`. Note that the names reported in `attributes` need to match exactly the column names in the CSV files: token_form.csv, in addition to being named after the exact lowercase versions of the layer's name and the attribute's name, has a column named *exactly* `form` and another one named `form_id`, while token.csv also has a column named `form_id`. Attribute names should always use under_score casing and can never include uppercase characters. Like we said earlier, the `form` attribute is of type `text` because the possible values are numerous, and when LCP sees an attribute of type `text` on an annotation layer in the configuration file, it requires a lookup file named `{layer}_{attribute}.csv` in addition to `{layer}.csv`. Finally, the `form` attribute is set to `nullable`=`false` because we do not accept tokens with an empty form.

### One last step

In its current state, LCP also requires the token layer of all corpora to define a `lemma` attribute of type `text` besides `form`, otherwise import will crash. 

{% hint style="info" %}
Take a moment to think of how you would modify the python script to add that attribute (re-using the same values as for `form`) and how you would update the configuration file to report that attribute.
{% endhint %}

An updated python script and an updated configuration file can be found [here](https://github.com/liri-uzh/lcp_tutorial/tree/main/text_with_lemma).

### Import

Run the python script, save the JSON configuration in a file named meta.json alongside your CSV files in your output folder. Install the `lcpcli` tool:

`pip install lcpcli`

Now visit [catchphrase](https://catchphrase.linguistik.uzh.ch) and create a new corpus collection, then open its setting by clicking the gear icon, click the "API" tab and create a new API key; write down the key and the secret.

Open a terminal and run the following command, replacing `$API_KEY` with the key you just got, `$API_SECRET` with the secret you just got and `$PROJECT` with the name of the collection you just created:

`lcpcli -c path/to/output/ -k $API_KEY -s $API_SECRET -p "$PROJECT" --live`

You should get a confirmation message, and your corpus should now be visible in your collection after you refresh the page!


### Adding annotations

For the sake of illustration, we will now add two pieces of annotation: on the segment annotation layer, we will report the original text of each segment (which will include the token-delimiter characters) and on the token annotation layer, we will report whether it was preceded by a single quote (we will name the attribute `shortened`). The former will be of type `text`, just like the `form` and `lemma` attributes on the token layer, so we will create a lookup table file named `segment_original.csv`. The latter will be of type `categorical` with two possible values (`yes` and `no`) which will be reported directly in `token.csv`.

Adding the `original` attribute to Segment follows the same logic as handling the `form` and `lemma` attributes of the Token layer.

```python
import csv

from os import path, mkdir
from re import search, split
from uuid import uuid4

documents = ["transcript1.srt", "transcript2.srt"]  # the documents to process


# helper method to return a new CSV writer after writing the headers
def csv_writer(file, headers):
    writer = csv.writer(file)
    writer.writerow(headers)
    return writer


# helpler method returning char_range in the proper format
def to_range(lower, upper):
    return f"[{lower},{upper})"


# custom class that will process and write the files
class Converter:

    # pass the output files + headers as keys, e.g. document=(doc_file,["document_id","char_range"])
    def __init__(self, **kwargs):
        self.char_range = 1  # incremented with each character of a token
        self.document_id = 1  # incremented with each document
        self.token_id = 1  # increment with each token
        self.token_delimiters = (
            r"[', ]"  # the characters that separate tokens in the input
        )
        self.segment_delimiters = (
            r"[.?!]"  # the characters that mark the end of a segment in the input
        )
        # associate the unique values to IDs for lookup purposes
        self.lookups = {
            "form": {},
            "original": {},
        }
        # the CSV outputs
        self.outputs = {
            filename: csv_writer(file, headers)
            for filename, (file, headers) in kwargs.items()
        }

    # helper method that writes to the segment and token files
    def process_segment(self, text):
        text = text.strip()
        if not text:  # ignore this segment if it is empty
            return
        forms = self.lookups["form"]
        # lower bound of the segment's char_range
        char_range_seg_start = self.char_range
        seg_id = uuid4()  # use a uuid for the segment
        token = ""  # string buffer for the token being currently processed
        shortened = False  # is the current token preceded by a single-quote character?
        # read the text one character at a time (make sure it ends with a token delimiter)
        for c in text + ",":
            # if we hit a token delimiter: write the current token (if any)
            if search(self.token_delimiters, c):
                if not token:
                    continue
                # retrieve and store the form's ID
                form_id = forms.get(token, len(forms) + 1)
                forms[token] = form_id
                # write the token's information to the output
                self.outputs["token"].writerow(
                    [
                        self.token_id,
                        form_id,  # we use the same values for form
                        form_id,  # as for lemma
                        "yes" if shortened else "no",
                        to_range(self.char_range, self.char_range + len(token)),
                        seg_id,
                    ]
                )
                # increment the char_range counter by the number of characters in the token
                self.char_range += len(token)
                self.token_id += 1
                # if the token delimiter is a single quote, mark the next token as shortened
                shortened = c == "'"
                token = ""
            else:
                token += c  # append the character to the string buffer
        originals = self.lookups["original"]
        # retrieve and store the original text's ID
        original_id = originals.get(text, len(originals) + 1)
        originals[text] = original_id
        # now that all the tokens have been processed, write the segment to the segment file
        self.outputs["segment"].writerow(
            [
                seg_id,
                to_range(char_range_seg_start, self.char_range),
                original_id,
            ]
        )
        return

    # This will be called on each input file
    def process_document(self, file):
        char_range_doc_start = self.char_range  # lower bound of doc's char_range
        current_segment = ""  # buffer storing the curent sentence's text
        new_block = True  # are we starting a new block from the transcription file?
        while line := file.readline():
            if new_block:
                # in SRT files, at the start of a new block, the first two lines
                # are the block number and the timestamps: we skip both of those
                file.readline()
                new_block = False
                continue
            if line == "\n":
                # in SRT files, an empty line signals the start of a new block
                new_block = True
                continue
            # from here on out we the line contains some actual transcript
            line = line.rstrip()
            if not search(self.segment_delimiters, line):
                # if the line has no segment delimiter, add it to the current segment
                current_segment += " " + line
            else:
                # if there's at least one segment delimiter, proceed in two times:
                # first end the current segment, then process the remainder content
                end_of_current_segment, *remainder = split(
                    self.segment_delimiters, line
                )
                current_segment += " " + end_of_current_segment
                # call process_segment now to write the current segment and its tokens to the files
                self.process_segment(current_segment)
                # now process any remaining content
                current_segment = ""
                for middle_segment in remainder[1:-1]:
                    # the line could have full segments in the middle, as in "ipsum. lorem ipsum. lorem"
                    # if it does, call process_segment on each of those middle chunks
                    self.process_segment(middle_segment)
                # start a new current_segment with the last tokens in the line
                current_segment = remainder[-1]
                if search(self.segment_delimiters + "$", line):
                    # but if the line actually *ends* with a segment delimiter,
                    # call process_segment on the last tokens and start afresh
                    self.process_segment(current_segment)
                    current_segment = ""
        # we are done with the current document: write it to the document file
        self.outputs["document"].writerow(
            [
                self.document_id,
                to_range(char_range_doc_start, self.char_range),
            ]
        )
        # increment the counter for the next document
        self.document_id += 1
        return

    # called at the end: write the lookup files
    def write_lookups(self):
        for form, form_id in self.lookups["form"].items():
            self.outputs["token_form"].writerow([form_id, form])
            self.outputs["token_lemma"].writerow([form_id, form])
        for original, original_id in self.lookups["original"].items():
            self.outputs["segment_original"].writerow([original_id, original])
        return


# create the output folder if it doesn't exist yet
if not path.exists("output"):
    mkdir("output")

# we first create all the output files
with open(path.join("output", "document.csv"), "w") as doc_output, open(
    path.join("output", "segment.csv"), "w"
) as seg_output, open(
    path.join("output", "segment_original.csv"), "w"
) as original_output, open(
    path.join("output", "token.csv"), "w"
) as tok_output, open(
    path.join("output", "token_form.csv"), "w"
) as form_output, open(
    path.join("output", "token_lemma.csv"), "w"
) as lemma_output:

    # initiate an instance of Converter with the output files
    converter = Converter(
        document=(doc_output, ["document_id", "char_range"]),
        segment=(seg_output, ["segment_id", "char_range", "original_id"]),
        token=(
            tok_output,
            [
                "token_id",
                "form_id",
                "lemma_id",
                "shortened",
                "char_range",
                "segment_id",
            ],
        ),
        segment_original=(original_output, ["original_id", "original"]),
        token_form=(form_output, ["form_id", "form"]),
        token_lemma=(lemma_output, ["lemma_id", "lemma"]),
    )

    # now process each document
    for document in documents:
        with open(document, "r") as doc_file:
            converter.process_document(doc_file)

    # finally, create the lookup files
    converter.write_lookups()
```

Updated JSON configuration:

```json
{
    "meta": {
        "name": "Test Corpus",
        "author": "LCP tutorial",
        "date": "2025-03-13",
        "version": 1,
        "corpusDescription": "Test corpus from the tutorial"
    },
    "firstClass": {
        "document": "Document",
        "segment": "Segment",
        "token": "Token"
    },
    "layer": {
        "Document": {
            "layerType": "span",
            "contains": "Segment",
            "attributes": {}
        },
        "Segment": {
            "layerType": "span",
            "contains": "Token",
            "attributes": {
                "original": {
                    "type": "text",
                    "nullable": false
                }
            }
        },
        "Token": {
            "layerType": "unit",
            "anchoring": {
                "stream": true,
                "time": false,
                "location": false
            },
            "attributes": {
                "form": {
                    "type": "text",
                    "nullable": false
                },
                "lemma": {
                    "type": "text",
                    "nullable": false
                },
                "shortened": {
                    "type": "categorical",
                    "values": [
                        "yes",
                        "no"
                    ]
                }
            }
        }
    }
}
```

### Time alignment and video

The corpus we prepared in part 1 in a text-only corpus: the token layer (and, by inheritence, the segment and document layers) are only anchored on `stream` and, correspondingly, their tables have a column named `char_range`. In this section, we will use the timestamps from the transcript files to add an anchor on `time`, and we will associate each document with its video file.

Using the timestamps from SRT files for this purpose illustrates a common challenge when preparing corpus data for a specific tool: oftentimes, the incoming data does not present a one-to-one correspondence with the entities defined in the tool's model. We already saw earlier that transcript files do not report one segment (as we defined it) per line and had to work around it. A related complication is that the timestamps in the SRT files do not perfectly align with the segments we extract, so we will again need to find a workaround. Additionally, while we reported the tokens as character-anchored, with its parent layers inheriting that anchoring, and accordingly wrote a `char_range` column in the tables of all three layers, the timestamps in the SRT files give no precise information about the time alignment of the _tokens_.

We will therefore proceed as follows. We will _not_ anchor the tokens on `time`, but only the segments and the documents; accordingly, the tables of the latter two will contain a `frame_range` table (the name of the corresponding column, more on that later) while the table of former will not. Furthermore, we will approximate the start- and end-time of each segment by using the timestamps of the first and last blocks of text that contain the text of the current segment. This means that when the text in a block contains a segment delimiter (e.g. `.`) then a segment will end at the timepoint to the right of `-->` while another segment will start at the timepoint to the left of `-->`, thus creating overlap. Fortunately, temporal overlaps are not an issue in LCP.

The `frame_range` column reports values in frame units, with a set ratio of 25 frames per second. Therefore, a segment that start 15s from the start of a video and ends at 20s will have a `frame_range` of `[375,500)` (note that the syntax is the same as for `char_range`). Finally, just like with `char_range`, we do _not_ reset the counter between documents: there is a single, unidimensional temporal axis, just like there is a single, unidimensional character axis. This way, each annotation entity is unambiguously placed along either axis, which makes for much faster lookup when the engine runs queries.

In addition to the column `frame_range`, which we add to both the segment and the document tables, we will add two columns to the document table: one column named `name`, which will report the name to be used in LCP for browsing purposes, and one column named `media`, which will report which video file to use for playback in LCP. The names are reported as-in in the former column (no lookup table) and the `media` column reports stringified JSON key-value objects with a key (here, `video`) mapping to the filename of the media file correspondig to the document.

An updated python script and an updated configuration file can be found [here](https://github.com/liri-uzh/lcp_tutorial/tree/main/video).

{% hint style="warning" %}
In addition to creating new files and new columns, we also revised our tokenization approach: instead of using the `split` method, we now parse the text one character at a time. This is because we want to detect whether a single quote precedes a token, so we can appropriately report `yes` or `no` in the `shortened` column of `token.csv`.
{% endhint %}



{% hint style="warning" %}
The configuration file only requires minimal edits. First, because this is now a multimedia corpus, we need to report a `mediaSlots` key-value object in `meta`. Each key in `mediaSlots` needs to have a correspondingly named key (in this case, `video`) in the object from the `media` column of the document's table, which will report the filename to display in LCP for that document. LCP allows assocations of more than just one media file per document, but we will keeps things simple here.

Finally, we now report explicit `anchoring` settings for the segment and document layers (with `time` set to `true`), because they no longer correspond to the `anchoring` settings for the token layer.
{% endhint %}

Make sure you place the mp4 files in a `media` subfolder in the output folder. The upload command remains the same as before, but the process will include one extra last step to upload the media files, which can take some time depending on your connection.

When you visit your corpus on _videoScope_, you will notice a video player and a timeline. By default, the timeline displays the segment attributes. Because this corpus has a single segment attribute, the timeline reports the `original` text, aligned according to the `frame_range` value of the corresponding segment.