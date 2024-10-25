# LiRI Corpus Platform (LCP)
[LCP](https://www.liri.uzh.ch/en/services/LiRI-Corpus-Platform-LCP.html) is a cloud-based software system for handling and querying corpora of different kinds. Data in LCP are accessible via three individual interfaces: Based on the modality of the corpus (text, audio, audiovisual/video) and the desired analysis, the user decides on which interface fits their needs best. LCP is being developed and maintained by a team at [LiRI](https://www.liri.uzh.ch/en.html), the Linguistic Research Infrastructure at UZH.

<p align="center"> <!-- Doesnt work, I wanted to center it, but it's not that important -->
  <img src="images/Doors_interface_Functionalities.png" alt="alt" width="550"/>
</p>

**1. [Catchphrase](catchphrase.md) is optimized for working with text corpora:** Use it when you are working with mono- or multilingual text corpora of any size. You can also use it when you need a faster search of your audiovisual collections by bypassing the retrieval of multimedia files.

**2. [Soundscript](soundscript.md) is optimized for working with audio corpora:** Use it for speech corpora that include audio recordings, transcriptions, and any other annotations on the textual or media stream. Results will output text and sound recordings. You can use it for video collections, to output results reduced to audio only.

**3. [Videoscope](videoscope.md) is optimized for working with audiovisual/video corpora:** Use it for viewing and querying audiovisual corpora based on video, that can include annotations on the media stream or text. The interface includes a video player and a timeline annotation preview. Querying results will output multimodal results and you can use them to navigate to the video recording.

Importantly, all interfaces are powered by LCP and use the same unified query language, which has specific functions for different datatypes. The advantage of the separation into separate access points is their customization optimized to specific corpus modalities. By the end of 2024, digital editions will also be implemented and added to LCP system. <!--This last sentence was written in the earlier version of README.md-->

Users can [query](querying.md) corpora directly from their browser and [import their own corpora](importing.md) using a command-line interface. Currently, the following corpora are publicly available in LCP:

- [British National Corpus (BNC)](http://www.natcorp.ox.ac.uk/) – text corpus
- [Text+Berg-Korpus - Alpine Journal](http://textberg.ch/site/de/willkommen/) – text corpus
- [corpus Oral de Français de Suisse Romande (OFROM)](https://ofrom.unine.ch/) - speech corpus

## First Steps
Upon accessing LCP via [lcp.linguistik.uzh.ch](https://lcp.linguistik.uzh.ch/)  you can browse the publicly available corpora.  This screenshot shows the current selection, but keep in mind the list will expand over time. 

((Put in current screenshot as soon as platform is ready))

The corpora are shaded according to their modality/modalities. E.g., green tells you that those are text corpora, and therefore can be queried in Catchphrase. Accordingly, the OFROM corpus is shaded in blue. Alternatively, hovering over the bottom right corner of a corpus lets you know which application is available. 

Navigating directly to any of the three interfaces at the top, e.g., on the blue “Soundscript” button, will filter the corpora accordingly. 

Clicking on one of the provided corpora reveals more details of the contained dataset, including the word count and information on the available metadata and parts of speech that can be queried for this corpus. Please note that the available metadata differs among the various datasets. See more information on the corpus structure on [Corpora in LCP](corpora_in_lcp.md). 


#### Login: edu-ID
While browsing the corpora can be done without it, any further action requires the user to log in. You will be prompted to do so when trying to access one of the corpora (clicking on one of the available interfaces as shown in the top left) or by navigating to the login option on the top right. You will be asked to login using your SWITCH edu-ID or institutional access. If you cannot find your institution in any of the provided options, please create e new switch-edu-login. You can do so [here](https://eduid.ch/registration). 

#### Querying corpora
LCP uses a dedicated query language called [DQD](dqd.md). To start out, LCP provides example queries for each corpus, with comments guiding the user through their first query. As you are getting to know the platform, you are invited to play around with the existing queries and see how the results change. To start a query, click “Submit”. 

<p align="center"> <!-- Doesnt work, I wanted to center it, but it's not that important -->
  <img src="images/example_query_in_corpus.png" alt="alt" width="650"/>
</p>

Once the results start showing up, several pieces of information are accessible by hovering over the various symbols and the individual tokens, such as form, lemma and part of speech as shown here.  of the results can be found [here](results.md). 

<p align="center"> <!-- Doesnt work, I wanted to center it, but it's not that important -->
  <img src="images/Hover_over_results.png" alt="alt" width="550"/>
</p>
Note that in this example, the query specified being interested in KWIC and NounDist; both are variables set by the user. To explore how to adapt your queries, see [Querying](querying.md). 

#### Beta Testing
LCP is currently in beta testing. The platform is free to use during this period as we gather input to improve it.
Feel free to report any feedback or bugs to ((add email address here)).
((Is this okay?))



#### Further Links
  * Further description of the [DQD query language](dqd.md)
  * Detailed tutorial on [Querying](querying.md)
  * [Data Model](model.md)
  * [How corpora are modelled in LCP](corpora_in_lcp.md)
  * How to store and share your corpora: [Corpus management](corpus_management.md)
  * How to [import your own corpora](importing.md)

