# LiRI Corpus Platform (LCP)
[LCP](https://www.liri.uzh.ch/en/services/LiRI-Corpus-Platform-LCP.html) is a cloud-based software system for handling and querying corpora of different kinds. Data in LCP are accessible via three individual interfaces: Based on the modality of the corpus (text, audio, audiovisual/video) and the desired analysis, the user decides on which interface fits their needs best. LCP is being developed and maintained by a team at [LiRI](https://www.liri.uzh.ch/en.html), the Linguistic Research Infrastructure at UZH. 

<p align="center"> <!-- Doesnt work, I wanted to center it, but it's not that important -->
  <img src="images/Doors_interface_Functionalities.png" alt="alt" width="600"/>
</p>

###### 1. Catchphrase is optimized for working with text corpora.
Use it when you are working with mono- or multilingual text corpora of any size. You can also use it when you need a faster search of your audiovisual collections by bypassing the retrieval of multimedia files.

###### 2. Soundscript is optimized for working with audio corpora.
Use it for speech corpora that include audio recordings, transcriptions, and any other annotations on the textual or media stream. Results will output text and sound recordings. You can use it for video collections, to output results reduced to audio only.

###### 3. Videoscope is optimized for working with audiovisual/video corpora.
Use it for viewing and querying audiovisual corpora based on video, that can include annotations on the media stream or text. The interface includes a video player and a timeline annotation preview. Querying results will output multimodal results and you can use them to navigate to the video recording.

Importantly, all interfaces are powered by LCP and use the same unified query language, which has specific functions for different datatypes. The advantage of the separation into separate access points is their customization optimized to specific corpus modalities. Read more on the query language [DQD](dqd.md) and how to [build queries here](querying.md). 






## Functionalities

  * allows definition of **complex queries**
  * users can import their **own corpora**
  * corpora is **automatically indexed** for faster search and retrieval
  * **modular system**: supports mono- or multilingual and mono- or multimodal data
  * comes with a dedicated **DQD** (Descriptive Query Definition) language

## Applications

LCP software system consists of several different applications, each allowing the querying and visualisation of different kind of corpora:

  * **[catchphrase](catchphrase.md)** - interface for querying textual corpora
  * **[soundscript](soundscript.md)** - interface for querying audio corpora
  * **[videoscope](videoscope.md)** - interface for querying multimodal corpora

By the end of 2024, digital editions will also be implemented and added to LCP system.


## Links

  * [DQD](dqd.md)
  * [Data Model](model.md)
  * [Corpora in LCP](corpora_in_lcp.md)
  * [Corpus management](corpus_management.md)
  * [Querying](querying.md)
  * [Importing](importing.md)
