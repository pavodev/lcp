import { createApp } from "vue";
import App from "./App.vue";
import { createPinia } from "pinia";
import router from "./router";
import FontAwesomeIcon from '@/fontawesome';
import VueNativeSock from 'vue-native-websocket-vue3'
import Multiselect from 'vue-multiselect';

import "vue-multiselect/dist/vue-multiselect.css";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap";
import "@/assets/style.css";
import "@/assets/multiselect.css";

const pinia = createPinia();

createApp(App).use(
  VueNativeSock, 'ws://localhost:9090/ws', {
    reconnection: true,
    reconnectionAttempts: 5,
    format: 'json',
    reconnectionDelay: 1000
})
  .component('multiselect', Multiselect)
  .component('FontAwesomeIcon', FontAwesomeIcon)
  .use(pinia)
  .use(router)
  .mount("#app");
