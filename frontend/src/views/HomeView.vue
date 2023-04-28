<template>
  <div class="home">
    <Title :title="'Welcome to LCP'" />
    <div class="container mt-4 text-start">
      <div class="row">
        <!-- <p>Select corpora to query:</p> -->
        <div
          class="col-4 mb-3"
          v-for="corpus in corpora"
          :key="corpus.id"
          @click="openCorpus(corpus)"
          data-bs-toggle="modal"
          data-bs-target="#corpusDetailsModal"
        >
          <div class="corpus-block">
            <p class="title mb-0">{{ corpus.meta.name }}</p>
            <p class="author mb-0" v-if="corpus.meta.author">
              by {{ corpus.meta.author }}
            </p>
            <p class="description mt-3">{{ corpus.meta.corpusDescription }}</p>
            <p class="word-count mb-0">
              Word count:
              <b>{{
                nFormatter(calculateSum(Object.values(corpus.token_counts)))
              }}</b>
            </p>
            <p class="word-count">
              Version: <b>{{ corpus.meta.version }}</b>
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <div
      class="modal fade"
      id="corpusDetailsModal"
      tabindex="-1"
      aria-labelledby="corpusDetailsModalLabel"
      aria-hidden="true"
      ref="vuemodal"
    >
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="corpusDetailsModalLabel">
              Corpus details
            </h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body text-start" v-if="corpusModal">
            <div class="row">
              <div class="col-5">
                <p class="title mb-0">{{ corpusModal.meta.name }}</p>
                <p class="author mb-0" v-if="corpusModal.meta.author">
                  by {{ corpusModal.meta.author }}
                </p>
                <p class="description mt-3">
                  {{ corpusModal.meta.corpusDescription }}
                </p>
                <p class="word-count mb-0">
                  Word count:
                  <b>{{
                    calculateSum(
                      Object.values(corpusModal.token_counts)
                    ).toLocaleString("de-DE")
                  }}</b>
                </p>
                <p class="word-count mb-0">
                  Version: {{ corpusModal.meta.version }}
                </p>
                <p class="word-count mb-0">
                  Description: {{ corpusModal.description }}
                </p>
                <span v-if="corpusModal.partitions">
                  <p class="word-count" v-if="corpusModal.partitions">
                    Partitions: {{ corpusModal.partitions.values.join(", ") }}
                  </p>
                  <div
                    class=""
                    v-for="partition in corpusModal.partitions.values"
                    :key="partition"
                  >
                    <p class="text-bold">{{ partition.toUpperCase() }}</p>
                    <p class="word-count">
                      Segments:
                      {{
                        corpusModal.mapping.layer.Segment.partitions[
                          partition
                        ].prepared.columnHeaders.join(", ")
                      }}
                    </p>
                    <!-- <p class="word-count">
                      Segments:
                      {{ corpusModal.mapping.layer.Segment.partitions[partition].prepared.columnHeaders.join(", ") }}
                    </p> -->
                  </div>
                </span>
              </div>
              <div class="col-7">
                <vue3-mermaid
                  v-if="showGraph"
                  :nodes="graphData"
                  type="graph TD"
                  :config="config"
                  :key="graphIndex"
                ></vue3-mermaid>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapState } from "pinia";
import { useCorpusStore } from "@/stores/corpusStore";

import Title from "@/components/TitleComponent.vue";
import Utils from "@/utils";

export default {
  name: "HomeView",
  data() {
    return {
      corpusModal: null,
      graphIndex: 0,
      showGraph: false,
      config: {
        theme: "neutral",
      },
    };
  },
  components: {
    Title,
  },
  methods: {
    openCorpus(corpus) {
      this.corpusModal = corpus;
    },
    calculateSum(array) {
      return array.reduce((accumulator, value) => {
        return accumulator + value;
      }, 0);
    },
    nFormatter: Utils.nFormatter,
  },
  computed: {
    ...mapState(useCorpusStore, ["queryData", "corpora"]),
    graphData() {
      let corpus = this.corpusModal;
      let data = [
        {
          id: "1",
          text: corpus.meta.name.replace(/\(/gi, "") .replace(/\)/gi, ""),
          next: Object.keys(corpus.layer).map((layer) => `l-${layer.toLowerCase().replace(/@/gi, "")}`),
        },
      ];
      Object.keys(corpus.layer).forEach((layer, index) => {
        let next = [];
        if ("attributes" in corpus.layer[layer]) {
          Object.keys(corpus.layer[layer].attributes).forEach((attribute) => {
            let attributeId = `a-${index}-${attribute.toLowerCase()}`;
            data.push({
              id: attributeId,
              text: attribute.replace(/@/gi, ""),
              edgeType: "circle",
            });
            next.push(attributeId);
          });
        }
        if ("meta" in corpus.layer[layer]) {
          Object.keys(corpus.layer[layer].meta).forEach((meta) => {
            let metaId = `a-${index}-${meta.toLowerCase()}`;
            data.push({
              id: metaId,
              text: meta.replace(/@/gi, ""),
              edgeType: "circle",
            });
            next.push(metaId);
          });
        }
        data.push({
          id: `l-${layer.toLowerCase().replace(/@/gi, "")}`,
          text: layer.replace(/@/gi, ""),
          next: next,
        });
      });
      return data;
    },
  },
  mounted() {
    this.$refs.vuemodal.addEventListener("shown.bs.modal", () => {
      this.showGraph = true
    });
    this.$refs.vuemodal.addEventListener("hide.bs.modal", () => {
      this.showGraph = false
    });
  },
};
</script>

<style scoped>
.corpus-block {
  border: 1px solid #d4d4d4;
  border-radius: 5px;
  padding: 20px;
  cursor: pointer;
}
.author {
  font-size: 70%;
}
.corpus-block:hover {
  background-color: #f3f3f3;
}
.title {
  font-size: 110%;
  font-weight: bold;
}
.description {
  font-size: 90%;
}
.word-count {
  font-size: 80%;
}
</style>
