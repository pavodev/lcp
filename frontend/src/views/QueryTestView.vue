<template>
  <div class="query">
    <h1>Query test</h1>
    <div class="container mt-4">
      <div class="row">
        <div class="col">
          <form>
            <div class="form-floating mb-3">
              <textarea class="form-control query-field" placeholder="Query (e.g. test.*)" v-model="query"></textarea>
              <label for="floatingTextarea">Query</label>
            </div>
            <div class="mb-3">
              <label for="exampleInputEmail1" class="form-label">Corpora (split by comma)</label>
              <input type="text" class="form-control" v-model="corpora">
            </div>
            <div class="mb-3">
              <label for="exampleInputEmail1" class="form-label">Room</label>
              <input type="text" class="form-control" v-model="roomId" disabled>
            </div>
            <div class="mb-3">
              <label for="exampleInputEmail1" class="form-label">User</label>
              <input type="text" class="form-control" v-model="userId" disabled>
            </div>
            <div class="mb-3">
              <label for="exampleInputEmail1" class="form-label">Number of results</label>
              <input type="number" class="form-control" v-model="nResults">
            </div>
            <div class="mb-3">
              <label for="exampleInputEmail1" class="form-label">Languages (split by comma)</label>
              <input type="text" class="form-control" v-model="languages">
            </div>
            <button type="button" @click="submit" class="btn btn-primary">Submit</button>
          </form>
        </div>
        <div class="col">
          <h6>Query submit result</h6>
          <div v-html="JSON.stringify(queryData)" v-if="queryData" class="pre"></div>
          <h6 class="mt-4">Query result (WS)</h6>
          <div v-html="WSData" class="pre"></div>
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
  font-family: 'Courier New', Courier, monospace;
}
.query-field {
  height: 300px;
}
</style>

<script>
import { mapState } from "pinia";
import { useCorpusStore } from "@/stores/corpusStore";
import { useUserStore } from "@/stores/userStore";

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
      corpora: '2',
      WSData: '',
      nResults: 10000,
      pageSize: 20,
      languages: 'en'
    }
  },
  mounted() {
    if (this.userData) {
      this.userId = this.userData.user.id;
      this.connectToRoom();
    }
  },
  unmounted() {
    this.$socket.sendObj({
      'room': this.roomId,
      'action': 'left',
      'user': this.userId,
    })
  },
  watch: {
    userData() {
      this.userId = this.userData.user.id;
      this.connectToRoom();
    }
  },
  methods: {
    connectToRoom(){
      this.waitForConnection(() => {
        this.$socket.sendObj({
          'room': this.roomId,
          'action': 'joined',
          'user': this.userId
        })
        this.$socket.onmessage = this.onSocketMessage
      }, 500)
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
      let data = JSON.parse(event.data)
      data['n_results'] = data['result'].length
      data['first_result'] = data['result'][0]
      delete data['result']
      this.WSData = JSON.stringify(data, null, 1)
    },
    submit() {
      let data = {
        corpora: this.corpora.split(','),
        query: this.query,
        user: this.userId,
        room: this.roomId,
        page_size: this.pageSize,
        languages: this.languages.split(','),
        total_results_requested: this.nResults
      }
      useCorpusStore().fetchQuery(data)
    }
  },
  computed: {
    ...mapState(useCorpusStore, ['queryData']),
    ...mapState(useUserStore, ['userData', 'roomId']),
  }
};
</script>
