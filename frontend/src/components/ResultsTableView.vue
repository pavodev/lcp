<template>
  <div id="kwic-view">
    <table class="table" v-if="data">
      <thead>
        <tr>
          <th scope="col" class="header-left">Left context</th>
          <th scope="col" class="header-form">Form</th>
          <th scope="col">Right context</th>
          <th scope="col">-</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(item, resultIndex) in results"
          :key="resultIndex"
          :data-index="resultIndex"
        >
          <td scope="row" class="left-context">
            <span
              class="token"
              v-for="(token, index) in item[0]"
              :key="`lt-${index}`"
              @mousemove="showPopover(token, resultIndex, $event)"
              @mouseleave="closePopover"
            >
              {{ token[0] }}
            </span>
          </td>
          <th scope="row" class="match-context">
            <span
              class="token"
              v-for="(token, index) in item[1]"
              :key="`lt-${index}`"
              @mousemove="showPopover(token, resultIndex, $event)"
              @mouseleave="closePopover"
            >
              {{ token[0] }}
            </span>
          </th>
          <td scope="row" class="right-context">
            <span
              class="token"
              v-for="(token, index) in item[2]"
              :key="`lt-${index}`"
              @mousemove="showPopover(token, resultIndex, $event)"
              @mouseleave="closePopover"
            >
              {{ token[0] }}
            </span>
          </td>
          <td>
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              data-bs-toggle="modal"
              data-bs-target="#detailsModal"
              @click="showModal(resultIndex)"
            >
              Details
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <PaginationComponent
      :resultCount="data.length"
      :resultsPerPage="resultsPerPage"
      :currentPage="currentPage"
      @update="updatePage"
      :key="data.length"
      :loading="loading"
    />
    <div
      class="popover-liri"
      v-if="currentToken"
      :style="{ top: popoverY + 'px', left: popoverX + 'px' }"
    >
      <table class="table">
        <thead>
          <tr>
            <th v-for="(item, index) in columnHeaders" :key="`th-${index}`">
              {{ item }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td v-for="(item, index) in columnHeaders" :key="`tr-${index}`">
              <span v-if="item == 'head'" v-html="headToken"> </span>
              <span
                v-else
                :class="
                  item.indexOf('pos') > -1
                    ? 'badge rounded-pill bg-secondary'
                    : ''
                "
                v-html="currentToken[index]"
              ></span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div
      class="modal fade"
      id="detailsModal"
      tabindex="-1"
      aria-labelledby="detailsModalLabel"
      aria-hidden="true"
    >
      <div class="modal-dialog modal-full">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="detailsModalLabel">Details</h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body text-start">
            <div class="modal-body-content">
              <ResultDetailsModalView
                :data="data[modalIndex]"
                :corpora="corpora"
                :key="modalIndex"
                v-if="modalVisible"
              />
            </div>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              Close
            </button>
          </div>
        </div>
      </div>
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
  z-index: 200;
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
import ResultDetailsModalView from "@/components/ResultDetailsModalView.vue";
import PaginationComponent from "@/components/PaginationComponent.vue";

export default {
  name: "ResultsTableView",
  props: ["data", "corpora", "resultsPerPage", "loading"],
  data() {
    return {
      popoverY: 0,
      popoverX: 0,
      currentToken: null,
      currentIndex: null,
      modalVisible: false,
      modalIndex: null,
      currentPage: 1,
    };
  },
  components: {
    ResultDetailsModalView,
    PaginationComponent,
  },
  methods: {
    showPopover(token, index, event) {
      this.popoverY = event.clientY + 10;
      this.popoverX = event.clientX + 10;
      this.currentToken = token;
      this.currentIndex = index + ((this.currentPage - 1)*this.resultsPerPage);
    },
    closePopover() {
      this.currentToken = null;
      this.currentIndex = null;
    },
    showModal(index) {
      this.modalIndex = index;
      this.modalVisible = true;
    },
    updatePage(currentPage) {
      this.currentPage = currentPage;
      this.$emit("updatePage", this.currentPage);
    },
  },
  computed: {
    headToken() {
      let token = "-";
      let headIndex = this.columnHeaders.indexOf("head");
      let lemmaIndex = this.columnHeaders.indexOf("lemma");
      if (headIndex) {
        let tokenId = this.currentToken[headIndex];
        if (tokenId) {
          let startId = this.data[this.currentIndex][2];
          let tokenIndexInList = tokenId - startId;
          token = this.data[this.currentIndex][3][tokenIndexInList][lemmaIndex];
        }
      }
      return token;
    },
    results() {
      return this.data
        .filter((row, rowIndex) => {
          let start = this.resultsPerPage * (this.currentPage - 1);
          let end = start + this.resultsPerPage;
          return rowIndex >= start && rowIndex < end;
        })
        .map((row, rowIndex) => {
          let startIndex = row[2];
          let range = [row[1][0] - startIndex, row[1][1] - startIndex];
          let tokens = row[3];
          return [
            tokens.filter((_, index) => index < range[0]).reverse(),
            tokens.filter((_, index) => index >= range[0] && index <= range[1]),
            tokens.filter((_, index) => index > range[1]),
            rowIndex,
          ];
        });
    },
    columnHeaders() {
      let partitions = this.corpora.corpus.partitions
        ? this.corpora.corpus.partitions.values
        : [];
      let columns = this.corpora.corpus["mapping"]["layer"]["Segment"];
      if (partitions.length) {
        columns = columns["partitions"][partitions[0]];
      }
      return columns["prepared"]["columnHeaders"];
    },
  },
};
</script>
