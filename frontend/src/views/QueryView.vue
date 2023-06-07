<template>
  <div class="query">
    <Title :title="'Query'" class="mt-4" />
    <div class="container mt-4">
      <div class="row">
        <div class="col-6">
          <div class="mb-3">
            <label class="form-label">Corpora</label>
            <multiselect
              v-model="selectedCorpora"
              :options="corporaOptions"
              :multiple="false"
              label="name"
              track-by="value"
            ></multiselect>
          </div>
          <!-- <div class="mb-3">
            <label class="form-label">Room</label>
            <input
              type="text"
              class="form-control"
              disabled
            />
          </div> -->
          <!-- <div class="mb-3">
            <label class="form-label"
              >Query name</label
            >
            <input type="text" class="form-control" v-model="queryName" />
          </div> -->
          <!-- <div class="mb-3">
            <label class="form-label">User</label>
            <input
              type="text"
              class="form-control"
              v-model="userId"
              disabled
            />
          </div> -->
          <div class="row">
            <div class="col-3">
              <div class="mb-3">
                <label class="form-label">Res. per page</label>
                <input
                  type="number"
                  class="form-control"
                  disabled
                  v-model="resultsPerPage"
                />
              </div>
            </div>
            <div class="col-3">
              <div class="mb-3">
                <label class="form-label">No. of results</label>
                <input
                  type="number"
                  class="form-control"
                  disabled
                  v-model="nResults"
                />
              </div>
            </div>
            <div class="col-6">
              <div class="mb-3">
                <label class="form-label">Languages</label>
                <multiselect
                  v-model="languages"
                  :options="availableLanguages"
                  :multiple="true"
                ></multiselect>
              </div>
            </div>
          </div>
          <div class="mb-3">
            <button
              type="button"
              @click="submit"
              class="btn btn-primary"
              :disabled="
                (selectedCorpora && selectedCorpora.length == 0) ||
                loading ||
                (isQueryValidData != null && isQueryValidData.valid == false) ||
                !query ||
                languages.length == 0
              "
            >
              Submit
            </button>
            <button
              type="button"
              @click="stop"
              :disabled="loading == false"
              class="btn btn-primary"
            >
              Stop
            </button>
            <!-- <button
              type="button"
              @click="resume"
              class="btn btn-primary"
              :disabled="selectedCorpora.length == 0"
            >
              Resume
            </button>
            <button
              type="button"
              @click="stop"
              :disabled="loading == false"
              class="btn btn-primary"
            >
              Stop
            </button>
            <button
              type="button"
              class="btn btn-primary"
              data-bs-toggle="modal"
              data-bs-target="#saveQueryModal"
            >
              Save query
            </button>
            <button type="button" @click="fetch" class="btn btn-primary">
              Fetch
            </button> -->
            <!-- <button type="button" @click="validate" :disabled="!query.trim()" class="btn btn-primary">Validate</button> -->
          </div>
          <div class="lds-ripple" v-if="loading">
            <div></div>
            <div></div>
          </div>
        </div>
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
        </div>
        <!-- <div class="col-12">
          <button type="button" @click="submit" class="btn btn-primary" :disabled="selectedCorpora.length == 0">
            Submit
          </button>
          <button type="button" @click="resume" class="btn btn-primary" :disabled="selectedCorpora.length == 0">
            Resume
          </button>
          <button type="button" @click="stop" class="btn btn-primary">
            Stop
          </button>
          <button type="button" @click="save" :disabled="!queryName" class="btn btn-primary">Save</button>
          <button type="button" @click="fetch" class="btn btn-primary">Fetch</button>
          <button type="button" @click="validate" :disabled="!query.trim()" class="btn btn-primary">Validate</button>

        </div> -->
        <div class="col">
          <hr class="mt-5 mb-5" />
          <h6 class="mb-3">Query result</h6>
          <div class="progress mb-2">
            <div
              class="progress-bar"
              :class="
                loading ? 'progress-bar-striped progress-bar-animated' : ''
              "
              role="progressbar"
              aria-label="Basic example"
              :style="`width: ${percentageDone}%`"
              :aria-valuenow="percentageDone"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              {{ percentageDone.toFixed(2) }}%
            </div>
          </div>
          Total progress
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
          </div>
          <div class="row mb-4">
            <div class="col">
              <p class="mb-1">
                Number of results:
                <span
                  class="text-bold"
                  v-html="WSDataResults.total_results_so_far"
                ></span>
              </p>
            </div>
            <div class="col">
              <p class="mb-1">
                Projected results:
                <span
                  class="text-bold"
                  v-html="WSDataResults.projected_results"
                ></span>
              </p>
            </div>
            <div class="col">
              <p class="mb-1">
                Batch done:
                <span
                  class="text-bold"
                  v-html="WSDataResults.batches_done"
                ></span>
              </p>
            </div>
            <div class="col">
              <p class="mb-1">
                Status:
                <span class="text-bold" v-html="WSDataResults.status"></span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="container-fluid">
      <div class="row">
        <div
          class="col-12"
          v-if="
            WSDataResults &&
            WSDataResults.result &&
            WSDataSentences &&
            WSDataSentences.result
          "
        >
          <nav>
            <div class="nav nav-tabs" id="nav-tab" role="tablist">
              <button
                class="nav-link"
                :class="index == 0 ? 'active' : ''"
                :id="`nav-results-tab-${index}`"
                data-bs-toggle="tab"
                :data-bs-target="`#nav-results-${index}`"
                type="button"
                role="tab"
                :aria-controls="`nav-results-${index}`"
                aria-selected="true"
                v-for="(resultSet, index) in WSDataResults.result['0']
                  .result_sets"
                :key="`result-btn-${index}`"
              >
                {{ resultSet.name }}
                <small>(<span v-if="resultSet.type == 'plain'">
                  {{
                    WSDataSentences && WSDataSentences.result[index + 1]
                      ? WSDataSentences.result[index + 1].length
                      : 0
                  }}</span
                >
                <span v-else>{{
                  WSDataResults && WSDataResults.result[index + 1]
                    ? WSDataResults.result[index + 1].length
                    : 0
                }}</span>
                )</small>
              </button>
              <!-- <button
                class="nav-link"
                id="nav-stats-tab"
                data-bs-toggle="tab"
                data-bs-target="#nav-stats"
                type="button"
                role="tab"
                aria-controls="nav-stats"
                aria-selected="false"
              >
                Statistics
              </button> -->
            </div>
          </nav>
          <div class="tab-content" id="nav-tabContent">
            <div
              class="tab-pane fade show"
              :class="index == 0 ? 'active' : ''"
              :id="`nav-results-${index}`"
              role="tabpanel"
              :aria-labelledby="`nav-results-${index}-tab`"
              v-for="(resultSet, index) in WSDataResults.result['0']
                .result_sets"
              :key="`result-tab-${index}`"
            >
              <ResultsKWICView
                v-if="resultSet.type == 'plain' && WSDataSentences"
                :data="WSDataSentences.result[index + 1]"
                :sentences="WSDataSentences.result[-1]"
                :attributes="resultSet.attributes"
                :corpora="selectedCorpora"
                @updatePage="updatePage"
                :resultsPerPage="resultsPerPage"
                :loading="loading"
              />
              <!-- <ResultsAnalysisView
                v-else-if="resultSet.type == 'analysis'"
                v-else-if="resultSet.type == 'collocation'"
                :data="WSDataResults.result[index + 1]"
                :attributes="resultSet.attributes"
              /> -->
              <ResultsTableView
                v-else
                :data="WSDataResults.result[index + 1]"
                :attributes="resultSet.attributes"
                :resultsPerPage="resultsPerPage"
              />
            </div>
            <!-- <div
              class="tab-pane fade"
              id="nav-stats"
              role="tabpanel"
              aria-labelledby="nav-stats-tab"
            >
              <table v-if="stats" class="table">
                <thead>
                  <tr>
                    <th scope="col">Name</th>
                    <th scope="col">Count</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(statsKey, index) in Object.keys(stats.result)"
                    :key="index"
                  >
                    <td>{{ statsKey }}</td>
                    <td>{{ stats.result[statsKey] }}</td>
                  </tr>
                </tbody>
              </table>
            </div> -->
          </div>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <div
      class="modal fade"
      id="saveQueryModal"
      tabindex="-1"
      aria-labelledby="saveQueryModalLabel"
      aria-hidden="true"
    >
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="saveQueryModalLabel">Save query</h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body text-start">
            <label for="queryName" class="form-label">Query name</label>
            <input
              type="text"
              class="form-control"
              id="queryName"
              v-model="queryName"
            />
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              Close
            </button>
            <button
              type="button"
              :disabled="!queryName"
              @click="saveQuery"
              class="btn btn-primary"
            >
              Save query
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container {
  text-align: left;
}
.pre {
  font-family: "Courier New", Courier, monospace;
}
.query {
  margin-bottom: 100px;
}
.query-field {
  height: 328px;
}
.query-field.error {
  border-color: red;
}
.btn-primary {
  margin-left: 2px;
  margin-right: 2px;
}
textarea {
  font-family: Consolas, Monaco, Lucida Console, Liberation Mono,
    DejaVu Sans Mono, Bitstream Vera Sans Mono, Courier New, monospace;
}
.error-text {
  margin-top: 7px;
}
</style>

