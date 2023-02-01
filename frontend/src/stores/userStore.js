import { defineStore } from "pinia";
import httpApi from "@/httpApi";
import Utils from '@/utils';

export const useUserStore = defineStore("userData", {
  state: () => ({
    userData: null,
    corpora: [],
    roomId: Utils.uuidv4(),
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
