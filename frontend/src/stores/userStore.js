import { defineStore } from "pinia";
import httpApi from "@/httpApi";
import Utils from '@/utils';

// Get roomId from localStorage
let roomId = localStorage.getItem("roomId");
if (!roomId) {
  roomId = Utils.uuidv4()
  localStorage.setItem("roomId", roomId);
}
roomId = Utils.uuidv4()

export const useUserStore = defineStore("userData", {
  state: () => ({
    userData: null,
    roomId: roomId,
    projects: [],
  }),
  getters: {},
  actions: {
    fetchUserData() {
      httpApi.get(`/settings`).then((r) => {
        this.userData = r.data;
        if (this.userData.publicProfiles.length) {
          this.projects = this.userData.publicProfiles
        }
        this.userData.subscription.subscriptions.forEach(subscription => {
          subscription.profiles.forEach(profile => {
            this.projects.push(profile)
          })
        })

        // Terms of use
        if (this.userData.termsOfUse.needToAccept === true) {
          window.location.href = this.userData.termsOfUse.url;
        }
      });
    },
  },
});
