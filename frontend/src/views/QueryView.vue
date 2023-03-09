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
              v-model="query"
            ></textarea>
            <label for="floatingTextarea">Query</label>
          </div>
        </div>
        <div class="col-6">
          <div class="mb-3">
            <label for="exampleInputEmail1" class="form-label"
              >Corpora (split by comma)</label
            >
            <multiselect
              v-model="selectedCorpora"
              :options="corporaOptions()"
              :multiple="true"
              label="name"
              track-by="value"
              :allow-empty="false"
            ></multiselect>
            <!-- <input type="text" class="form-control" v-model="corpora" /> -->
          </div>
          <div class="mb-3">
            <label for="exampleInputEmail1" class="form-label">Room</label>
            <input
              type="text"
              class="form-control"
              disabled
            />
          </div>
          <div class="mb-3">
            <label for="exampleInputEmail1" class="form-label">Query name</label>
            <input
              type="text"
              class="form-control"
              v-model="queryName"
            />
          </div>
          <div class="mb-3">
            <label for="exampleInputEmail1" class="form-label">User</label>
            <input
              type="text"
              class="form-control"
              v-model="userId"
              disabled
            />
          </div>
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
                <input type="text" class="form-control" v-model="languages" />
              </div>
            </div>
          </div>
        </div>
        <div class="col-12">
          <button type="button" @click="submit" class="btn btn-primary" :disabled="selectedCorpora.length == 0">
            Submit
          </button>
          <button type="button" @click="save" :disabled="!queryName" class="btn btn-primary">Save</button>
          <button type="button" @click="fetch" class="btn btn-primary">Fetch</button>

        </div>
        <div class="col">
          <hr class="mt-5 mb-5">
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
              :class="WSData.percentage_done < 100 ? 'progress-bar-striped progress-bar-animated' : ''"
              role="progressbar"
              aria-label="Basic example"
              :style="`width: ${WSData.percentage_done}%`"
              :aria-valuenow="WSData.percentage_done"
              aria-valuemin="0"
              aria-valuemax="100"
            >{{ WSData.percentage_done }}</div>
          </div>
          <div class="row">
            <div class="col">
              <p class="mb-1">Number of results: <span class="text-bold" v-html="WSData.n_results"></span></p>
            </div>
            <div class="col">
              <p class="mb-1">Projected results: <span class="text-bold" v-html="WSData.projected_results"></span></p>
            </div>
            <div class="col">
              <p class="mb-1">Batch done: <span class="text-bold" v-html="WSData.batches_done"></span></p>
            </div>
            <div class="col">
              <p class="mb-1">Status: <span class="text-bold" v-html="WSData.status"></span></p>
            </div>
          </div>
          <h6 class="mt-4 mb-3">Results:</h6>
          <table class="table" v-if="WSData && WSData.first_result">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Form</th>
                <th scope="col">Lemma</th>
                <th scope="col">UPOS</th>
                <th scope="col">POS</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in WSData.first_result[2]" :key="index">
                <th scope="row">{{ item[0] }}</th>
                <td>{{ item[1] }}</td>
                <td>{{ item[2] }}</td>
                <td>{{ item[3] }}</td>
                <td>{{ item[4] }}</td>
              </tr>
            </tbody>
          </table>
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
}
</style>

<script>
import { mapState } from "pinia";
import { useCorpusStore } from "@/stores/corpusStore";
import { useUserStore } from "@/stores/userStore";
import Title from "@/components/TitleComponent.vue";

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
      selectedCorpora: this.corpora ? this.corpora.filter(corpus => corpus.meta.id == 2).map(corpus => {
        return {
          "name": corpus.meta.name,
          "value": corpus.meta.id,
        }
      }) : [],
      WSData: "",
      nResults: 1000,
      pageSize: 20,
      languages: "en",
      queryName: ""
    };
  },
  components: {
    Title,
  },
  mounted() {
    if (this.userData) {
      this.userId = this.userData.user.id;
      this.connectToRoom();
    }
  },
  beforeMount() {
    window.addEventListener("beforeunload", this.sendLeft)
  },
  unmounted() {
    this.sendLeft()
  },
  watch: {
    userData() {
      this.userId = this.userData.user.id;
      this.connectToRoom();
    },
    corpora() {
      this.selectedCorpora = this.corpora && this.selectedCorpora.length == 0 ? this.corpora.filter(corpus => corpus.meta.id == 2).map(corpus => {
        return {
          "name": corpus.meta.name,
          "value": corpus.meta.id,
        }
      }) : []
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
      if (Object.prototype.hasOwnProperty.call(data, 'action')) {
        if (data['action'] === 'fetch_queries') {
          console.log('do something here with the fetched queries?', data)
          return
        } else if (data['action'] === 'store_query') {
          console.log('query stored', data)
          return
        }
      }
      data["n_results"] = data["result"].length;
      data["first_result"] = data["result"][0];
      delete data["result"];
      this.WSData = data;
    },
    submit() {
      let data = {
        corpora: this.selectedCorpora.map(corpus => corpus.value),
        query: this.query,
        user: this.userId,
        // room: this.roomId,
        room: null,
        page_size: this.pageSize,
        languages: this.languages.split(","),
        total_results_requested: this.nResults,
      };
      useCorpusStore().fetchQuery(data);
    },
    save() {
      let data = {
        corpora: this.selectedCorpora.map(corpus => corpus.value),
        query: this.query,
        user: this.userId,
        // room: this.roomId,
        room: null,
        page_size: this.pageSize,
        languages: this.languages.split(','),
        total_results_requested: this.nResults,
        query_name: this.queryName
      }
      useCorpusStore().saveQuery(data)
    },
    fetch() {
      let data = {
        user: this.userId,
        // room: this.roomId
        room: null
      }
      useCorpusStore().fetchQueries(data)
    },
    corporaOptions() {
      return this.corpora ? this.corpora.map(corpus => {
        return {
          "name": corpus.meta.name,
          "value": corpus.meta.id,
        }
      }) : []
    },
  },
  computed: {
    ...mapState(useCorpusStore, ["queryData", "corpora"]),
    ...mapState(useUserStore, ["userData", "roomId"]),
  },
};
</script>
