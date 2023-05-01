import { defineStore } from "pinia";

export const useLoadingStore = defineStore("loadingData", {
  state: () => ({
    status: false,
  }),
  getters: {},
  actions: {
    start() {
      this.status = true
    },
    stop() {
      this.status = false
    },
    set(value) {
      this.status = value
    },
  },
});
