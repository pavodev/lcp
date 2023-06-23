<template>
  <div class="player mb-5">
    <div class="container mt-4">
      <div class="row">
        <div class="col-5">
          <label class="form-label">Corpus</label>
          <!-- <multiselect
            v-model="selectedCorpora"
            :options="corporaList"
            :multiple="false"
            label="name"
            track-by="value"
          ></multiselect> -->
          <select v-model="selectedCorpora" class="form-select">
            <option
              v-for="corpora in corpusList"
              :value="corpora"
              v-html="corpora.name"
              :key="corpora.value"
            ></option>
          </select>
        </div>
        <!--<div class="col-5">
          <label class="form-label">Document</label>
          <!- - <span v-if="loading">Loading ...</span> - ->
          <select v-model="currentDocument" class="form-select">
            <option
              v-for="document in corpusData.filter(corpus => Object.values(documentDict).includes(corpus[1]))"
              :value="document"
              v-html="document[1]"
              :key="document[0]"
            ></option>
          </select>
        </div>-->
      </div>
      <div class="row mt-4" v-if="selectedCorpora">
        <div class="col">
          <nav>
            <div class="nav nav-tabs" id="nav-tab" role="tablist">
              <button
                v-for="document in corpusData.filter(corpus => Object.values(documentDict).includes(corpus[1]))"
                :key="document[0]"
                class="nav-link"
                :class="currentDocument && currentDocument[2] == document[2] ? 'active' : ''"
                :id="`nav-${document[0]}-tab`"
                data-bs-toggle="tab"
                :data-bs-target="`#nav-${document[0]}`"
                type="button"
                role="tab"
                @click="setDocument(document)"
                :aria-controls="`nav-${document[0]}`"
                aria-selected="true"
              >
                {{ document[1] }}
              </button>
            </div>
          </nav>
          <!-- <div class="tab-content pt-3" id="nav-tabContent">
            <div
              v-for="(document, index) in corpusData.filter(corpus => Object.values(documentDict).includes(corpus[1]))"
              :key="document[0]"
              class="tab-pane fade"
              :class="index == -1 ? 'active show' : ''"
              :id="`nav-${document[0]}`"
              role="tabpanel"
              aria-labelledby="nav-results-tab"
            >
            </div>
          </div> -->
        </div>
      </div>
    </div>

    <!-- <div id="eventdrops-demo" style="width: 90%" class="mt-4"></div> -->

    <div v-if="currentDocument">
      <div class="container mt-4 mb-4">
        <div class="video-box">
          <div class="video-text-test" v-html="subtext"></div>
          <div :class="mainVideo == 1 ? 'active' : ''">
            <video ref="videoPlayer1" @timeupdate="timeupdate">
              <source
                :src="baseVideoUrl + currentDocument[2][0]"
                type="video/mp4"
              />
            </video>
          </div>
          <div
            :class="mainVideo == 2 ? 'active' : ''"
            v-if="currentDocument[2].length > 1"
          >
            <video ref="videoPlayer2">
              <source
                :src="baseVideoUrl + currentDocument[2][1]"
                type="video/mp4"
              />
            </video>
          </div>
          <div
            :class="mainVideo == 3 ? 'active' : ''"
            v-if="currentDocument[2].length > 2"
          >
            <video ref="videoPlayer3">
              <source
                :src="baseVideoUrl + currentDocument[2][2]"
                type="video/mp4"
              />
            </video>
          </div>
          <div
            :class="mainVideo == 4 ? 'active' : ''"
            v-if="currentDocument[2].length > 3"
          >
            <video ref="videoPlayer4">
              <source
                :src="baseVideoUrl + currentDocument[2][3]"
                type="video/mp4"
              />
            </video>
          </div>
        </div>
      </div>

      <div class="container mt-4 mb-4">
        <div class="btn-group" role="group">
          <button
            type="button"
            class="btn btn-sm btn-primary"
            @click="playerFromStart"
          >
            <FontAwesomeIcon :icon="['fas', 'backward-step']" />
          </button>
          <button type="button" class="btn btn-sm btn-primary">
            <FontAwesomeIcon :icon="['fas', 'backward']" />
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary active"
            @click="playerStop"
            v-if="playing"
          >
            <FontAwesomeIcon :icon="['fas', 'pause']" />
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary"
            @click="playerPlay"
            v-else
          >
            <FontAwesomeIcon :icon="['fas', 'play']" />
          </button>
          <button type="button" class="btn btn-sm btn-primary">
            <FontAwesomeIcon :icon="['fas', 'forward']" />
          </button>
        </div>
        <div class="btn-group ms-1" role="group">
          <!-- <button
            type="button"
            class="btn btn-sm btn-primary"
            @click="playerVolumeDown"
          >
            <FontAwesomeIcon :icon="['fas', 'volume-down']" />
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary"
            @click="playerVolumeUp"
          >
            <FontAwesomeIcon :icon="['fas', 'volume-up']" />
          </button> -->
          <button
            type="button"
            class="btn btn-sm btn-primary"
            @click="playerVolumeMute"
          >
            <div style="width: 11px; text-align: left">
              <FontAwesomeIcon v-if="volume == 0" :icon="['fas', 'volume-xmark']" />
              <FontAwesomeIcon v-else-if="volume > 0.9" :icon="['fas', 'volume-high']" />
              <FontAwesomeIcon v-else :icon="['fas', 'volume-low']" />
            </div>
          </button>

          <span class="btn btn-sm btn-primary pt-0 pb-0">
            <input
              type="range"
              class="form-range"
              v-model="volume"
              min="0"
              max="1"
              step="0.05"
              style="height: 2px"
            />
          </span>
          <span class="btn btn-sm btn-primary" style="width: 37px">
            <small>{{ parseInt(volume*100, 10) }}</small>
          </span>
          <!-- <input
            type="range"
            class="form-range mt-1 ms-1"
            v-model="volume"
            min="0"
            max="1"
            step="0.001"
          />
          -->
        </div>
        <div class="btn-group ms-1" role="group">
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            @click="playerFrameDown(5)"
          >
            -5
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            @click="playerFrameDown(1)"
          >
            -1
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            @click="playerFrameUp(1)"
          >
            +1
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            @click="playerFrameUp(5)"
          >
            +5
          </button>
          <!-- <button type="button" class="btn btn-sm btn-primary" @click="playerFrame100"><div class="icon-number">F100</div></button>
          <button type="button" class="btn btn-sm btn-primary" @click="playerSetTime"><div class="icon-number">Set time 10</div></button> -->
        </div>
        <div class="btn-group ms-1" role="group">
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            :class="playerSpeed == 0.5 ? 'active' : ''"
            @click="playerSetSpeed(0.5)"
          >
            0.5x
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            :class="playerSpeed == 1 ? 'active' : ''"
            @click="playerSetSpeed(1)"
          >
            1x
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            :class="playerSpeed == 1.5 ? 'active' : ''"
            @click="playerSetSpeed(1.5)"
          >
            1.5x
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            :class="playerSpeed == 2 ? 'active' : ''"
            @click="playerSetSpeed(2)"
          >
            2x
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            :class="playerSpeed == 3 ? 'active' : ''"
            @click="playerSetSpeed(3)"
          >
            3x
          </button>
        </div>
        <div class="btn-group ms-1" role="group">
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            :class="mainVideo == 1 ? 'active' : ''"
            @click="playerMainVideo(1)"
          >
            V1
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            v-if="currentDocument[2].length > 1"
            :class="mainVideo == 2 ? 'active' : ''"
            @click="playerMainVideo(2)"
          >
            V2
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            v-if="currentDocument[2].length > 2"
            :class="mainVideo == 3 ? 'active' : ''"
            @click="playerMainVideo(3)"
          >
            V3
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            v-if="currentDocument[2].length > 3"
            :class="mainVideo == 4 ? 'active' : ''"
            @click="playerMainVideo(4)"
          >
            V4
          </button>
        </div>
        <div class="btn-group ms-1" role="group">
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            :class="mainAudio == 1 ? 'active' : ''"
            @click="playerMainAudio(1)"
          >
            A1
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            v-if="currentDocument[2].length > 1"
            :class="mainAudio == 2 ? 'active' : ''"
            @click="playerMainAudio(2)"
          >
            A2
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            v-if="currentDocument[2].length > 2"
            :class="mainAudio == 3 ? 'active' : ''"
            @click="playerMainAudio(3)"
          >
            A3
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary btn-text-icon"
            v-if="currentDocument[2].length > 3"
            :class="mainAudio == 4 ? 'active' : ''"
            @click="playerMainAudio(4)"
          >
            A4
          </button>
        </div>
      </div>
      <div class="container mt-4">
        <div class="row">
          <div class="col" @click="timelineClick">
            <div
              class="progress"
              style="height: 10px; widdth: 100%"
              ref="timeline"
            >
              <div
                class="progress-bar bg-danger"
                role="progressbar"
                :style="'width: ' + progress + '%'"
                aria-valuenow="25"
                aria-valuemin="0"
                aria-valuemax="100"
              ></div>
            </div>
          </div>
        </div>
        <div class="row mb-3 mt-2">
          <div class="col">
            <!-- Percentage: <span v-html="progress.toFixed(2)" />% -->
            Frame:
            <span
              v-html="parseInt(currentFrame, 10)"
            />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Time: <span v-html="currentTime" />
          </div>
        </div>
      </div>

      <div id="eventdrops-demo" style="width: 90%" class="mt-4"></div>

      <hr />

      <div class="container mt-4">
        <div class="row">
          <div class="col-6">
            <div class="form-floating mb-3">
              <nav>
                <div class="nav nav-tabs" id="nav-tab" role="tablist">
                  <button
                    class="nav-link active"
                    id="nav-dqd-tab"
                    data-bs-toggle="tab"
                    data-bs-target="#nav-dqd"
                    type="button"
                    role="tab"
                    aria-controls="nav-dqd"
                    aria-selected="true"
                    @click="currentTab = 'dqd'"
                  >
                    DQD
                  </button>
                  <button
                    class="nav-link"
                    id="nav-json-tab"
                    data-bs-toggle="tab"
                    data-bs-target="#nav-json"
                    type="button"
                    role="tab"
                    aria-controls="nav-json"
                    aria-selected="false"
                    @click="currentTab = 'json'"
                  >
                    JSON
                  </button>
                </div>
              </nav>
              <div class="tab-content" id="nav-tabContent">
                <div
                  class="tab-pane fade show active pt-3"
                  id="nav-dqd"
                  role="tabpanel"
                  aria-labelledby="nav-results-tab"
                >
                  <EditorView
                    :query="queryDQD"
                    :corpora="selectedCorpora"
                    @update="updateQueryDQD"
                    :key="editorIndex"
                  />
                  <p
                    class="error-text text-danger mt-3"
                    v-if="isQueryValidData && isQueryValidData.valid != true"
                  >
                    {{ isQueryValidData.error }}
                  </p>
                </div>
                <div
                  class="tab-pane fade pt-3"
                  id="nav-json"
                  role="tabpanel"
                  aria-labelledby="nav-stats-tab"
                >
                  <textarea
                    class="form-control query-field"
                    placeholder="Query (e.g. test.*)"
                    :class="
                      isQueryValidData == null || isQueryValidData.valid == true
                        ? 'ok'
                        : 'error'
                    "
                    v-model="query"
                  ></textarea>
                  <!-- <label for="floatingTextarea">Query</label> -->
                  <p
                    class="error-text text-danger"
                    v-if="isQueryValidData && isQueryValidData.valid != true"
                  >
                    {{ isQueryValidData.error }}
                  </p>
                </div>
              </div>
            </div>
            <div class="form-floating mb-3">
              <!-- <textarea
                class="form-control query-field"
                style="height: 200px"
                placeholder="Query (e.g. test.*)"
                v-model="query"
              ></textarea>
              <label for="floatingTextarea">Query</label> -->
            </div>
            <button
              type="button"
              @click="submitQuery"
              class="btn btn-primary me-1"
              :disabled="
                (selectedCorpora && selectedCorpora.length == 0) ||
                loading ||
                (isQueryValidData != null && isQueryValidData.valid == false) ||
                !query
              "
            >
              <FontAwesomeIcon :icon="['fas', 'magnifying-glass-chart']" />
              Submit
            </button>
            <button
              v-if="loading"
              type="button"
              @click="stop"
              :disabled="loading == false"
              class="btn btn-primary"
            >
              Stop
            </button>
            <br />
            <br />
            Load example query:
            <button
              type="button"
              @click="setExample(1)"
              class="btn btn-sm btn-secondary ms-1"
            >
              1
            </button>
            <button type="button" @click="setExample(2)" class="btn btn-sm btn-secondary ms-1">2</button>
            <button
              type="button"
              @click="setExample(3)"
              class="btn btn-sm btn-secondary ms-1"
            >
              3
            </button>
            <!-- <button
              type="button"
              @click="setExample(4)"
              class="btn btn-sm btn-secondary ms-1"
            >
              4
            </button> -->
          </div>
          <div class="col-6" v-if="WSDataResults">
            <!-- Total progress
            <div class="progress mb-2">
              <div
                class="progress-bar"
                :class="
                  loading ? 'progress-bar-striped progress-bar-animated' : ''
                "
                role="progressbar"
                aria-label="Basic example"
                :style="`width: ${percentageTotalDone}%`"
                :aria-valuenow="percentageTotalDone"
                aria-valuemin="0"
                aria-valuemax="100"
              >
                {{ percentageTotalDone.toFixed(2) }}%
              </div>
            </div> -->
            <span v-if="WSDataResults">
              <ul class="list-no-bullets">
                <li
                  v-for="(result, index) in currentPageResults"
                  :key="index"
                  class="cursor-pointer hover-opacity"
                  @click="resultClick(result)"
                >
                  <div class="row">
                    <div class="col-2">
                      <span
                        class="badge bg-secondary"
                        v-html="frameNumberToTime(result[5][0][0])"
                      ></span>
                    </div>
                    <div class="col">
                      <span class="text-bold" v-html="WSDataResults.result[-1][result[0]][1].map(x => x[0]).join(' ')" />
                      <span v-if="result[3]">
                        <br>Gesture: <b><span v-html="result[3]"></span></b>
                      </span>
                    </div>
                    <div class="col-1">
                      <span v-html="documentDict[result[2]]"></span>
                      <br>
                      <span v-html="result[4]"></span>
                    </div>
                  </div>
                </li>
              </ul>
              <PaginationComponent
                :resultCount="WSDataResults.result[1].length"
                :resultsPerPage="resultsPerPage"
                :currentPage="currentPage"
                @update="updatePage"
                :key="WSDataResults.result[1].length"
                :loading="loading"
              />
            </span>
            <!-- <span v-else-if="queryData == 1"></span> -->
            <span v-else>Loading ...</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Utils from "@/utils.js";
