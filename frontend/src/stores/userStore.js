import { defineStore } from "pinia";
import httpApi from "@/httpApi";
import Utils from '@/utils';

// Get roomId from localStorage
let roomId = localStorage.getItem("roomId");
if (!roomId) {
  roomId = Utils.uuidv4()
  localStorage.setItem("roomId", roomId);
}

export const useUserStore = defineStore("userData", {
  state: () => ({
    userData: null,
    roomId: roomId,
  }),
  getters: {},
  actions: {
    fetchUserData() {
      httpApi.get(`/settings`).then((r) => {
        this.userData = r.data;

        // Terms of use
        if (this.userData.termsOfUse.needToAccept === true) {
          window.location.href = this.userData.termsOfUse.url;
        }
      });
    },
  },
});
