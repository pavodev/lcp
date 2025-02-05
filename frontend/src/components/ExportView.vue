<template>
    <div id="exportMonitor" ref="export" v-if="notifs.length > 0">
        <div
            v-for="(notif, n) in notifs"
            class="notif"
            :key="`notif-${n}`"
        >
            {{`[${notif.when}] ${notif.msg}`}}
            <span
              v-if="notif.dl_info && notif.dl_info.status == 'ready'"
              @click="fetch(notif.dl_info)"
              class="download"
            >[ ready ]</span>
            <span v-else>[ {{ notif.dl_info.status }} ]</span>
        </div>
    </div>
  </template>
  

<script>
import { mapState } from "pinia";
// // import { useUserStore } from "@/stores/userStore";
import { useCorpusStore } from "@/stores/corpusStore";
import { useWsStore } from "@/stores/wsStore";

export default {
  name: "ExportView",
  data() {
    return {
        notifs: []
    }
  },
  props: [],
  methods: {
    fetch(info) {
      console.log("fetching", info);
      useCorpusStore().fetchExport(info);
    },
    onSocketMessage(data) {
      const nowStr = new Date().toLocaleString();
      if (data["action"] == "started_export") {
        this.notifs = [{when: nowStr, msg: `Started exporting to ${data.format}`}, ...this.notifs];
      }
      if (data["action"] == "export_link") {
        this.notifs = [{when: nowStr, msg: `Downloading ${data.format} export file`}, ...this.notifs];
      }
      if (data["action"] == "export_notifs") {
        const _notifs = [];
        // eslint-disable-next-line no-unused-vars
        for (let [hash, status, msg, uid, format, offset, requested, delivered, created_at, modified_at] of data.exports) {
          const d = new Date(modified_at).toLocaleString();
          const info = {
            hash: hash,
            format: format,
            offset: offset,
            requested: requested,
            delivered: delivered,
            status: status
          };
          const obj = {when: d, msg: `Exported to ${format}`, dl_info: info};
          const json_obj = JSON.stringify(obj);
          if (_notifs.map(n=>JSON.stringify(n)).includes(json_obj))
            continue
          _notifs.push(obj);
        }
        this.notifs = _notifs;
      }
    }
  },
  computed: {
    ...mapState(useWsStore, ["messages"]),
  },
  watch: {
    messages: {
      handler() {
        let _messages = this.messages;
        if (_messages.length > 0) {
          _messages.forEach(message => this.onSocketMessage(message))
        }
      },
      immediate: true,
      deep: true,
    },
  },
  mounted() {
    // pass
  },
  beforeUnmount() {
    // pass
  }
}
</script>

<style scoped>
#exportMonitor {
  position: absolute;
  background-color: cornsilk;
  padding: 0.5em;
  border-radius: 0.5em;
  box-shadow: 1px 1px 8px black;
  display: none;
  flex-direction: column;
}
#exportMonitor:hover {
  display: flex;
}
span.download {
  cursor: pointer;
  text-decoration: underline;
}
</style>