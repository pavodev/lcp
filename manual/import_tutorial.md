# Import Tutorial

In this tutorial, you will learn how to import video files with timed transcripts into LCP. In the first part, you will learn how to generate a text-only corpus from the transcript files using python. In the second part, you will learn how to also integrate the timecodes so you can upload the corpus of transcripts along with their videos to LCP.

## Files

Download the video files and their timed transcripts here: https:///.

## Part 1: text only

### Desired output

All text corpora in LCP structure define at least three levels, or *annotation layers*: *tokens*, which roughly correspond to individual words, *segments*, which roughly correspond to sentences, i.e. sequences of tokens, and *documents*, which in our case will each correspond to one video, i.e. sequences of segments. Corpus curators could decide to add intermediary annotation layers between segments and documents (e.g. paragraphs, which would be sequences of segments, so that documents would in turn contain sequences of paragraphs) but in this tutorial we will stick to the three basic levels.

Our approach will be as follows: each transcript file will correspond to a document, and each sequence of characters separated by a whitespace, a linebreak or single quote character will be modeled as a token; we will use periods, exclamation and question marks are delimiters for segments and ignore other punctuation signs. We intentionally keep things simple in this tutorial, although such an approach would be too simplistic when processing a real corpus.

Take this sample of a transcript as an example:

```
1
00:00:03,400 --> 00:00:06,177
Let's talk about finance. One of
the most important aspects of

2
00:00:06,177 --> 00:00:10,009
finance is interest.
```

Our goal is to output the data modeled as follows:

```
Document :  [                                             ...
            1

Segment:    [                                ] [          ...
            1                                  2

Token:      [Let] [s] [talk] [about] [finance] [One] [of] ...
            1     2   3      4       5         6     7

character:  1    4   5      9       14        21    24   26               
```

Note that we have decided to ignore the numbered divisions marked `1` and `2` from the original transcript, as well as the timecodes (for now) and instead number units based on the criteria explained above. The sample above numbers the units under `[`: it displays one document, two segments and seven tokens. The bottom line numbers the characters in the sequence of tokens (i.e. ignoring the characters we chose to discard, namely the punctuation characters): the first token starts on the `1`st character and ends before the `4`th character (i.e. it is 3-character long), the second token starts on the `4`th character and ends before the `5`th character (i.e. it is 1-character long) and so on. Correspondingly, the first segment starts on the `1`st character and ends before the `21`st character, the second segments starts on the `21`st character and ends on the `67`th character (not shown here).

Each annotation layer has its own CSV file, with one row per unit and one column for each annotation or "attribute" on that unit (besides one ID column). Applied to the example above, this means that we want three CSV files, one for "document", one for "segment" and one for "token". Focusing on the illustrated sample only, the document CSV file would have a single row (besides the top header line) the segment CSV file would have 2 rows and the token CSV file would have 7 rows.

Let us focus on the document for now, without adding any annotations to it yet. The CSV file we want to generate is very simple:

```
document_id,char_range
1,"[1,68)"
```

LCP requires the document table to use integers as IDs in `document_id`. Note that a column named `char_range` reports the span of the document along the character axis: it uses the format `[x,y)` where `x` is the index of the first character covered by the annotation unit and `y` is the index `+ 1` of the last character (`)` meaning "exclusive").

Turning to the segments, again without adding any annotations to them, the CSV file we want to generate is similar:

```
segment_id,char_range
6fd88979-742c-4e75-8da3-b1d8c1ecd734,"[1,21)"
64b81434-2bd4-4ddd-a51f-4a17d089669a,"[1,68)"
```

LCP requires the segment table to use UUIDs as IDs in `segment_id`: they will be used to randomly partition the corpus in batches of logarithmically increasing sizes for faster preview of query results. Again, `char_range` reports the characters covered by each annotation unit.

Let us finally turn to the tokens. So far we have included no annotations in the document or in the segment table (except for `char_range`) but the tokens readily come with one essential attribute: their form (i.e. the specific characters they contain). That attribute is a string, and there two ways that LCP handles string attributes: when the number of all possible values for that attribute in the corpus is small (less than 100) it can be reported as is in the table and it is a **categorical** attribute; when the number is high (as is the case here) then one uses a lookup table to list the strings and reports the associated index in the table instead. This means that our token CSV file would look like this:

