<template>
  <div id="notifications">
    <div
      class="alert alert-success notification"
      role="alert"
      v-for="(message, index) in messages"
      :key="index"
    >
      {{ message.text }}
    </div>
  </div>
</template>

<style scoped>
#notifications {
  width: 100%;
  margin: auto;
  position: fixed;
  bottom: 1em;
  text-align: center;
  z-index: 100000;
}

.notification {
  width: 50%;
  margin: auto;
  text-align: left;
  margin-top: 7px;
}

small {
  opacity: 0.4;
  margin-top: 3px;
}
</style>

<script>
import { mapState } from "pinia";
import { useNotificationStore } from "@/stores/notificationStore";

export default {
  name: "NotificationsView",
  data() {
    return {
      dismissSecs: 5,
      messages: [],
    };
  },
  computed: {
    ...mapState(useNotificationStore, ["notifications"]),
  },
  watch: {
    notifications: {
      handler() {
        let _notifications = this.notifications;
        if (_notifications.length > 0) {
          _notifications.forEach((element) => {
            this.messages.push({
              ...element,
              show: true,
              dismissCountDown: this.dismissSecs,
            });
            setTimeout(() => this.removeMessages(), 5000)
          });
          useNotificationStore().clear()
        }
      },
      immediate: true,
      deep: true,
    }
  },
  methods: {
    countDownChanged(dismissCountDown, index) {
      this.messages[index].dismissCountDown = dismissCountDown;
    },
    removeMessages() {
      this.messages = []
    }
  },
};
</script>
