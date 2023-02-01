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
  },
});
