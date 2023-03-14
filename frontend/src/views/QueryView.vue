<template>
  <div class="query">
    <Title :title="'Query test'" />
    <div class="container mt-4">
      <div class="row">
        <div class="col-6">
          <div class="form-floating mb-3">
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
            <label for="floatingTextarea">Query</label>
            <p
              class="error-text text-danger"
              v-if="isQueryValidData && isQueryValidData.valid != true"
            >
              {{ isQueryValidData.error }}
            </p>
          </div>
        </div>
        <div class="col-6">
          <div class="mb-3">
            <label for="exampleInputEmail1" class="form-label">Corpora</label>
            <multiselect
              v-model="selectedCorpora"
              :options="corporaOptions()"
              :multiple="false"
              label="name"
              track-by="value"
            ></multiselect>
          </div>
          <!-- <div class="mb-3">
            <label for="exampleInputEmail1" class="form-label">Room</label>
            <input
              type="text"
              class="form-control"
              disabled
            />
          </div> -->
          <!-- <div class="mb-3">
            <label for="exampleInputEmail1" class="form-label"
              >Query name</label
            >
            <input type="text" class="form-control" v-model="queryName" />
          </div> -->
          <!-- <div class="mb-3">
            <label for="exampleInputEmail1" class="form-label">User</label>
            <input
              type="text"
              class="form-control"
              v-model="userId"
              disabled
            />
          </div> -->
          <div class="row">
            <div class="col-6">
              <div class="mb-3">
                <label for="exampleInputEmail1" class="form-label"
                  >Number of results</label
                >
                <input type="number" class="form-control" v-model="nResults" />
              </div>
            </div>
            <div class="col-6">
              <div class="mb-3">
                <label for="exampleInputEmail1" class="form-label"
                  >Languages (split by comma)</label
                >
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
              :disabled="selectedCorpora.length == 0"
            >
              Submit
            </button>
            <button
              type="button"
              @click="resume"
              class="btn btn-primary"
              :disabled="selectedCorpora.length == 0"
            >
              Resume
            </button>
            <button type="button" @click="stop" :disabled="loading == false" class="btn btn-primary">
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
            </button>
            <!-- <button type="button" @click="validate" :disabled="!query.trim()" class="btn btn-primary">Validate</button> -->
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
          <!-- <h6>Query submit result</h6>
          <div
            v-html="JSON.stringify(queryData)"
            v-if="queryData"
            class="pre"
          ></div> -->
          <h6 class="mb-3">Query result (WS)</h6>
          <div class="progress mb-2">
            <div
              class="progress-bar"
              :class="
                percentageDone < 100
                  ? 'progress-bar-striped progress-bar-animated'
                  : ''
              "
              role="progressbar"
              aria-label="Basic example"
              :style="`width: ${percentageDone}%`"
              :aria-valuenow="percentageDone"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              {{ percentageDone }}
            </div>
          </div>
          <div class="row">
            <div class="col">
              <p class="mb-1">
                Number of results:
                <span class="text-bold" v-html="WSData.n_results"></span>
              </p>
            </div>
            <div class="col">
              <p class="mb-1">
                Projected results:
                <span
                  class="text-bold"
                  v-html="WSData.projected_results"
                ></span>
              </p>
            </div>
            <div class="col">
              <p class="mb-1">
                Batch done:
                <span class="text-bold" v-html="WSData.batches_done"></span>
              </p>
            </div>
            <div class="col">
              <p class="mb-1">
                Status: <span class="text-bold" v-html="WSData.status"></span>
              </p>
            </div>
          </div>
          <h6 class="mt-4 mb-3">Results:</h6>
          <KWICTable :data="WSData.result" v-if="WSData && WSData.result" />
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
            <label for="queryName" class="form-label"
              >Query name</label
            >
            <input type="text" class="form-control" id="queryName" v-model="queryName" />
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              Close
            </button>
            <button type="button" :disabled="!queryName" @click="saveQuery" class="btn btn-primary">Save query</button>
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
.query-field {
  height: 328px;
  /* background: url(http://i.imgur.com/2cOaJ.png);
  background-attachment: local;
  background-repeat: no-repeat;
  padding-left: 40px; */
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
import { useUserStore } from "@/stores/userStore";
import Title from "@/components/TitleComponent.vue";
import KWICTable from "@/components/KWICTableView.vue";

export default {
  name: "QueryTestView",
  data() {
    return {
      query: `
{
    "comment": "An NP with an unlimited number of adjectives (at least one)",
    "nodes": [{
            "name": "t1",
            "layer": "token",
            "filter": {
                "attribute": "upos",
                "value": "DET",
                "op": "="
            }
        },
        {
            "name": "t2",
            "layer": "token",
            "filter": {
                "attribute": "lemma",
                "value": "friend",
                "op": "="
            }
        }
    ],
    "edges": [{
        "source": "t1",
        "target": "t2",
        "constraint": {
            "AND": [{
                    "relation": "distance",
                    "value": [2, null]
                },
                {
                    "filter": "repeat",
                    "elements": [{
                        "attribute": "upos",
                        "value": "ADJ",
                        "op": "="
                    }],
                    "repetitions": [1, null]
                }
            ]
        }
    }]
}`,
      userId: null,
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
      WSData: "",
      nResults: 1000,
      pageSize: 20,
      languages: ["en"],
      queryName: "",
      simultaneousMode: false,
      currentResults: [],
      percentageDone: 0,
      loading: false,
    };
  },
  components: {
    Title,
    KWICTable,
  },
  mounted() {
    if (this.userData) {
      this.userId = this.userData.user.id;
      this.connectToRoom();
      this.stop();
    }
  },
  beforeMount() {
    window.addEventListener("beforeunload", this.sendLeft);
  },
  unmounted() {
    this.sendLeft();
  },
  watch: {
    userData() {
      this.userId = this.userData.user.id;
      this.connectToRoom();
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
    WSData() {
      this.percentageDone = this.WSData.percentage_done;
      if (["finished", "satisfied"].includes(this.WSData.status)){
        this.percentageDone = 100;
      }
      if (this.percentageDone >= 100) {
        this.loading = false;
      }
    },
    selectedCorpora() {
      console.log("EE", this.corpora);
    },
    query() {
      // console.log("Check is valid")
      this.validate();
    },
  },
  methods: {
    sendLeft() {
      this.$socket.sendObj({
        // room: this.roomId,
        room: null,
        action: "left",
        user: this.userId,
      });
    },
    connectToRoom() {
      this.waitForConnection(() => {
        this.$socket.sendObj({
          // room: this.roomId,
          room: null,
          action: "joined",
          user: this.userId,
        });
        this.$socket.onmessage = this.onSocketMessage;
      }, 500);
    },
    waitForConnection(callback, interval) {
      if (this.$socket.readyState === 1) {
        callback();
      } else {
        setTimeout(() => {
          this.waitForConnection(callback, interval);
        }, interval);
      }
    },
    onSocketMessage(event) {
      // this.WSData = event.data
      // the below is just temporary code
      let data = JSON.parse(event.data);
      if (Object.prototype.hasOwnProperty.call(data, "action")) {
        if (data["action"] === "interrupted") {
          console.log("Query interrupted", data);
          return;
        }
        if (data['action'] === 'timeout') {
          console.log('Query job expired', data)
          return
        }
        if (data['action'] === 'validate') {
          // console.log('Query validation', data)
          this.isQueryValidData = data;
          return
        }
        if (data["action"] === "stats") {
          console.log("stats", data);
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
          }
          return;
        }
      }
      // we might need this block for stats related stuff later, don't worry about it much right now
      if (this.simultaneousMode) {
        this.allResults = this.allResults.concat(data['result'])
        if (this.allResults.length >= data['total_results_requested']) {
          this.allResults = this.allResults.slice(0, data['total_results_requested'])
          this.enough(data['simultaneous']);
          data['status'] = 'satisfied';
        }
        data["first_result"] = this.allResults[0];
        data["n_results"] = this.allResults.length;
        delete data["result"];
        data["percentage_done"] += this.percentageDone;
        this.WSData = data;
      } else {
        data["n_results"] = data["result"].length;
        // data["first_result"] = data["result"][0];
        // delete data["result"];
        this.WSData = data;
      }
    },
    submit(event, resumeQuery = false) {
      if (!resumeQuery) {
        this.stop();
        this.WSData = {};
      }
      let data = {
        // corpora: this.selectedCorpora.map((corpus) => corpus.value),
        corpora: this.selectedCorpora.value,
        query: this.query,
        user: this.userId,
        // room: this.roomId,
        room: null,
        page_size: this.pageSize,
        languages: this.languages,
        total_results_requested: this.nResults,
        stats: true,
        resume: resumeQuery,
        simultaneous: this.simultaneousMode
      };
      if (resumeQuery) {
        data["previous"] = this.WSData.job;
      }
      useCorpusStore().fetchQuery(data);
      this.loading = true;
      this.percentageDone = 0.001;
    },
    resume() {
      this.submit(null, true);
    },
    stop() {
      this.currentResults = [];
      this.percentageDone = 0
      this.$socket.sendObj({
        // room: this.roomId,
        room: null,
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
        // room: this.roomId,
        room: null,
        action: "enough_results",
        user: this.userId,
        job: job
      });
    },
    validate() {
      this.$socket.sendObj({
        // room: this.roomId,
        room: null,
        action: "validate",
        user: this.userId,
        query: this.query,
        query_name: this.queryName,
      });
    },
    saveQuery() {
      let data = {
        // corpora: this.selectedCorpora.map((corpus) => corpus.value),
        corpora: this.selectedCorpora.value,
        query: this.query,
        user: this.userId,
        // room: this.roomId,
        room: null,
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
        // room: this.roomId
        room: null,
      };
      useCorpusStore().fetchQueries(data);
    },
    corporaOptions() {
      return this.corpora
        ? this.corpora.map((corpus) => {
            return {
              name: corpus.meta.name,
              value: corpus.meta.id,
            };
          })
        : [];
    },
  },
  computed: {
    ...mapState(useCorpusStore, ["queryData", "corpora"]),
    ...mapState(useUserStore, ["userData", "roomId"]),
    availableLanguages() {
      let retval = []
      if (this.selectedCorpora) {
        if (this.corpora.filter(corpus => corpus.meta.id == this.selectedCorpora.value).length) {
          retval = Object.keys(this.corpora.filter(
            corpus => corpus.meta.id == this.selectedCorpora.value
          )[0].layer).filter(
            key => key.startsWith("Token@")
          ).map(key => key.replace(/Token@/, ''))
          if (retval.length == 0) {
            retval = ["en"]
          }
        }
      }
      return retval
    },
  },
};
</script>
