import { createApp } from "vue";
import App from "./App.vue";
import { createPinia } from "pinia";
import router from "./router";
import FontAwesomeIcon from '@/fontawesome';
import VueNativeSock from 'vue-native-websocket-vue3'
import Multiselect from 'vue-multiselect';
import config from "@/config";
import Vue3Mermaid from "vue3-mermaid";

import "vue-multiselect/dist/vue-multiselect.css";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap";
import "@/assets/style.css";
import "@/assets/multiselect.css";

const pinia = createPinia();

createApp(App).use(
  VueNativeSock, config.wsUrl, {
    reconnection: true,
    reconnectionAttempts: 5,
    format: 'json',
    reconnectionDelay: 1000
})
  .component('multiselect', Multiselect)
  .component('FontAwesomeIcon', FontAwesomeIcon)
  .use(pinia)
  .use(router)
  .use(Vue3Mermaid)
  .mount("#app");