<script>
import { mapState } from "pinia";

import { useCorpusStore } from "@/stores/corpusStore";
import { useNotificationStore } from "@/stores/notificationStore";
import { useUserStore } from "@/stores/userStore";
import { useWsStore } from "@/stores/wsStore";

import Title from "@/components/TitleComponent.vue";
import ResultsTableView from "@/components/results/TableView.vue";
import ResultsKWICView from "@/components/results/KWICView.vue";
import EditorView from "@/components/EditorView.vue";

export default {
  name: "QueryTestView",
  data() {
    return {
      query: "",
      queryDQD: `Turn d
    IsPresident = no
    PoliticalGroup != NI

Segment@d s

sequence seq
    Token@s t1
        upos = DET
    Token@s t2
        upos = ADJ
    Token@s t3
        lemma = ^fr.*
        lemma.length > 5
        upos = NOUN

set tdeps
    Token@s tx
        DepRel
            head = t3
            dep = tx

Token@s thead
    upos = VERB
    DepRel
        head = thead
        dep = t3


myKWIC1 => plain
    context
        s
    entities
        t1
        #t2
        t3

myKWIC2 => plain
    context
        s
    entities
        t1
        t2
        t3

myStat1 => analysis
    attributes
        t1.lemma
        t2.lemma
        t3.lemma
    functions
        frequency
    filter
        frequency > 10

myStat2 => analysis
    attributes
        t3.lemma
        d.OriginalLanguage
    functions
        frequency
    filter
        frequency > 10

myColl1 => collocation
    center
        t3
    window
        -5..+5
    attribute
        lemma

myColl2 => collocation
    space
        tdeps
    attribute
        lemma
    comment
        PoS collocations of all dependends
`,
      userId: null,
      wsConnected: false,
      selectedCorpora: this.corpora
        ? this.corpora
            .filter((corpus) => corpus.meta.id == 2)
            .map((corpus) => {
              return {
                name: corpus.meta.name,
                value: corpus.meta.id,
                corpus: corpus,
              };
            })
        : [],
      isQueryValidData: null,
      WSDataResults: "",
      WSDataSentences: "",
      nResults: 200,
      pageSize: 100,
      languages: ["en"],
      queryName: "",
      currentTab: "dqd",
      simultaneousMode: false,
      percentageDone: 0,
      percentageTotalDone: 0,
      loading: false,
      stats: null,
      queryTest: "const noop = () => {}",
      resultsPerPage: 100,
      failedStatus: false,
      // nResults: 50,
    };
  },
  components: {
    Title,
    ResultsKWICView,
    ResultsTableView,
    // ResultsAnalysisView,
    // KWICTable,
    // DetailsTableView,
    EditorView,
  },
  mounted() {
    if (this.userData) {
      this.userId = this.userData.user.id;
      // this.connectToRoom();
      // this.stop();
    }
  // },
  // beforeMount() {
  //   window.addEventListener("beforeunload", this.sendLeft);
  // },
  // unmounted() {
  //   this.sendLeft();
  },
  watch: {
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
    userData() {
      this.userId = this.userData.user.id;
      // this.connectToRoom();
    },
    selectedCorpora() {
      this.validate();
    },
    corpora() {
      this.selectedCorpora =
        this.corpora && this.selectedCorpora.length == 0
          ? this.corpora
              .filter((corpus) => corpus.meta.id == 2)
              .map((corpus) => {
                return {
                  name: corpus.meta.name,
                  value: corpus.meta.id,
                  corpus: corpus,
                };
              })
          : [];
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
      }

      if (this.WSDataResults.percentage_done >= 100) {
        this.loading = false;
      }
    },
    query() {
      // console.log("Check is valid")
      if (this.currentTab != "dqd") {
        this.validate();
      }
    },
  },
  methods: {
    updatePage(currentPage) {
      let newNResults = this.resultsPerPage * Math.max(currentPage + 1, 3);
      // console.log("Page updated 1", currentPage, this.nResults, newNResults);
      if (newNResults > this.nResults) {
        this.nResults = newNResults;
        this.submit(null, true);
        // console.log("Submit", newNResults);
      }
      // console.log("Page updated 2", currentPage, this.nResults, newNResults);
    },
    updateQueryDQD(queryDQD) {
      this.queryDQD = queryDQD;
      this.validate();
    },
    sendLeft() {
      this.$socket.sendObj({
        room: this.roomId,
        // room: null,
        action: "left",
        user: this.userId,
      });
      this.wsConnected = false;
      console.log("Left WS")
    },
    // connectToRoom() {
    //   console.log("Connect to WS room", this.wsConnected, this.$socket.readyState)
    //   if (this.$socket.readyState != 1 || this.wsConnected == false){
    //     console.log("Connect to WS")
    //     this.waitForConnection(() => {
    //       this.$socket.sendObj({
    //         room: this.roomId,
    //         // room: null,
    //         action: "joined",
    //         user: this.userId,
    //       });
    //       this.wsConnected = true;
    //       this.$socket.onmessage = this.onSocketMessage;
    //       console.log("Connected to WS")
    //       this.validate();
    //     }, 500);
    //   }
    // },
    // waitForConnection(callback, interval) {
    //   if (this.$socket.readyState === 1) {
    //     callback();
    //   } else {
    //     setTimeout(() => {
    //       this.waitForConnection(callback, interval);
    //     }, interval);
    //   }
    // },
    onSocketMessage(data) {
      // the below is just temporary code
      // let data = JSON.parse(event.data);
      // console.log("R", event)
      if (Object.prototype.hasOwnProperty.call(data, "action")) {
        if (data["action"] === "interrupted") {
          console.log("Query interrupted", data);
          this.loading = false;
          useNotificationStore().add({
            type: "error",
            text: data.toString(),
          });
          return;
        }
        if (data["action"] === "timeout") {
          console.log("Query job expired", data);
          this.failedStatus = true;
          this.submit(null, false, false);
          return;
        }
        if (data["action"] === "validate") {
          // console.log("Query validation", data);
          if (data.kind == "dqd" && data.valid == true) {
            // console.log("Set query from server");
            this.query = JSON.stringify(data.json, null, 2);
          }
          this.isQueryValidData = data;
          return;
        }
        if (data["action"] === "stats") {
          // console.log("stats", data);
          this.stats = data;
          return;
        }
        if (data["action"] === "update_config") {
          // todo: when a new corpus is added, all connected websockets
          // will get this message containing the new config data. plz
          // ensure that it gets added to the corpusstore properly and
          // the app is updated accordingly
          delete data["config"]["-1"]
          // todo: no idea if this is right:
          useCorpusStore().corpora = Object.keys(data["config"]).map(corpusId => {
            let corpus = data["config"][corpusId]
            corpus.meta["id"] = corpusId
            return corpus
          });
          // we could also do this but we already have the data here...
          // useCorpusStore().fetchCorpora();
          return;
        }
        if (data["action"] === "fetch_queries") {
          console.log("do something here with the fetched queries?", data);
          return;
        } else if (data["action"] === "store_query") {
          console.log("query stored", data);
          return;
        } else if (data["action"] === "stopped") {
          if (data["n"]) {
            console.log("queries stopped", data);
            useNotificationStore().add({
              type: "success",
              text: "Query stopped",
            });
            this.loading = false
          }
          return;
        } else if (data["action"] === "query_result") {
          // console.log("query_result", data);
          if (
            this.failedStatus &&
            data.result.length < this.WSDataResults.n_results
          ) {
            return;
          }
          this.failedStatus = false;
          data["n_results"] = data["result"].length;
          this.WSDataResults = data;
          return;
        } else if (data["action"] === "sentences") {
          // console.log("sentences", data);
          this.WSDataSentences = data;
          return;
        } else if (data["action"] === "failed") {
          this.loading = false;
          useNotificationStore().add({
            type: "error",
            text: data.value,
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

      // we might need this block for stats related stuff later, don't worry about it much right now
      if (this.simultaneousMode) {
        this.allResults = this.allResults.concat(data["result"]);
        if (this.allResults.length >= data["total_results_requested"]) {
          this.allResults = this.allResults.slice(
            0,
            data["total_results_requested"]
          );
          this.enough(data["simultaneous"]);
          data["status"] = "satisfied";
        }
        data["first_result"] = this.allResults[0];
        data["n_results"] = this.allResults.length;
        delete data["result"];
        data["percentage_done"] += this.percentageDone;
        this.WSDataResults = data;
      }
    },
    async submit(event, resumeQuery = false, cleanResults = true) {
      if (resumeQuery == false) {
        this.failedStatus = false;
        this.stop();
        if (cleanResults == true) {
          this.WSDataResults = {};
          this.WSDataSentences = {};
        }
      }
      let data = {
        // corpora: this.selectedCorpora.map((corpus) => corpus.value),
        corpora: this.selectedCorpora.value,
        query: this.query,
        user: this.userId,
        room: this.roomId,
        // room: null,
        // page_size: this.pageSize,
        // page_size: this.nResults,
        page_size: this.resultsPerPage,
        languages: this.languages,
        total_results_requested: this.nResults,
        stats: true,
        resume: resumeQuery,
        simultaneous: this.simultaneousMode,
      };
      if (resumeQuery) {
        data["previous"] = this.WSDataResults.job;
      }
      let retval = await useCorpusStore().fetchQuery(data);
      if (retval.status == "started") {
        this.loading = true;
        this.percentageDone = 0.001;
      }
    },
    resume() {
      this.submit(null, true);
    },
    stop() {
      this.percentageDone = 0;
      this.percentageTotalDone = 0;
      this.failedStatus = false;
      this.$socket.sendObj({
        room: this.roomId,
        // room: null,
        action: "stop",
        user: this.userId,
      });
      this.loading = false;
      // if (this.WSData) {
      //   this.WSData.percentage_done = 100;
      // }
    },
    enough(job) {
      this.$socket.sendObj({
        room: this.roomId,
        // room: null,
        action: "enough_results",
        user: this.userId,
        job: job,
      });
    },
    validate() {
      // console.log("RRRR")
      this.$socket.sendObj({
        room: this.roomId,
        // room: null,
        action: "validate",
        user: this.userId,
        query: this.currentTab == "json" ? this.query : this.queryDQD + "\n",
        // query_name: this.queryName,
      });
    },
    saveQuery() {
      let data = {
        // corpora: this.selectedCorpora.map((corpus) => corpus.value),
        corpora: this.selectedCorpora.value,
        query: this.query,
        user: this.userId,
        room: this.roomId,
        // room: null,
        page_size: this.pageSize,
        languages: this.languages,
        total_results_requested: this.nResults,
        query_name: this.queryName,
      };
      useCorpusStore().saveQuery(data);
    },
    fetch() {
      let data = {
        user: this.userId,
        room: this.roomId
        // room: null,
      };
      useCorpusStore().fetchQueries(data);
    },
  },
  computed: {
    ...mapState(useCorpusStore, ["queryData", "corpora"]),
    ...mapState(useUserStore, ["userData", "roomId"]),
    ...mapState(useWsStore, ["messages"]),
    availableLanguages() {
      let retval = [];
      if (this.selectedCorpora) {
        if (
          this.corpora.filter(
            (corpus) => corpus.meta.id == this.selectedCorpora.value
          ).length
        ) {
          retval = Object.keys(
            this.corpora.filter(
              (corpus) => corpus.meta.id == this.selectedCorpora.value
            )[0].layer
          )
            .filter((key) => key.startsWith("Token@"))
            .map((key) => key.replace(/Token@/, ""));
          if (retval.length == 0) {
            retval = ["en"];
          }
        }
      }
      return retval;
    },
    corporaOptions() {
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
  },
};
</script>
