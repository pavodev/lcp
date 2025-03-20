# Import Tutorial

In this tutorial, you will learn how to import video files with timed transcripts into LCP. In the first part, you will learn how to generate a text-only corpus from the transcript files using python. In the second part, you will learn how to also integrate the timecodes so you can upload the corpus of transcripts along with their videos to LCP.

## Files

Download the video files and their timed transcripts here: https:///.

## Part 1: text only

### Desired output

All text corpora in LCP structure define at least three levels, or *annotation layers*: *tokens*, which roughly correspond to individual words, *segments*, which roughly correspond to sentences, i.e. sequences of tokens, and *documents*, which in our case will each correspond to one transcript, i.e. the sequence of all the segments in a video. Corpus curators could decide to add intermediary annotation layers between segments and documents (e.g. paragraphs, which would be sequences of segments, so that documents would in turn contain sequences of paragraphs) but in this tutorial we will stick to the three basic levels.

Our approach will be as follows: each transcript file will correspond to a document, and each sequence of characters separated by a whitespace, a linebreak or single quote character will be modeled as a token; we will use periods, exclamation and question marks as delimiters for segments and ignore other punctuation signs. We intentionally keep things simple in this tutorial, although such an approach would be too simplistic when processing a real corpus.

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

What we need to achieve is re-model the data above as follows:

```
Document :  [                                             ...
            1

Segment:    [                                ] [          ...
            1                                  2

Token:      [Let] [s] [talk] [about] [finance] [One] [of] ...
            1     2   3      4       5         6     7

character:  1    4   5      9       14        21    24   26               
```

Note that we have decided to ignore the lines that mark the block numbers (`1` and `2`) from the original transcript, as well as the timecodes (for now). The model above numbers each unit on a dedicated line under the `[` characters: the first of these lines numbers one document, the second numbers two segments and the third numbers seven tokens. The bottom line numbers the *characters* in the sequence of tokens (ignoring the characters we chose to discard, namely the punctuation characters): the first token starts on the `1`st character and ends before the `4`th character (i.e. it is 3-character long), the second token starts on the `4`th character and ends before the `5`th character (i.e. it is 1-character long) and so on. Correspondingly, the first segment starts on the `1`st character and ends before the `21`st character, the second segments starts on the `21`st character and ends on the `67`th character (not shown here).

Each annotation layer needs its own CSV file, with one row per unit and one column per attribute on that unit. Applied to the example above, this means that we want three CSV files, one for "document", one for "segment" and one for "token". Focusing on the illustrated sample only, the CSV file for the document would have a single row (besides the top header line), the CSV file for the segments would have 2 rows and the CSV file for the tokens would have 7 rows.

Let us focus on the document for now. The CSV file we want to generate is very simple:

```
document_id,char_range
1,"[1,68)"
```

LCP requires the document table to use integers as IDs in `document_id`. Note that a column named `char_range` reports the span of the document along the character axis: it uses the format `[x,y)` where `x` is the index of the first character covered by the annotation unit and `y` is the index `+ 1` of the last character (`)` meaning "exclusive").

Turning to the segments, the CSV file we want to generate is again very simple:

```
segment_id,char_range
6fd88979-742c-4e75-8da3-b1d8c1ecd734,"[1,21)"
64b81434-2bd4-4ddd-a51f-4a17d089669a,"[1,68)"
```

LCP requires the segment table to use UUIDs as IDs in `segment_id`: they will be used to randomly partition the corpus in batches of logarithmically increasing sizes for faster preview of query results. Again, `char_range` reports the characters covered by each annotation unit.

Let us finally turn to the tokens. So far we have included no annotations in the document or in the segment table (except for the IDs and `char_range`, which will not be exposed to the end users) but the tokens readily come with one essential attribute: their form (i.e. the specific characters they contain). That attribute is a string, and there are two ways that LCP handles string attributes: when the number of all possible values for a string attribute in the corpus is small (say, less than 100) and the each possbile value is under 50 characters long, it can be directly reported as is in the column of the CSV file, and it is then a **categorical** attribute; when the number is high (as will be the case with the full corpus here) and/or some values exceed 50 characters, then one uses a lookup table (a separate CSV file) to list the strings, and reports the associated index in the annotation unit's CSV file instead. This means that our CSV file for the tokens would look like this:

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

