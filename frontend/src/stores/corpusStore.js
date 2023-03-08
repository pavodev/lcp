import { defineStore } from "pinia";
import httpApi from "@/httpApi";

export const useCorpusStore = defineStore("corpusData", {
  state: () => ({
    queryData: null,
    corporaJson: null,
    corpora: [],
  }),
  getters: {},
  actions: {
    fetchQuery(data) {
      httpApi.post(`/query`, data).then((r) => {
        this.queryData = r.data;
        return r.data;
      });
    },
    fetchCorpora(data) {
      httpApi.post(`/corpora`, data).then((r) => {
        this.corporaJson = r.data;
        this.corpora = Object.keys(this.corporaJson.config).map(corpusId => {
          let corpus = this.corporaJson.config[corpusId]
          corpus.meta['id'] = corpusId
          return corpus
        })
        return r.data;
      });
    },
  },
});
