<template>
  <div id="kwic-view">
    <table class="table" v-if="data">
      <thead>
        <tr>
          <!-- <th scope="col">#</th> -->
          <!-- <th scope="col"></th> -->
          <th scope="col" class="header-left">Left context</th>
          <th scope="col" class="header-form">Form</th>
          <th scope="col">Right context</th>
          <!-- <th scope="col">Lemma</th>
          <th scope="col">UPOS</th>
          <th scope="col">POS</th> -->
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, index) in results" :key="index" :data-index="index">
          <td scope="row" class="left-context">
            <span
              class="token"
              v-for="(token, index) in item[0]"
              :key="`lt-${index}`"
              @mousemove="showPopover(token, $event)"
              @mouseleave="closePopover"
            >
              {{ token[1] }}
            </span>
          </td>
          <th
            scope="row"
            class="match-context"
          >
            <span
              class="token"
              v-for="(token, index) in item[1]"
              :key="`lt-${index}`"
              @mousemove="showPopover(token, $event)"
              @mouseleave="closePopover"
            >
              {{ token[1] }}
            </span>
          </th>
          <td scope="row" class="right-context">
            <span
              class="token"
              v-for="(token, index) in item[2]"
              :key="`lt-${index}`"
              @mousemove="showPopover(token, $event)"
              @mouseleave="closePopover"
            >
              {{ token[1] }}
            </span>
          </td>
          <!-- <td>{{ item[1] }}</td>
          <td>{{ item[2] }}</td>
          <td>{{ item[3] }}</td>
          <td>{{ item[4] }}</td> -->
        </tr>
      </tbody>
    </table>
    <div class="popover-liri" v-if="currentToken" :style="{top: popoverY + 'px', left: popoverX + 'px'}">
      {{ currentToken }}
    </div>
  </div>
</template>

<style>
.header-form {
  text-align: center;
}
.header-left {
  text-align: right;
}
.left-context {
  text-align: right;
  overflow: hidden;
  white-space: nowrap;
  max-width: 0;
  direction: rtl;
  width: 40%;
  text-overflow: ellipsis;
}
.right-context {
  white-space: nowrap;
  overflow: hidden;
  white-space: nowrap;
  max-width: 0;
  width: 40%;
  text-overflow: ellipsis;
}
.popover-liri {
  position: fixed;
  background: #cfcfcf;
  padding: 10px;
  border: #cbcbcb 1px solid;
  border-radius: 5px;
}
.match-context {
  white-space: nowrap;
  text-align: center;
}
.token {
  padding-left: 2px;
  padding-right: 2px;
  display: inline-block;
  transition: 0.3s all;
  border-radius: 2px;
}
.token:hover {
  background-color: #1e9899;
  color: #fff;
  cursor: pointer;
}
</style>

<script>
// import { Popover } from "bootstrap/dist/js/bootstrap.esm.min.js";

export default {
  name: "KWICTableView",
  props: ["data"],
  data() {
    return {
      popoverY: 0,
      popoverX: 0,
      currentToken: null,
    }
  },
  // watch: {
  //   data() {
  //     console.log("1231231");
  //     Array.from(
  //       document.querySelectorAll('*[data-bs-toggle="popover"]')
  //     ).forEach((popoverNode) => new Popover(popoverNode));
  //   },
  // },
  methods: {
    showPopover(token, event) {
      // console.log("T", token, event)
      this.popoverY = event.clientY+10;
      this.popoverX = event.clientX+10;
      this.currentToken = token;
    },
    closePopover() {
      this.currentToken = null
      // console.log("Close popover")
    },
  },
  computed: {
    results() {
      return this.data.map((row) => {
        let startIndex = row[2];
        let range = [row[1][0] - startIndex, row[1][1] - startIndex];
        let tokens = row[3];
        return [
          tokens.filter((_, index) => index < range[0]).reverse(),
          tokens.filter((_, index) => index >= range[0] && index <= range[1]),
          // .map((token) => `<span class="show-data" data-id="${token[0]}">${token[1]}</span>`)
          // .join(" "),
          tokens.filter((_, index) => index > range[1]),
          // .map((token) => `<span class="show-data" data-id="${token[0]}">${token[1]}</span>`)
          // .join(" "),
        ];
      });
    },
  },
};
</script>