import * as d3 from "d3/build/d3";
import eventDrops from "../../../vian-eventdrops/src/";

import { mapState } from "pinia";

import { useCorpusStore } from "@/stores/corpusStore";
import { useNotificationStore } from "@/stores/notificationStore";
import { useUserStore } from "@/stores/userStore";
import { useWsStore } from "@/stores/wsStore";

import config from "@/config";
import EditorView from "@/components/EditorView.vue";
import PaginationComponent from "@/components/PaginationComponent.vue";

// import exampleData from '@/assets/example_data.json';

export default {
  data() {
    return {
      preselectedCorporaId: this.$route.params.id,
      selectedCorpora: null,
      currentDocument: null,
      currentDocumentData: null,
      isQueryValidData: null,
      loading: false,
      failedStatus: false,
      WSDataResults: null,

      resultsPerPage: 20,
      currentPage: 1,

      percentageTotalDone: 0,
      progress: 0,
      chart: null,
      editorIndex: 0,
      currentFrame: 0,
      currentTime: "",
      subtitles: {},
      subtext: "",
      playing: false,
      playerSpeed: 1,
      mainVideo: 1,
      mainAudio: 1,
      baseVideoUrl: `${config.baseVideoUrl}/e822e422-32e1-4635-a0c9-0366970affeb/`,
      volume: 0.5,
      frameRate: 25.0,

      setResultTime: null,
      query: "",
      queryDQD: `Segment s

sequence@s
	Token t1
		upos = DET
	Token t2
		upos = NOUN

Gesture g
	agent = s.agent
	type = PG
	start >= s.start - 3s
	end <= s.end + 3s

KWIC => plain
	context
		s
	entities
		t1
		t2
		g
`,
      corpusData: [
        [2, "AKAW1", ["AKAW1_K1.mp4", "AKAW1_K2.mp4"], [1,57800]],
        [3, "AKAW2", ["AKAW2_K1.mp4"], [57799,103525]],
        [4, "AWAV1", ["AWAV1_K1.mp4"], [103524,142044]],
        [5, "CALK1", ["CALK1_K1.mp4", "CALK1_K2.mp4"], [142043,180563]],
        [6, "CHAB2", ["CHAB2_K1.mp4", "CHAB2_K2.mp4"], [180562,235692]],
        [7, "DAAF1", ["DAAF1_K1.mp4", "DAAF1_K2.mp4"], [0, 0]],
      ],
      documentDict: {},
    };
  },
  components: {
    EditorView,
    PaginationComponent,
  },
  computed: {
    ...mapState(useCorpusStore, ["queryData", "corpora"]),
    ...mapState(useUserStore, ["userData", "roomId"]),
    ...mapState(useWsStore, ["messages"]),
    corpusList() {
      return this.corpora
        ? this.corpora.map((corpus) => {
            return {
              name: corpus.meta.name,
              value: corpus.meta.id,
              corpus: corpus,
            };
          })
        : [];
    },
    currentPageResults() {
      let start = this.resultsPerPage * (this.currentPage - 1);
      let end = start + this.resultsPerPage;
      return this.WSDataResults.result[1]
        .filter((row, rowIndex) => {
          return rowIndex >= start && rowIndex < end;
        })
    },
  },
  methods: {
    setDocument(document) {
      this.currentDocument = document
    },
    frameNumberToTime(frameNumber) {
      let seconds = Utils.frameNumberToSeconds(frameNumber);
      return Utils.msToTime(seconds);
    },
    updatePage(currentPage) {
      this.currentPage = currentPage;
    },
    resultClick(result) {
      // console.log(result, result[4][0][1], this.currentDocument)
      let value = Utils.frameNumberToSeconds(result[4][0][1]) / 1000;
      if (this.currentDocument[0] == result[2]) {
        this._playerSetTime(value);
      } else {
        //   // this.currentDocument = this.corpusData[result[2] - 1];
        // this.currentDocument = this.documentDict[result[2]];
        this.setResultTime = value;
        this.currentDocument = this.corpusData.filter(corpus => corpus[0] == result[2])[0]
        //   // console.log("Change document")
        // console.log("Set doc", this.currentDocument, this.corpusData, result)
      }
    },
    playerPlay() {
      if (this.$refs.videoPlayer1) {
        this.$refs.videoPlayer1.play();
      }
      if (this.$refs.videoPlayer2) {
        this.$refs.videoPlayer2.play();
      }
      if (this.$refs.videoPlayer3) {
        this.$refs.videoPlayer3.play();
      }
      if (this.$refs.videoPlayer4) {
        this.$refs.videoPlayer4.play();
      }
      this.playing = true;
      this.chart.player.playing = true;
    },
    playerStop() {
      if (this.$refs.videoPlayer1) {
        this.$refs.videoPlayer1.pause();
      }
      if (this.$refs.videoPlayer2) {
        this.$refs.videoPlayer2.pause();
      }
      if (this.$refs.videoPlayer3) {
        this.$refs.videoPlayer3.pause();
      }
      if (this.$refs.videoPlayer4) {
        this.$refs.videoPlayer4.pause();
      }
      this.playing = false;
      this.chart.player.playing = false;
    },
    playerFromStart() {
      this._playerSetToFrame(0);
    },
    playerVolumeUp() {
      this.volume = Math.max(0, this.volume + 0.05);
      this._setVolume();
    },
    playerVolumeDown() {
      this.volume = Math.max(0, this.volume - 0.05);
      this._setVolume();
    },
    playerVolumeMute() {
      this._setVolume(0);
    },
    playerFrameUp(value) {
      this.currentFrame =
        this.$refs.videoPlayer1.currentTime.toFixed(5) * this.frameRate;
      this._playerSetToFrame(this.currentFrame + value);
    },
    _playerSetToFrame(frameNumber) {
      let value = (frameNumber / this.frameRate).toFixed(5);
      this._playerSetTime(value);
    },
    _playerSetTime(value) {
      if (this.$refs.videoPlayer1) {
        this.$refs.videoPlayer1.currentTime = value;
      }
      if (this.$refs.videoPlayer2) {
        this.$refs.videoPlayer2.currentTime = value;
      }
      if (this.$refs.videoPlayer3) {
        this.$refs.videoPlayer3.currentTime = value;
      }
      if (this.$refs.videoPlayer4) {
        this.$refs.videoPlayer4.currentTime = value;
      }
    },
    playerFrameDown(value) {
      this.currentFrame =
        this.$refs.videoPlayer1.currentTime.toFixed(5) * this.frameRate;
      this._playerSetToFrame(this.currentFrame - value);
    },
    playerSetSpeed(speed) {
      if (this.$refs.videoPlayer1) {
        this.$refs.videoPlayer1.playbackRate = speed;
      }
      if (this.$refs.videoPlayer2) {
        this.$refs.videoPlayer2.playbackRate = speed;
      }
      if (this.$refs.videoPlayer3) {
        this.$refs.videoPlayer3.playbackRate = speed;
      }
      if (this.$refs.videoPlayer4) {
        this.$refs.videoPlayer4.playbackRate = speed;
      }
      this.playerSpeed = speed;
    },
    timeupdate() {
      try {
        this.currentFrame =
          this.$refs.videoPlayer1.currentTime.toFixed(5) * this.frameRate;
        this.currentTime =
          new Date(this.$refs.videoPlayer1.currentTime * 1000)
            .toISOString()
            .substring(14, 19) +
          "/" +
          new Date(this.$refs.videoPlayer1.duration * 1000)
            .toISOString()
            .substring(14, 19);
        this.progress =
          (this.$refs.videoPlayer1.currentTime /
            this.$refs.videoPlayer1.duration) *
          100;
      } catch {
        this.currentFrame = 0;
        this.progress = 0;
      }

      let filtered = Object.keys(this.subtitles).filter(
        (x) => x >= this.currentFrame
      );
      if (filtered.length) {
        this.subtext = this.subtitles[filtered[0]];
      }
      if (this.chart && this.$refs.videoPlayer1) {
        this.chart.player.time = this.$refs.videoPlayer1.currentTime;
      }
    },
    playerMainVideo(number) {
      this.mainVideo = number;
    },
    playerMainAudio(number) {
      this.mainAudio = number;
      this._setVolume();
    },
    timelineClick(event) {
      let percent =
        parseFloat(
          event.clientX - this.$refs.timeline.getBoundingClientRect().left
        ) / this.$refs.timeline.getBoundingClientRect().width;
      let time = this.$refs.videoPlayer1.duration * percent;
      if (this.$refs.videoPlayer1) {
        this.$refs.videoPlayer1.currentTime = time;
      }
      if (this.$refs.videoPlayer2) {
        this.$refs.videoPlayer2.currentTime = time;
      }
      if (this.$refs.videoPlayer3) {
        this.$refs.videoPlayer3.currentTime = time;
      }
      if (this.$refs.videoPlayer4) {
        this.$refs.videoPlayer4.currentTime = time;
      }
    },
    // calcSize(number) {
    //   let retVal = [320, 240]
    //   if (number == this.mainVideo) {
    //     retVal = [480, 320]
    //   }
    //   return retVal
    // },
    _setVolume(volume = null) {
      let _volume = volume != null ? volume : this.volume;
      if (this.$refs.videoPlayer1) {
        this.$refs.videoPlayer1.volume = this.mainAudio == 1 ? _volume : 0;
      }
      if (this.$refs.videoPlayer2) {
        this.$refs.videoPlayer2.volume = this.mainAudio == 2 ? _volume : 0;
      }
      if (this.$refs.videoPlayer3) {
        this.$refs.videoPlayer3.volume = this.mainAudio == 3 ? _volume : 0;
      }
      if (this.$refs.videoPlayer4) {
        this.$refs.videoPlayer4.volume = this.mainAudio == 4 ? _volume : 0;
      }
      this.volume = _volume
    },
    // loadData() {
    //   if (this.currentDocument) {
    //     this.mainVideo = 1;
    //     this.mainAudio = 1;
    //     this.subtitles = {};
    //     this.loading = true;
    //     this.playing = false;
    //     this._playerSetTime(0);
    //     useCorpusStore()
    //       .fetchDocument(this.currentDocument[0])
    //       .then((data) => {
    //         this.loadDataJobId = data.job;
    //       });
    //   }
    // },
    updateQueryDQD(query) {
      this.queryDQD = query
      this.validate()
    },
    updateQueryJSON(query) {
      console.log("Update JSON query", query)
      this.query = query
      // this.queryDQD = query;
      // this.validate();
    },
    async submitQuery() {
      this.WSDataResults = null;
      this.currentPage = 1;

      let data = {
        corpora: this.selectedCorpora.value,
        query: this.query,
        user: this.userId,
        room: this.roomId,
      }
      let retval = await useCorpusStore().fetchQuery(data);
      if (retval.status == "started") {
        this.loading = true;
        this.percentageDone = 0.001;
      }
      // useCorpusStore()
      //   .fetchQuery(data)
      //   .then((data) => {
      //     this.loading = true
      //   });
    },
    // connectToRoom() {
    //   this.waitForConnection(() => {
    //     this.$socket.sendObj({
    //       room: this.roomId,
    //       // room: null,
    //       action: "joined",
    //       user: this.userId,
    //     });
    //     this.$socket.onmessage = this.onSocketMessage;
    //   }, 500);
    // },
    onSocketMessage(data) {
      // let data = JSON.parse(event.data);
      console.log("SOC", data)
      if (Object.prototype.hasOwnProperty.call(data, "action")) {
        if (data["action"] === "document") {
          this.showData(data.document[0]);
          return;
        }
        else if (data["action"] === "document_ids") {
          // console.log("DOC", data);
          this.documentDict = data.document_ids
          return;
        }
        else if (data["action"] === "validate") {
          console.log("Query validation", data);
          if (data.kind == "dqd" && data.valid == true) {
            // console.log("Set query from server");
            this.query = JSON.stringify(data.json, null, 2);
          }
          this.isQueryValidData = data;
          return;
        }
        else if (data["action"] === "sentences") {
          this.failedStatus = false;
          if (this.WSDataResults && this.WSDataResults.first_job == data.first_job) {
            Object.keys(this.WSDataResults.result).forEach(key => {
              if (key > 0) {
                this.WSDataResults.result[key] = this.WSDataResults.result[key].concat(data.result[key])
              }
            })
            this.WSDataResults.result[-1] = {
              ...this.WSDataResults.result[-1],
              ...data.result[-1]
            }
          }
          else {
            this.WSDataResults = data;
          }
          return;
          // this.failedStatus = false;
          // this.WSDataResults = data;
          // return;
        } else if (data["action"] === "failed") {
          this.loading = false;
          useNotificationStore().add({
            type: "error",
            text: data.value,
          });
        }
        else if (data["action"] === "timeout") {
          console.log("Query job expired", data);
          this.failedStatus = true;
          // this.submit(null, false, false);
          return;
        }
        else if (data["action"] === "query_error") {
          this.loading = false;
          useNotificationStore().add({
            type: "error",
            text: data.info,
          });
        }
      } else if (Object.prototype.hasOwnProperty.call(data, "status")) {
        if (data["status"] == "failed") {
          this.loading = false;
          useNotificationStore().add({
            type: "error",
            text: data.value,
          });
        }
        if (data["status"] == "error") {
          this.loading = false;
          useNotificationStore().add({
            type: "error",
            text: data.info,
          });
        }
      }
    },
    // waitForConnection(callback, interval) {
    //   if (this.$socket.readyState === 1) {
    //     callback();
    //   } else {
    //     setTimeout(() => {
    //       this.waitForConnection(callback, interval);
    //     }, interval);
    //   }
    // },
    showData(data) {
      this.chart = eventDrops({
        d3,
        range: {
          start: new Date("2022-01-01T00:00:00.000"),
          end: new Date("2022-01-01T00:50:00.000"),
        },
        // axis: {
        //   formats: {
        //       milliseconds: '%L',
        //       seconds: ':%S',
        //       minutes: '%H:%M',
        //       hours: '%H',
        //       days: '',
        //       weeks: '',
        //       months: '',
        //       year: '',
        //   },
        //   verticalGrid: false,
        //   tickPadding: 6,
        // },
        drop: {
          date: (d) => new Date(d.date),
          // onClick: e => {
          //   // console.log(e, 123123)
          //   this._playerSetToFrame(e.frameNumber)
          // },
          // onMouseOver: commit => {
          //   tooltip
          //     .transition()
          //     .duration(200)
          //     .style('opacity', 1)
          //     .style('pointer-events', 'auto');

          //   tooltip
          //     .html(`
          //       <div class="content">
          //         ${commit.message}
          //       </div>
          //     `)
          //     .style('left', `${d3.event.pageX - 30}px`)
          //     .style('top', `${d3.event.pageY + 20}px`)
          // },
          // onMouseOut: () => {
          //   tooltip
          //     .transition()
          //     .duration(500)
          //     .style('opacity', 0)
          //     .style('pointer-events', 'none');
          // },
        },
      });

      // this.chart.player.time = 0

      let that = this;
      function calcDate(frameNumber) {
        try {
          let shift = that.corpusData[that.currentDocument[0]-2][3][0]
          frameNumber = frameNumber - shift
        }
        catch {
          console.log("Shift error")
        }
        Utils.msToTime((frameNumber * 1000) / that.frameRate);
        let time = new Date((parseFloat(frameNumber) / that.frameRate) * 1000)
          .toISOString()
          .substring(11, 23);
        return `2022-01-01T${time}`;
      }

      // Prepare data - group by agent
      let _tmpData = {};
      if (data && data.tracks) {
        for (let track of Object.values(data.tracks)) {
          if (track.sentences && track["agent"]) {
            if (!(track["agent"] in _tmpData)) {
              _tmpData[track["agent"]] = {
                sentences: [],
                gestures: [],
              };
            }
            let _track = {
              name: track["name"],
              data: [],
              height: 50,
            };
            // let _track2 = {
            //   name: "Annotation",
            //   data: [],
            // };
            // let _track3 = {
            //   name: "Lemma",
            //   data: [],
            // };
            for (let sentence of track["sentences"]) {
              _track.data.push({
                date: calcDate(sentence.frame_range[0]),
                dateEnd: calcDate(sentence.frame_range[1]),
                specClass: "threeLine",
                l1: sentence.content.map((text) => text[0]).join(" "),
                l2: sentence.content.map((text) => text[1]).join(" "),
                l3: sentence.content.map((text) => text[2]).join(" "),
                frameRange: sentence.frame_range,
              });
              // _track2.data.push({
              //   date: calcDate(sentence.frame_range[0]),
              //   dateEnd: calcDate(sentence.frame_range[1]),
              //   message: sentence.content.map((text) => text[3]).join(" "),
              //   frameRange: sentence.frame_range,
              // });
              // _track3.data.push({
              //   date: calcDate(sentence.frame_range[0]),
              //   dateEnd: calcDate(sentence.frame_range[1]),
              //   message: sentence.content.map((text) => text[2]).join(" "),
              //   frameRange: sentence.frame_range,
              // });
              this.subtitles[sentence.frame_range[1]] = sentence.content
                .map((text) => text[1])
                .join(" ");
            }
            _tmpData[track["agent"]]["sentences"].push(_track);
            // _tmpData[track["agent"]]["sentences"].push(_track2);
            // _tmpData[track["agent"]]["sentences"].push(_track3);
          }
          if (track.gestures && track["agent"]) {
            if (!(track["agent"] in _tmpData)) {
              _tmpData[track["agent"]] = {
                sentences: [],
                gestures: [],
              };
            }
            let _track = {
              name: track["name"],
              data: [],
            };
            for (let gesture of track["gestures"]) {
              _track.data.push({
                date: calcDate(gesture.frame_range[0]),
                dateEnd: calcDate(gesture.frame_range[1]),
                specClass: "oneLine",
                l2: gesture.gesture,
                frameRange: gesture.frame_range,
              });
            }
            _tmpData[track["agent"]]["gestures"].push(_track);
          }
        }
      }

      let repositoriesData = [];
      for (let agentId of Object.keys(_tmpData)) {
        for (let sentence of _tmpData[agentId]["sentences"]) {
          repositoriesData.push(sentence);
        }
        for (let gesture of _tmpData[agentId]["gestures"]) {
          repositoriesData.push(gesture);
        }
      }

      d3.select("#eventdrops-demo").data([repositoriesData]).call(this.chart);

      // this.loading = false;
      if (this.setResultTime) {
        // console.log("Set time", this.setResultTime)
        this._playerSetTime(this.setResultTime);
        this.setResultTime = null;
      }
    },
    setExample(num) {
      if (num == 1) {
        this.queryDQD = `Segment s

sequence@s
  Token t1
    upos = DET
  Token t2
    upos = NOUN

Gesture g1
  agent = s.agent
  type = PG
  start >= s.start - 3s
  end <= s.end + 3s

KWIC => plain
  context
    s
  entities
    t1
    t2
    g1

`
      }
      else if (num == 2) {
        this.queryDQD = `Segment s

sequence@s
  Token@s t1
    upos = DET
  Token@s t2
    upos = NOUN

Gesture g
  agent = s.agent
  type in (PG, OG, IG, UG)
  g.start >= s.start - 5s
  g.end <= s.end + 2s

KWIC => plain
  context
    s
  entities
    t1
    t2
    g

`
      }
      else if (num == 3) {
        this.queryDQD = `Segment s1
  agent.name = speaker_1

Token@s1 t1
  form = [kK]opf

Segment s2
  agent.name = speaker_2
  start >= s1.start
  end <= s1.end

Token@s2 t2
  form = rechts

KWIC => plain
  context
    s1
    s2
  entities
    t1
    t2

`
      }
      else if (num == 4) {
        this.queryDQD = `Document d

Gesture g1
  agent.name = speaker_1

NOT EXISTS
  Gesture g2
    agent.name = speaker_2
    start >= g1.start - 3s
    end <= g1.end + 3s

KWIC => plain
  context
    d
  entities
    g1

`
      }
      this.editorIndex++
      this.validate()
    },
    // async fetch() {
    //   let data = {
    //     user: this.userId,
    //     room: this.roomId,
    //     // room: null,
    //   };
    //   // useCorpusStore().fetchQueries(data);
    //   let retval = await useCorpusStore().fetchQuery(data);
    //   if (retval.status == "started") {
    //     this.loading = true;
    //     this.percentageDone = 0.001;
    //   }
    // },
    sendLeft() {
      this.$socket.sendObj({
        room: this.roomId,
        // room: null,
        action: "left",
        user: this.userId,
      });
    },
    // resume() {
    //   this.submit(null, true);
    // },
    stop() {
      this.percentageDone = 0;
      this.percentageTotalDone = 0;
      this.failedStatus = false;
      this.$socket.sendObj({
        room: this.roomId,
        action: "stop",
        user: this.userId,
      });
      this.loading = false;
    },
    validate() {
      this.$socket.sendObj({
        room: this.roomId,
        action: "validate",
        user: this.userId,
        query: this.currentTab == "json" ? this.query : this.queryDQD + "\n",
      });
    },
    loadDocuments() {
      this.documentDict = {}
      if (this.roomId && this.userId) {
        useCorpusStore().fetchDocuments({
          room: this.roomId,
          user: this.userId,
          corpora_id: this.selectedCorpora.value,
        })
      }
      else {
        setTimeout(() => this.loadDocuments(), 200)
      }
    },
    loadDocument() {
      try {
        this.$refs.videoPlayer1.load();
        if (this.currentDocument[2].length > 1) {
          this.$refs.videoPlayer2.load();
        }
        if (this.currentDocument[2].length > 2) {
          this.$refs.videoPlayer3.load();
        }
        if (this.currentDocument[2].length > 3) {
          this.$refs.videoPlayer4.load();
        }
      } catch {
        console.log("Error player");
      }
      if (this.currentDocument) {
        // console.log("AA", this.currentDocument)
        useCorpusStore().fetchDocument({
          doc_id: this.currentDocument[0],
          corpora: [this.selectedCorpora.value],
          user: this.userId,
          room: this.roomId,
        });
      }
    },
  },
  mounted() {
    if (this.userData) {
      this.userId = this.userData.user.id;
      // this.connectToRoom();
      // this.stop();
      this.validate();
    }
    this._setVolume();
    window.addEventListener("keydown", (e) => {
      if (e.key == "ArrowLeft") {
        // key left
        this.playerFrameDown(25);
      } else if (e.key == "ArrowRight") {
        // key right
        this.playerFrameUp(25);
      }
    });
    // window.addEventListener("keypress", (e) => {
    //   if (e.key == " ") {
    //     e.preventDefault();
    //     if (this.playing) {
    //       this.playerStop();
    //     } else {
    //       this.playerPlay();
    //     }
    //   }
    // });
    window.addEventListener("timelineClick", () => {
      if (this.chart && this.chart.player) {
        let time = this.chart.player.time;
        this._playerSetTime(time);
      }
    });


    // this.showData(exampleData.document[0])
    // exampleData;
  },
  // beforeMount() {
  //   window.addEventListener("beforeunload", this.sendLeft);
  // },
  // unmounted() {
  //   this.sendLeft();
  // },
  watch: {
    corpora: {
      handler() {
        if (this.preselectedCorporaId) {
          let corpus = this.corpora.filter(corpus => corpus.meta.id == this.preselectedCorporaId)
          if (corpus.length) {
            this.selectedCorpora = {
              name: corpus[0].meta.name,
              value: corpus[0].meta.id,
              corpus: corpus[0],
            }
          }
          this.preselectedCorporaId = null
          this.loadDocuments()
        }
      },
      immediate: true,
      deep: true,
    },
    messages: {
      handler() {
        let _messages = this.messages;
        if (_messages.length > 0) {
          console.log("WSM", _messages)
          _messages.forEach(message => this.onSocketMessage(message))
          useWsStore().clear();
        }
      },
      immediate: true,
      deep: true,
    },
    selectedCorpora() {
      this.loadDocuments()
      history.pushState(
        {},
        null,
        `/player/${this.selectedCorpora.value}/${this.selectedCorpora.corpus.shortname}`
      )
    },
    currentDocument() {
      this.loadDocument()
    },
    volume() {
      this._setVolume();
    },
    WSDataResults() {
      if (this.WSDataResults) {
        if (this.WSDataResults.percentage_done) {
          this.percentageDone = this.WSDataResults.percentage_done;
        }
        if (
          this.WSDataResults.total_results_so_far &&
          this.WSDataResults.projected_results
        ) {
          this.percentageTotalDone =
            (this.WSDataResults.total_results_so_far /
              this.WSDataResults.projected_results) *
            100;
        }
        if (["finished"].includes(this.WSDataResults.status)) {
          this.percentageDone = 100;
          this.percentageTotalDone = 100;
        }
        if (["satisfied"].includes(this.WSDataResults.status)) {
          // this.percentageDone = this.WSDataResults.hit_limit/this.WSDataResults.projected_results*100.
          this.percentageDone = 100;
          this.loading = false;
        }
        // console.log("XXX", this.percentageTotalDone, this.percentageDone);
        if (this.WSDataResults.percentage_done >= 100) {
          this.loading = false;
        }
      }
    },
  },
};
</script>

