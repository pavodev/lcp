import { defineStore } from "pinia";
import httpApi from "@/httpApi";

export const useCorpusStore = defineStore("corpusData", {
  state: () => ({
    queryData: null,
    corpora: [],
    vianCorpus: [],
  }),
  getters: {},
  actions: {
    async fetchQuery(data) {
      let response = await httpApi.post(`/query`, data)
      this.queryData = await response.data;
      return this.queryData
    },
    saveQuery(data) {
      httpApi.post(`/store`, data).then((response) => {
        return response.data;
      });
    },
    fetchQueries(data) {
      httpApi.post(`/fetch`, data).then((response) => {
        this.fetchedQueries = response.data;
        return response.data;
      });
    },
    fetchCorpora() {
      httpApi.post(`/corpora`).then((response) => {
        this.corporaJson = response.data;
        delete this.corporaJson.config["-1"]
        this.corpora = Object.keys(this.corporaJson.config).map(corpusId => {
          let corpus = this.corporaJson.config[corpusId]
          corpus.meta['id'] = corpusId
          return corpus
        })
      });
    },
    fetchDocuments(data) {
      httpApi.post(`/document_ids/${data.corpora_id}`, data).then((response) => {
        return response.data;
      });
    },
    fetchDocument(data) {
      httpApi.post(`/document/${data.doc_id}`, data).then((response) => {
        return response.data;
      });
    },
  },
});
