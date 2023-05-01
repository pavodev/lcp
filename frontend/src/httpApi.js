import axios from "axios";
import config from "@/config";

import { useLoadingStore } from "@/stores/loadingStore";
import { useNotificationStore } from "@/stores/notificationStore";


const httpApi = axios.create({
  baseURL: config.apiUrl,
  headers: {
    "Content-type": "application/json",
    ...config.apiHeaders,
  },
});

axios.interceptors.request.use((axiosConfig) => {
  axiosConfig.headers = config.apiHeaders;
  return axiosConfig;
});

let oldXHR = window.XMLHttpRequest
function newXHR() {
  let realXHR = new oldXHR();
  // store.dispatch('loadingStatus', true)
  useLoadingStore().set(true)
  realXHR.addEventListener("readystatechange", function () {
    if (realXHR.readyState == 4) {
      if (realXHR.status == 0) {
        // Still loading
        // The same error appears when ajax cancel a previous request
        // location.reload()
      }
      else if (realXHR.status == 200) {
        useLoadingStore().set(false)
      }
      else {
        useLoadingStore().set(false)
        useNotificationStore().add({
          type: "error",
          text: `Something went wrong (${realXHR.statusText})`
        })
      }
    }
  }, false)
  return realXHR
}
window.XMLHttpRequest = newXHR

export default httpApi;
