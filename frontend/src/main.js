import { createApp } from "vue";
import App from "./App.vue";
import { createPinia } from "pinia";
import router from "./router";
import VueNativeSock from 'vue-native-websocket-vue3'

import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap";

const pinia = createPinia();

createApp(App).use(
  VueNativeSock, 'ws://localhost:9090/ws', {
    reconnection: true,
    reconnectionAttempts: 5,
    format: 'json',
    reconnectionDelay: 1000
}).use(pinia).use(router).mount("#app");
