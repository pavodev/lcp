# Part 1: Conceptual overview


<p>
  <img src="images/tuto_io.png" alt="Input to Output" width="1827"/>
</p>

The image above shows, on the left, the first lines of a transcript file (our input) and, one the right, what we want to obtain in _videoScope_ (our output). To do so, we need to go through 3 main steps:

 - **Segmentation**
 - **Tokenization**
 - **Time alignment**

<p>
  <img src="images/tuto_seg_tok_ali.png" alt="Segmentation, Tokenization, Time alignment" width="1450"/>
</p>

## Segmentation

In LCP, the source text needs to be _segmented_: segments will be the space within which end-users will look for sequences of words. Typically, **segments will correspond to sentences**.

SRT files often have one sentence per numbered block, as in the image above (one sentence in the two text lines of block 1, another sentence in the two text lines of block 2).

{% hint style="warning" %}
**Sentences and blocks don't always align**: some sentences will span multiple blocks in an SRT file, and some blocks will contain multiple sentences. This will be something to keep in mind when processing the data
{% endhint %}

## Tokenization

In addition, each segment is further divided into _tokens_. **Tokens typically correspond to words**, which roughly correspond to space-separated bits of text in the input.

{% hint style="warning" %}
**Using just space characters as token delimiters is too simplistic**: as visible in this example, written English has cases like `shouldn't`, which arguably corresponds to two tokens (`should` and `not`). For the sake of simplicity, we will also use `'` as a delimiter and accordingly map `shouldn't` to two tokens with the forms `shouldn` and `t`.
{% endhint %}

## Time alignment

Time alignment is the process of reporting **where the units previously defined (segments, tokens) fall along the time axis** in the corpus.

SRT files do not provide a good estimate for timecode for words, but we can use the blocks' timecodes to align the segments.

{% hint style="info" %}
LCP uses a convention of 25 frames per second for time-alignment purposes, which is the format in which we will report time alignment values.
{% endhint %}

{% hint style="warning" %}
**Rembember that sentences and blocks don't always align** so using the blocks' time codes is only an _approximation_ of when sentences start and end.
{% endhint %}

# Plan

In the next part, we will first apply segmentation and tokenization. These will produce a text-only corpus that we can upload to _catchphrase_.

In a second step, we will add annotations to the data:(1) we will report which tokens are preceded by `'` (we will flag them as `shortened`), and (2) we will associate each segment with its original text (including the delimiter characters) for display purposes.

In the last step, we will add time alignment and associate each document with a video file, so we can upload the corpus to _videoScope_.