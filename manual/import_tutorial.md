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

Each annotation layer has its own TSV file, with one row per unit and one column for each annotation or "attribute" on that unit (besides one ID column). Applied to the example above, this means that we want three TSV files, one for "document", one for "segment" and one for "token". Focusing on the illustrated sample only, the document TSV file would have a single row (besides the top header line) the segment TSV file would have 2 rows and the token TSV file would have 7 rows.

Let us focus on the document for now, without adding any annotations to it yet. The TSV file we want to generate is very simple:

```
document_id	char_range
1	[1,68)
```

LCP requires the document table to use integers as IDs in `document_id`. Note that a column named `char_range` reports the span of the document along the character axis: it uses the format `[x,y)` where `x` is the index of the first character covered by the annotation unit and `y` is the index `+ 1` of the last character (`)` meaning "exclusive").

Turning to the segments, again without adding any annotations to them, the TSV file we want to generate is similar:

```
segment_id	char_range
daab3ddc-d2a3-4596-ae55-6f4303b23b4b	[1,21)
92b705da-e42e-4293-87b8-037ce6094b1e	[21,68)
```

LCP requires the segment table to use UUIDs as IDs in `segment_id`: they will be used to randomly partition the corpus in batches of logarithmically increasing sizes for faster preview of query results. Again, `char_range` reports the characters covered by each annotation unit.

Let us finally turn to the tokens. So far we have included no annotations in the document or in the segment table (except for `char_range`) but the tokens readily come with one essential attribute: their form (i.e. the specific characters they contain). That attribute is a string, and there two ways that LCP handles string attributes: when the number of all possible values for that attribute in the corpus is small (less than 100) it can be reported as is in the table and it is a **categorical** attribute; when the number is high (as is the case here) then one uses a lookup table to list the strings and reports the associated index in the table instead. This means that our token TSV file would look like this:

```
token_id	form_id	char_range	segment_id
1	1	[1,4)	daab3ddc-d2a3-4596-ae55-6f4303b23b4b
2	2	[4,5)	daab3ddc-d2a3-4596-ae55-6f4303b23b4b
3	3	[5,9)	daab3ddc-d2a3-4596-ae55-6f4303b23b4b
4	4	[9,14)	daab3ddc-d2a3-4596-ae55-6f4303b23b4b
5	5	[14,21)	daab3ddc-d2a3-4596-ae55-6f4303b23b4b
6	6	[21,24) 92b705da-e42e-4293-87b8-037ce6094b1e
7	7	[24,26) 92b705da-e42e-4293-87b8-037ce6094b1e
8	8	[26,29) 92b705da-e42e-4293-87b8-037ce6094b1e
9	9	[29,33) 92b705da-e42e-4293-87b8-037ce6094b1e
10	10	[33,42) 92b705da-e42e-4293-87b8-037ce6094b1e
11	11	[42,49) 92b705da-e42e-4293-87b8-037ce6094b1e
12	7	[49,51) 92b705da-e42e-4293-87b8-037ce6094b1e
13	5	[51,58) 92b705da-e42e-4293-87b8-037ce6094b1e
14	12	[58,60) 92b705da-e42e-4293-87b8-037ce6094b1e
15	13	[60,68) 92b705da-e42e-4293-87b8-037ce6094b1e
```

Note that the token table uses integer IDs, just like the document table (UUIDs are only used in segment for the purpose we discussed earlier). It also reports the `segment_id` to which the tokens belong, to optimize queries in LCP. Now, looking at the first 11 lines, it may look like reporting an index in `form_id` does not accomplish much becasuse the value is the same as `token_id`. However, the next two lines, which correspond to the second occurrences of `of` and `finance`, show that some tokens re-use indices, and this actually is true of most tokens in sufficiently large corpora.

The only table left that LCP needs now is a lookup table for `form`, which is a simple two-column table:

```
form_id	form
1	Let
2	s
3	talk
4	about
5	finance
6	One
7	of
8	the
9	most
10	important
11	aspects
12	is
13	interest
```

### Generating the tables

```python
from os import path

documents = ["transcript1.srt", "transcript2.srt"]
forms = {}
char_range = 1

with open(path.join("output", "document.tsv"), "w") as doc_output,
     open(path.join("output", "segment.tsv"), "w") as seg_output,
     open(path.join("output", "token.tsv"), "w") as tok_output,
     open(path.join("output", "token_form.tsv"), "w") as form_output:

    doc_output.write("\t".join(["document_id", "char_range"]))
    seg_output.write("\t".join(["segment_id", "char_range"]))
    tok_output.write("\t".join(["token_id", "form_id", "char_range", "segment_id"]))
    form_output.write("\t".join(["form_id", "form"]))

    for n_doc, document in enumerate(documents, start=1):
        with open(document, "r") as input:
            char_range_doc_start = char_range
            doc_output.write("\n" + "\t".join([str(n_doc_), f"[{char_range_doc_start},{char_range})"]))

```

## Part 2: time alignment