<style scoped>
video {
  margin-right: 3px;
  object-fit: fill;
  height: 140px;
}
.vertical-line {
  position: absolute;
  width: 1px;
  height: 56px;
  margin-top: -10px;
  background-color: rgb(114, 114, 114);
}
.progress-bar {
  border-radius: 4px;
}
.btn-text-icon {
  font-weight: bold;
  color: #fff;
  font-size: 12px;
  padding-top: 6px;
}

.video-text-test {
  position: absolute;
  top: 400px;
  width: 710px;
  left: 45px;
  color: #fff;
  font-weight: bold;
  user-select: none;
  font-size: 110%;
  text-align: center;
  background-color: #0000008c;
  padding: 2px;
}

.video-box {
  height: 450px;
  display: flex;
  flex-flow: column wrap;
  transition: 2s ease;
  position: relative;
  cursor: default;
}
.video-box > div {
  flex: 1 1 80px;
  margin: 1px;
}
.video-box > div.active {
  min-height: 100%;
  order: -1;
}
div.active video {
  height: 450px;
}

* >>> .drop {
  cursor: pointer;
}
.query-field {
  height: 328px;
}
.list-no-bullets {
  list-style-type: none;
}
.list-no-bullets li:hover {
  cursor: pointer;
  opacity: 0.8;
}
</style>
