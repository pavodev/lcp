<template>
  <div class="query">
    <div class="container-fluid mt-4 px-4">
      <div class="row">
        <div class="col">
          <Title :title="`User profile${ userData && userData.user && userData.user.displayName ?  ' - ' + userData.user.displayName : ''}`" />
        </div>
      </div>
      <div class="row mt-2">
      </div>
      <div class="row mt-5">
      </div>
    </div>
  </div>
</template>

<style scoped></style>

<script>
import { mapState } from "pinia";

// Components
import Title from "@/components/TitleComponent.vue";

// Stores
import { useUserStore } from "@/stores/userStore";

export default {
  name: "UserView",
  data() {
    return {
    };
  },
  components: {
    Title,
  },
  watch: {
  },
  methods: {
  },
  computed: {
    ...mapState(useUserStore, ["userData"]),
  },
  mounted() {
    useUserStore().fetchUserData();
    // this.fetch(); // Retrieve the saved queries
  },
  beforeUnmount() {
  },
};
</script>
