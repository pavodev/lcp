<template>
  <div class="container">
    <header
      class="d-flex flex-wrap justify-content-center py-3 mb-4 border-bottom"
    >
      <a
        href="/"
        class="d-flex align-items-center mb-3 mb-md-0 me-md-auto text-dark text-decoration-none"
      >
        <svg class="bi me-2" width="40" height="32">
          <use xlink:href="#bootstrap"></use>
        </svg>
        <span class="fs-4">uplord</span>
      </a>

      <ul class="nav nav-pills">
        <li class="nav-item" @click="addActionClass">
          <router-link class="nav-link" to="/">Home</router-link>
        </li>
        <li class="nav-item" @click="addActionClass">
          <router-link class="nav-link" to="/query">Query</router-link>
        </li>
        <li class="nav-item" @click="addActionClass">
          <router-link class="nav-link" to="/player">Player</router-link>
        </li>
        <li class="nav-item">
          <router-link class="nav-link" to="/Shibboleth.sso/Logout" v-if="userData && userData.user && userData.user.id"
            >Logout ({{ userData.user.displayName }})</router-link
          >
          <router-link class="nav-link" to="/Shibboleth.sso/Login" v-else
            >Login</router-link
          >
        </li>
      </ul>
    </header>
  </div>
  <router-view />
</template>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
}
</style>

<script>
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";

export default {
  mounted() {
    useUserStore().fetchUserData()
    // useUserStore().fetchCorpuses()
  },
  methods: {
    addActionClass(e){
      e.currentTarget.querySelector('.nav-link').classList.add("active")
    }
  },
  computed: {
    ...mapState(useUserStore, ['userData'])
  }
};
</script>
