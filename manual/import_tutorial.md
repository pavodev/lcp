# Import Tutorial

In this tutorial, you will learn how to import video files with timed transcripts into LCP. In the first part, you will learn how to generate a text-only corpus from the transcript files. In the second part, you will learn how to also integrate the timecodes so you can upload the corpus of transcripts along with their videos to LCP.

## Files

Download the video files and their timed transcripts here: https:///.

## Part 1: text only

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
Document : [                                             ...
           1

Segment:   [                                ] [          ...
           1                                  2

Token:     [Let] [s] [talk] [about] [finance] [One] [of] ...
           1     2   3      4       5         6     7
```

Note that we have decided to ignore the numbered divisions marked `1` and `2` from the original transcript, as well as the timecodes (for now) and instead number units based on the criteria explained above.

Each annotation layer has its own TSV file, with one row per unit and one column for each annotation or "attribute" on that unit (besides one ID column). Applied to the example above, this means that we want three TSV files, one for "document", one for "segment" and one for "token". Focusing on the illustrated sample only, the token TSV file would have 7 rows (below the header), the segment TSV file would have 2 rows and the document TSV file would have a single row.

Let us focus on tokens for now, with one annotation reporting whether a token was preceded by a single-quote character in the original transcript as `0` vs `1` in a column named "shortened", which applies to token number 2 (`s`). Although the final TSV file will contain more columns, the table below is a first version of what we want to generate:

```
token_id	form	shortened
1	Let	0
2	s	1
3	talk	0
4	about	0
5	finance	0
6	One	0
7	of	0
```

## Part 2: time alignment