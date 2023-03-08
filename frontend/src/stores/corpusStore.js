import { defineStore } from "pinia";
import httpApi from "@/httpApi";

export const useCorpusStore = defineStore("corpusData", {
  state: () => ({
    queryData: null,
  }),
  getters: {},
  actions: {
    fetchQuery(data) {
      httpApi.post(`/query`, data).then((r) => {
        this.queryData = r.data;
        return r.data;
      });
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
  },
});