Let us start with a simple but imperfect approach, to illustrate our general approach. We will create 4 CSV files (document.csv, segment.csv, token.csv, token_form.csv) and read an SRT file line by line. We will split each line using the segment-delimiters we listed earlier, and we will split each resulting segment-chunk using the token-delimiters we listed earlier. Each piece is a token whose form we store along with its index (= the number of unique forms encountered so far); we write to token.csv the token's ID (incremented by 1 each time), the form's index, the `char_range` info (current counter + form's length) and the current segment's UUID. Before moving to the next token, we update the `char_range` and `token_id` counters. After processing all the current segment's tokens, we write to segment.csv the segment's UUID plus the `char_range` info (= counter value before processing the tokens + all the tokens' forms' lengths). Finally we write to document.csv its ID (`1` because this script only processes one file) and the `char_range` info (1 + value of the counter after processing all the segments).

The script below, here for training purposes only and not to be used on real data (see below for a cleaner approach), accomplishes that:

```python
import csv
from os import path, mkdir
from re import split
from uuid import uuid4

if not path.exists("output"):
    mkdir("output")  # create directory if necessary

# Create the output files and open the input file
with open(
    path.join("output", "document.csv"), "w"
) as doc_output, open(path.join("output", "segment.csv"), "w") as seg_output, open(
    path.join("output", "token.csv"), "w"
) as tok_output, open(
    path.join("output", "token_form.csv"), "w"
) as form_output, open("transcript1.srt", "r") as input:

    # Write the headers in a CSV format
    doc_csv = csv.writer(doc_output)
    doc_csv.writerow(["document_id", "char_range"])
    seg_csv = csv.writer(seg_output)
    seg_csv.writerow(["segment_id", "char_range"])
    tok_csv = csv.writer(tok_output)
    tok_csv.writerow(["token_id", "form_id", "char_range", "segment_id"])
    form_csv = csv.writer(form_output)
    form_csv.writerow(["form_id", "form"])

    char_range = 1  # will be incremented with each character in a token
    token_id = 1  # will be incremented with each new token
    all_forms = {}  # stores the encountered forms along with their index
    while line := input.readline():
        line = line.strip()
        for segment in split(r"[.?!]", line): # split by period/question/exclamation mark
            if not segment.strip():
                continue
            char_range_start_seg = char_range  # lower bound of the segment's char_range
            seg_id = uuid4()  # segments use UUIDs as their ID
            for token in split(r"[', ]", segment): # split by single-quote/comma/space
                form = token.strip()
                if not form:
                    continue
                # retrieve/store the form's index
                form_id = all_forms.get(form, len(all_forms) + 1)
                all_forms[form] = form_id
                tok_csv.writerow(
                    [
                        token_id,
                        form_id,
                        f"[{char_range},{char_range+len(form)})",
                        seg_id,
                    ]
                )
                char_range += len(form)  # increment char_range by the form's length
                token_id += 1  # increment by 1 for each processed token
            seg_csv.writerow([seg_id, f"[{char_range_start_seg},{char_range})"])
    # now write the lookup table
    for form, form_id in all_forms.items():
        form_csv.writerow([form_id, form])
    doc_csv.writerow(["1", f"[1,{char_range})"])
```

The output files are well-formatted files, but they do not exactly reflect the model we laid down above. This is because (1) we parsed the lines reporting the blocks numbers (`1` and `2`) as well as the lines reporting the timestamps; (2) we treated each new line as a new segment, even though there exists text separated by two periods that spans multiple lines, and that text should still constitute a single segment.

The updated and streamlined script below will generate the desired output. It refactors the core of the logic above inside a custom `Converter` class, it properly handles non-transcript lines, and it is able to process an arbitrary number of input files. Extensive comments are included to guide the reader through the logic of the code.

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


# custom class that will process each input file and write the output files
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
                    to_range(self.char_range, self.char_range + len(token)),
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
                to_range(char_range_seg_start, self.char_range),
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

The output files look good now, as can be seen by comparing them with the tables we illustrated above.

### Configuration file

Before we can upload our files, we need to create a configuration file to let LCP know how to handle the tables. The configuration file is a JSON file which reports some metadata information about the corpus (its name, its authors, etc.) the annotation layers present in the corpus and their attributes.

In our case, things are pretty simple, let's see what the configuration file needs to look like:

```json
{
    "meta": {
        "name": "Test Corpus",
        "author": "LCP tutorial",
        "date": "2025-03-18",
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

The first key, `firstClass`, simply defines the names your corpus uses for the three basic annotation layers, and in this case we use straightforward names.

Under `layer` should be reported one key for each annotation layer in the corpus. In this case, we work with a very basic corpus, so we only define the three basic annotation layers. Note that for the basic layers, the names need to match exactly the values defined in `firstClass` (i.e. the names start with an uppercase character, not a lowercase one). The names of the CSV files also need to match those names, although the filenames should use lowercase characters exclusively; this is also true of the column names (`document_id`, `segment_id`, `token_id`). For example, had we reported `"segment": "Sentence"` in `firstClass`, we would have used `"Sentence"` as key instead of `"Segment"` in `layer`, `sentence.csv` instead of `segment.csv` as a filename and the column's name would have been `sentence_id`.

The `Document` and `Segment` layers are straightforward: they are spans of segments and token units, respectively, and have no attributes exposed to the user (their IDs and character ranges exist for database-related purposes only and, as such, are not considered attributes here).

The `Token` layer is of type `"unit"` because it is parent to no further annotation layer. This layer must always define `anchoring`: it tells LCP whether the layer has a `char_range` column (i.e. `stream` is set to `true`) and whether it has other types of ranges, for timestamps (`time` -- more about this later in this tutorial) or for XY coordinates (`location` -- not covered in this tutorial). Finally, `attributes` lists the attributes of the tokens, in this case only `form`. Note that the names reported in `attributes` need to match exactly the column names in the CSV files: token_form.csv, in addition to being named after the exact lowercase versions of the layer's name and the attribute's name, has a column named *exactly* `form` and another one named `form_id`, while token.csv also has a column named `form_id`. Attribute names should always use under_score casing and can never include uppercase characters. Like we said earlier, the `form` attribute is of type `text` because the possible values are numerous, and when LCP sees an attribute of type `text` on an annotation layer in the configuration file, it requires a lookup file named `{layer}_{attribute}.csv` in addition to `{layer}.csv`. Finally, the `form` attribute is set to `nullable`=`false` because we do not accept tokens with an empty form.

### One last step

In its current state, LCP also requires the token layer of all corpora to define a `lemma` attribute of type `text` besides `form`, otherwise import will crash. Take a moment to think of how you would modify the python script to add that attribute (re-using the same values as for `form`) and how you would update the configuration file to report that attribute.

---

The necessary edits to the python script are minimal:

 1. in the `process_segment` method, duplicate the line `form_id,` (we are using the same values for lemma as for form)
 2. in `write_lookups`, add `self.outputs["token_lemma"].writerow([form_id, form])` immediately below the line writing to `token_form` (again, same value for lemma as for form)
 3. in the `with` statement, after opening a file named `token_form.csv`, also open a file named `token_lemma.csv` (`open(path.join("output", "token_lemma.csv"), "w") as lemma_output`)
 4. as part of the `token` value when initiating the converter, add a line `"lemma_id",` under the line `"form_id",` to correspond with the duplication of `form_id` in step 1
 5. finally, add a `token_lemma` attribute to the converter to initiate the corresponding CSV writer: `token_lemma=(lemma_output, ["lemma_id", "lemma"]),`

The necessary edits to the JSON configuration are also minimal, as only these 4 lines need to be added under `form` in the token attributes:

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

For the sake of illustration, we will now add two pieces of annotation: on the segment annotation layer, we will report the original text of each segment (i.e. including the token delimiter characters) and on the token annotation layer, we will report whether it was preceded by a single quote (we will name the attribute `shortened`). The former will be of type `text`, just like the `form` and `lemma` attributes on the token layer, so we will create a lookup table file named `segment_original.csv`. The latter will be of type `categorical` with two possible values (`yes` and `no`) which will be reported directly in `token.csv`.

The updated script is reported below. In addition to creating new files and new columns, we also revised our tokenization approach: instead of using the `split` method, we now parse the text one character at a time. This is because we want to detect whether a single quote precedes a token, so we can appropriately report `yes` or `no` in the `shortened` column of `token.csv`.

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

## Part 2: time alignment and video



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
        self.frame_offset = 0  # offset for the timestamps of the next document
        self.last_timestamps = (0, 0)  # last processed timestamp
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

    # helper method to convert hh:mm:ss,sss into a number (25fps)
    def timestamp_to_range(self, timestamp: str) -> int:
        hour, minute, second = timestamp.split(":")
        seconds = (
            float(second.replace(",", "."))
            + float(minute) * 60.0
            + float(hour) * 3600.0
        )
        return self.frame_offset + int(seconds * 25.0)

    # helper method that writes to the segment and token files
    def process_segment(self, text, frame_range_seg_start):
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
        frame_range_seg_start = (
            frame_range_seg_start
            if self.last_timestamps[1] > frame_range_seg_start
            else frame_range_seg_start + 1
        )
        # now that all the tokens have been processed, write the segment to the segment file
        self.outputs["segment"].writerow(
            [
                seg_id,
                to_range(char_range_seg_start, self.char_range),
                to_range(frame_range_seg_start, self.last_timestamps[1]),
                original_id,
            ]
        )
        return

    # This will be called on each input file
    def process_document(self, file):
        char_range_doc_start = self.char_range  # lower bound of doc's char_range
        frame_range_doc_start = self.frame_offset  # lower bound of doc's frame_range
        current_segment = ""  # buffer storing the curent sentence's text
        frame_range_seg_start = self.frame_offset
        new_block = True  # are we starting a new block from the transcription file?
        while line := file.readline():
            if new_block:
                # in SRT files, at the start of a new block, the first two lines
                # are the block number and the timestamps: we skip both of those
                timestamp_string = file.readline().strip()
                self.last_timestamps = tuple(
                    [
                        self.timestamp_to_range(x)
                        for x in timestamp_string.split(" --> ")
                    ]
                )
                if not current_segment:
                    frame_range_seg_start = self.last_timestamps[0]
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
                self.process_segment(current_segment, frame_range_seg_start)
                # now process any remaining content
                current_segment = ""
                for middle_segment in remainder[1:-1]:
                    # the line could have full segments in the middle, as in "ipsum. lorem ipsum. lorem"
                    # if it does, call process_segment on each of those middle chunks
                    self.process_segment(middle_segment, frame_range_seg_start)
                # start a new current_segment with the last tokens in the line
                current_segment = remainder[-1]
                if search(self.segment_delimiters + "$", line):
                    # but if the line actually *ends* with a segment delimiter,
                    # call process_segment on the last tokens and start afresh
                    self.process_segment(current_segment, frame_range_seg_start)
                    current_segment = ""
        self.frame_offset = self.last_timestamps[1]
        filename_no_ext = file.name.replace(".srt", "")
        # we are done with the current document: write it to the document file
        self.outputs["document"].writerow(
            [
                self.document_id,
                to_range(char_range_doc_start, self.char_range),
                to_range(frame_range_doc_start, self.frame_offset),
                filename_no_ext,
                '{"video": "' + filename_no_ext + '.mp4"}',
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
        document=(
            doc_output,
            ["document_id", "char_range", "frame_range", "name", "media"],
        ),
        segment=(
            seg_output,
            ["segment_id", "char_range", "frame_range", "original_id"],
        ),
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

```json
{
    "meta": {
        "name": "Test Corpus",
        "author": "LCP tutorial",
        "date": "2025-03-13",
        "version": 1,
        "corpusDescription": "Test corpus from the tutorial",
        "mediaSlots": {
            "video": {
                "mediaType": "video",
                "obligatory": true
            }
        }
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
            "anchoring": {
                "stream": true,
                "time": true,
                "location": false
            },
            "attributes": {}
        },
        "Segment": {
            "layerType": "span",
            "contains": "Token",
            "anchoring": {
                "stream": true,
                "time": true,
                "location": false
            },
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