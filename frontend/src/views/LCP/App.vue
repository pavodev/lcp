<template>
  <div id="app-content">
    <nav class="navbar navbar-expand-lg bg-liri mb-3">
      <div class="container">
        <a class="navbar-brand" href="#">LCP</a>
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
            <li class="nav-item">
              <router-link class="nav-link" to="/query">
                <FontAwesomeIcon
                  :icon="['fas', 'magnifying-glass']"
                  class="me-1"
                />
                Query
              </router-link>
            </li>
            <!-- <li class="nav-item">
              <router-link class="nav-link" to="/query-test">
                <FontAwesomeIcon :icon="['fas', 'circle-nodes']" class="me-1" />
                Query Test
              </router-link>
            </li> -->
            <!-- <li class="nav-item">
              <router-link class="nav-link" to="/player">
                <FontAwesomeIcon
                  :icon="['fas', 'video']"
                  class="me-1"
                />
                Player
              </router-link>
            </li> -->
          </ul>
          <ul class="navbar-nav ms-auto">
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

import LoadingView from "@/components/LoadingView.vue";
import NotificationView from "@/components/NotificationView.vue";

export default {
  name: "AppLCP",
  mounted() {
    useUserStore().fetchUserData();
    useCorpusStore().fetchCorpora();
  },
  methods: {
    addActionClass(e) {
      e.currentTarget.querySelector(".nav-link").classList.add("active");
    },
  },
  components: {
    LoadingView,
    NotificationView,
  },
  computed: {
    ...mapState(useUserStore, ["userData"]),
  },
};
</script>