```
token_id,form_id,char_range,segment_id
1,1,"[1,4)",6fd88979-742c-4e75-8da3-b1d8c1ecd734
2,2,"[4,5)",6fd88979-742c-4e75-8da3-b1d8c1ecd734
3,3,"[5,9)",6fd88979-742c-4e75-8da3-b1d8c1ecd734
4,4,"[9,14)",6fd88979-742c-4e75-8da3-b1d8c1ecd734
5,5,"[14,21)",6fd88979-742c-4e75-8da3-b1d8c1ecd734
6,6,"[21,24)",64b81434-2bd4-4ddd-a51f-4a17d089669a
7,7,"[24,26)",64b81434-2bd4-4ddd-a51f-4a17d089669a
8,8,"[26,29)",64b81434-2bd4-4ddd-a51f-4a17d089669a
9,9,"[29,33)",64b81434-2bd4-4ddd-a51f-4a17d089669a
10,10,"[33,42)",64b81434-2bd4-4ddd-a51f-4a17d089669a
11,11,"[42,49)",64b81434-2bd4-4ddd-a51f-4a17d089669a
12,7,"[49,51)",64b81434-2bd4-4ddd-a51f-4a17d089669a
13,5,"[51,58)",64b81434-2bd4-4ddd-a51f-4a17d089669a
14,12,"[58,60)",64b81434-2bd4-4ddd-a51f-4a17d089669a
15,13,"[60,68)",64b81434-2bd4-4ddd-a51f-4a17d089669a
```

Note that the token table uses integer IDs, just like the document table (UUIDs are only used in segment for the purpose we discussed earlier). It also reports the `segment_id` to which the tokens belong, to optimize queries in LCP. Now, looking at the first 11 lines, it may look like reporting an index in `form_id` does not accomplish much becasuse the value is the same as `token_id`. However, the next two lines, which correspond to the second occurrences of `of` and `finance`, show that some tokens re-use indices, and this actually is true of most tokens in sufficiently large corpora.

The only table left that LCP needs now is a lookup table for `form`, which is a simple two-column table:

```
form_id,form
1,Let
2,s
3,talk
4,about
5,finance
6,One
7,of
8,the
9,most
10,important
11,aspects
12,is
13,interest
```

### Generating the tables

