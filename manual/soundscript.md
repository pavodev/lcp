# *Soundscript*

The _Soundscript_ interface is optimized for querying, analyzing and visualizing audio data. If you work with, e.g., speech corpora or want to focus on the audio aspects of a multimodal corpus, _Soundscript_ is most efficient. 


## The landing page 
The landing page of _Soundscript_ is designed in the same way as the main LCP page, but only lists the corpora that contain audio data. In case of video corpora, sound and annotations will be included, but not the video. Text-only corpora are not shown here.

<p align="center"> <!-- Doesnt work, I wanted to center it, but it's not that important -->
  <img src="images/soundscript_landing.png" alt="alt" width="550"/>
</p>


## Data tab

In _Soundscript_ (and in Videoscope), the _Data_ tab is shown first, to allow for browsing though the media and annotations before querying.

### Media Player and timeline

The media player shows the audio recording for a chosen document. 

The timeline previews time-aligned transcripts and other annotations in layers. You can click and drag the timeline left and right to view annotations. You can hover annotation bars to see more information associated to that element.

<p align="center"> <!-- Doesnt work, I wanted to center it, but it's not that important -->
  <img src="images/soundscript_player.png" alt="alt" width="550"/>
</p>


## Query tab

The _Query_ tab is designed the same way across all interfaces. It contains the query entry field and the corpus template preview. Each corpus typically comes with a default query for illustration purposes. Move and magnify the corpus template for a better overview.

<p align="center"> <!-- Doesnt work, I wanted to center it, but it's not that important -->
  <img src="images/soundscript_query.png" alt="alt" width="550"/>
</p>

For more information on querying see the [Querying](querying.md) page and the [DQD](dqd.md) page.

## Results

Once the query has been submitted, results will automatically show in the _Data_ tab, below the player. Pressing the play &#9658; button will start playing back the media from the position in the document for the corresponding line.

<p align="center"> <!-- Doesnt work, I wanted to center it, but it's not that important -->
  <img src="images/soundscript_results.png" alt="alt" width="550"/>
</p>

### Analyses
In the analyses tabs, you can sort the results based on column values. Variables shown here depend on the definition in the DQD query.

<p align="center"> <!-- Doesnt work, I wanted to center it, but it's not that important -->
  <img src="images/catchphrase_analyses.png" alt="alt" width="550"/>
</p>

<div style="padding: 0.5em; margin: 1em 0em; background-color: rgb(237,245,253); color: black; border-radius: 0.2em;">
<span style="color: darkblue; font-weight: bold;">( ! ) </span>
<strong>Pro tip:</strong> if you sort by one column and then press another column header while holding the Shift button, you can sort based on two columns.
</div>

### Collocations

Here you can see the statistics regarding collocations for the chosen settings from the DQD query.

<p align="center"> <!-- Doesnt work, I wanted to center it, but it's not that important -->
  <img src="images/catchphrase_collocations.png" alt="alt" width="550"/>
</p>


