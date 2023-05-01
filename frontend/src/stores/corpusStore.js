import { defineStore } from "pinia";
import httpApi from "@/httpApi";

export const useCorpusStore = defineStore("corpusData", {
  state: () => ({
    queryData: null,
    corpora: [],
  }),
  getters: {},
  actions: {
    async fetchQuery(data) {
      let r = await httpApi.post(`/query`, data)
      this.queryData = await r.data;
      return this.queryData
    },
    saveQuery(data) {
      httpApi.post(`/store`, data).then((r) => {
        return r.data;
      });
    },
    fetchQueries(data) {
      httpApi.post(`/fetch`, data).then((r) => {
        this.fetchedQueries = r.data;
        return r.data;
      });
    },
    fetchCorpora(data) {
      httpApi.post(`/corpora`, data).then((r) => {
        this.corporaJson = r.data;
        delete this.corporaJson.config["-1"]
        this.corpora = Object.keys(this.corporaJson.config).map(corpusId => {
          let corpus = this.corporaJson.config[corpusId]
          corpus.meta['id'] = corpusId
          return corpus
        })
      });
    }
  },
});
