import { defineStore } from "pinia";

export const useNotificationStore = defineStore("notificationData", {
  state: () => ({
    notifications: [],
  }),
  getters: {},
  actions: {
    add(message){
      this.notifications.push(message)
    },
    clear(){
      this.notifications = []
    },
  },
});
