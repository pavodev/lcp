import { defineStore } from "pinia";

export const useWsStore = defineStore("wsData", {
  state: () => ({
    messages: [],
  }),
  getters: {},
  actions: {
    add(message) {
      this.messages.push(message)
    },
    clear() {
      this.messages = []
    },
  },
});
