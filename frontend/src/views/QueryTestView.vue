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
                "attribute": "upos",
                "value": "NOUN",
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
      corpora: 'tangram',
      WSData: '',
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
      'user': this.userId
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
      // this.WSData = JSON.parse(event.data)
      this.WSData = event.data
    },
    submit() {
      let data = {
        corpora: this.corpora.split(","),
        query: this.query,
        user: this.userId,
        room: this.roomId
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
