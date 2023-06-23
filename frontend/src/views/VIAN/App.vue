<template>
  <div id="app-content">
    <nav class="navbar navbar-expand-lg bg-liri mb-3 fixed-top">
      <div class="container">
        <a class="navbar-brand" href="/">VIAN-DH</a>
        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarNav"
          aria-controls="navbarNav"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav">
            <li class="nav-item">
              <router-link class="nav-link" to="/">
                <FontAwesomeIcon :icon="['fas', 'house']" class="me-1" />
                Home
              </router-link>
            </li>
            <!-- <li class="nav-item">
              <router-link class="nav-link" to="/query">
                <FontAwesomeIcon
                  :icon="['fas', 'magnifying-glass']"
                  class="me-1"
                />
                Query
              </router-link>
            </li> -->
            <!-- <li class="nav-item">
              <router-link class="nav-link" to="/query-test">
                <FontAwesomeIcon :icon="['fas', 'circle-nodes']" class="me-1" />
                Query Test
              </router-link>
            </li> -->
            <li class="nav-item">
              <router-link class="nav-link" to="/player">
                <FontAwesomeIcon
                  :icon="['fas', 'video']"
                  class="me-1"
                />
                Viewer
              </router-link>
            </li>
          </ul>
          <ul class="navbar-nav ms-auto">
            <li class="nav-item">
              <span class="nav-link version-number">
                #{{ appVersion }}
              </span>
            </li>
            <li class="nav-item">
              <router-link
                class="nav-link"
                to="/Shibboleth.sso/Logout"
                v-if="userData && userData.user && userData.user.id"
              >
                <FontAwesomeIcon :icon="['fas', 'power-off']" class="me-1" />
                Logout <small>({{ userData.user.displayName }})</small>
              </router-link>
              <router-link class="nav-link" to="/Shibboleth.sso/Login" v-else>
                <FontAwesomeIcon :icon="['fas', 'user']" class="me-1" />
                Login
              </router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    <router-view />
    <NotificationView />
    <LoadingView />
  </div>
</template>

<script>
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";
import { useCorpusStore } from "@/stores/corpusStore";
import { useWsStore } from "@/stores/wsStore";

import LoadingView from "@/components/LoadingView.vue";
import NotificationView from "@/components/NotificationView.vue";

export default {
  name: "AppVIAN",
  data() {
    return {
      appVersion: process.env.GIT_HASH,
    }
  },
  mounted() {
    useUserStore().fetchUserData();
    useCorpusStore().fetchCorpora();
  },
  unmounted() {
    this.sendLeft();
  },
  methods: {
    addActionClass(e) {
      e.currentTarget.querySelector(".nav-link").classList.add("active");
    },
    sendLeft() {
      this.$socket.sendObj({
        room: this.roomId,
        action: "left",
        user: this.userData.user.id,
      });
      console.log("Left WS")
    },
    waitForConnection(callback, interval) {
      if (this.$socket.readyState === 1) {
        callback();
      } else {
        setTimeout(() => {
          this.waitForConnection(callback, interval);
        }, interval);
      }
    },
    connectToRoom() {
      console.log("Connect to WS room", this.$socket.readyState, this.roomId, this.userData.user.id)
      // if (this.$socket.readyState != 1){
      // console.log("Connect to WS")
      this.waitForConnection(() => {
        this.$socket.sendObj({
          room: this.roomId,
          action: "joined",
          user: this.userData.user.id,
        });
        this.$socket.onmessage = this.onSocketMessage;
        this.$socket.onclose = (e) => {
          console.log('Socket is closed. Reconnect will be attempted in 1 second.', e.reason);
          setTimeout(() => {
            this.connectToRoom();
          }, 1000);
        };
        this.$socket.onerror = (err) => {
          console.error('Socket encountered error: ', err.message, 'Closing socket');
          this.$socket.close();
        };
        console.log("Connected to WS")
      }, 500);
      // }
    },
    onSocketMessage(event) {
      let data = JSON.parse(event.data);
      console.log("Rec", data)
      useWsStore().add(data)
    }
  },
  components: {
    LoadingView,
    NotificationView,
  },
  computed: {
    ...mapState(useUserStore, ["userData", "roomId"]),
  },
  watch: {
    userData() {
      this.connectToRoom();
    },
  },
};
</script>

<style scoped>
.version-number {
  font-size: 80% !important;
  opacity: 0.75;
  margin-top: 2px;
}
</style>