The script below will generate the table files from the transcript files. It contains detailed comments to guide the reader through its logic, but the general idea is the following: for each line from the transcript files (ignoring the two lines starting each transcript block, i.e. its number and its timestamps) we split the tokens on each whitespace/comma/apostrophe, and whenever we find a period/question mark/exclamation mark, we write the current tokens and segment to their files; in parallel, we keep a `char_range` counter incremented with the length of each token, and we maintain a dictionary of the encountered forms to write the corresponding lookup table at the end.

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
def to_char_range(lower, upper):
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
        # associate the unique values to IDs for lookup purposes (to be extended later)
        self.lookups = {
            "form": {},
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
        # read the text one character at a time (make sure it ends with a token delimiter)
        for token in split(self.token_delimiters, text):
            if not token:
                continue
            # retrieve and store the form's ID
            form_id = forms.get(token, len(forms) + 1)
            forms[token] = form_id
            # write the token's information to the output
            self.outputs["token"].writerow(
                [
                    self.token_id,
                    form_id,
                    to_char_range(self.char_range, self.char_range + len(token)),
                    seg_id,
                ]
            )
            # increment the char_range counter by the number of characters in the token
            self.char_range += len(token)
            self.token_id += 1
        # now that all the tokens have been processed, write the segment to the segment file
        self.outputs["segment"].writerow(
            [
                seg_id,
                to_char_range(char_range_seg_start, self.char_range),
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
                to_char_range(char_range_doc_start, self.char_range),
            ]
        )
        # increment the counter for the next document
        self.document_id += 1
        return

    # called at the end: write the lookup files
    def write_lookups(self):
        for form, form_id in self.lookups["form"].items():
            self.outputs["token_form"].writerow([form_id, form])
        return


# create the output folder if it doesn't exist yet
if not path.exists("output"):
    mkdir("output")

# we first create all the output files
with open(path.join("output", "document.csv"), "w") as doc_output, open(
    path.join("output", "segment.csv"), "w"
) as seg_output, open(path.join("output", "token.csv"), "w") as tok_output, open(
    path.join("output", "token_form.csv"), "w"
) as form_output:

    # initiate an instance of Converter with the output files
    converter = Converter(
        document=(doc_output, ["document_id", "char_range"]),
        segment=(seg_output, ["segment_id", "char_range"]),
        token=(
            tok_output,
            [
                "token_id",
                "form_id",
                "char_range",
                "segment_id",
            ],
        ),
        token_form=(form_output, ["form_id", "form"]),
    )

    # now process each document
    for document in documents:
        with open(document, "r") as doc_file:
            converter.process_document(doc_file)

    # finally, create the lookup files
    converter.write_lookups()
```

### Configuration file

Before we can upload our files, we need to create a configuration file to let LCP know how to handle the tables. The configuration file is a JSON file which reports some metadata information about the corpus (its name, its authors, etc.) the annotation layers present in the corpus and their attributes.

In our case, things are pretty simple, let's see what the configuration file needs to look like:

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

You do not need to worry about `firstClass` for now: it simply defines the names your corpus uses for the three basic annotation layers, in this case we use straightforward names.

Under `layer` should there be one key for each annotation layer. In this case, we work with a very basic corpus, so we only define the three basic annotation layers. Note that for the basic layers, the names need to match exactly the values defined in `firstClass` (i.e. the names start with an uppercase character, not a lowercase one). The names of the CSV files also need to match those names, although the filenames should use lowercase characters exclusively.

The `Document` and `Segment` layers are straightforward: they are spans of segments and token units, respectively, and have no attributes (their IDs are character ranges exist for database-related purposes only and, as such, are not considered attributes).

The `Token` layer is of type `"unit"` because it is parent to no further annotation layer. This layer must always define `anchoring`: it tells LCP whether the layer has a `char_range` column (i.e. `stream` is set to `true`) and whether it has other types of ranges for timestamps (`time` -- more about this later in this tutorial) and for XY coordinates (`location` -- not covered in this tutorial). Finally, `attributes` lists the attributes of the tokens, in this case only `form`. Note that the names reported in `attributes` need to match exactly the column names in the CSV files: token_form.csv indeed has a column named *exactly* `form` and another one named `form_id` while token.csv also has a column named `form_id`. Attribute names should always use under_score casing and can never include uppercase characters. Like we said earlier, the `form` attribute is of type `text` because the possible values are numerous, and when LCP sees an attribute of type `text` on an annotation layer in the configuration file, it requires a lookup file named `{layer}_{attribute}.CSV` in addition to `{layer}.CSV`. Finally, the `form` attribute is set to `nullable`=`false` because we do not accept tokens with an empty form.

### One last step

In its current state, LCP also requires the token layer of all corpora to define a `lemma` attribute of type `text` besides `form`, otherwise import will crash. Take a moment to think of how you would modify the python script to add that attribute (re-using the same values as for `form`) and how you would update the configuration file to report that attribute.

The necessary edits to the python script are minimal. In the `process_segment` method, one simply needs to duplicate the line `form_id,` in the call to `self.outputs["token"].writerow`. Then in the main body of the script, after opening a file named `token_form.csv`, one should also open a file named `token_lemma.csv` (`open(path.join("output", "token_lemma.csv"), "w") as lemma_output`), add `token_lemta=(lemma_output,["lemma_id", "lemma"])` in the  below `form_output.write("\n" + to_row([form_id, form]))` towards the end: `lemma_output.write("\n" + to_row([form_id, form]))`.

The necessary edits to the JSON configuration are also minimal, as only these lines need to be added under `form`:

```json
"lemma": {
    "type": "text",
    "nullable": false
}
```

### Import

Run the python script, save the JSON configuration in a file named meta.json alongside your CSV files in your output folder. Install the `lcpcli` tool:

`pip install lcpcli`

Now visit [catchphrase](https://catchphrase.linguistik.uzh.ch) and create a new corpus collection, then open its setting by clicking the gear icon, click the "API" tab and create a new API key; write down the key and the secret.

Open a terminal and run the following command, replacing `$API_KEY` with the key you just got, `$API_SECRET` with the secret you just got and `$PROJECT` with the name of the collection you just created:

`lcpcli -c path/to/output/ -k $API_KEY -s $API_SECRET -p "$PROJECT" --live`

You should get a confirmation message, and your corpus should now be visible in your collection after you refresh the page!


### Adding annotations

For the sake of illustration, we will add two pieces of annotation: on the segment annotation layer, we will report the original text of each segment (i.e. including the token delimiter characters) and on the token annotation layer, we will report whether it was preceded by a single quote (we will name the attribute `shortened`). The former will be of type `text`, just like the `form` and `lemma` attributes on the token layer, so we will create a lookup table file named `segment_original.CSV`. The latter will be of type `categorical` with two possible values: `yes` and `no`.

Updated script:

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
def to_char_range(lower, upper):
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
                        to_char_range(self.char_range, self.char_range + len(token)),
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
                to_char_range(char_range_seg_start, self.char_range),
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
                to_char_range(char_range_doc_start, self.char_range),
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

## Part 2: time alignment