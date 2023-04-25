<template>
  <div id="kwic-view">
    <table class="table" v-if="data">
      <thead>
        <tr>
          <th scope="col" v-for="(col, index) in attributes" :key="index">
            {{ col.name }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(item, resultIndex) in data"
          :key="resultIndex"
          :data-index="resultIndex"
        >
          <td
            scope="row"
            v-for="(col, index) in attributes"
            :key="index"
          >
            {{ item[index] }}
          </td>
        </tr>
      </tbody>
    </table>
    <PaginationComponent
      :resultCount="data ? data.length : 0"
      :resultsPerPage="resultsPerPage"
      :currentPage="currentPage"
      @update="updatePage"
      :key="data ? data.length : 0"
      :loading="loading"
    />
  </div>
</template>

<style>
.header-form {
  text-align: center;
}
.header-left {
  text-align: right;
}
table {
  text-align: left;
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
  text-align: left;
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
.highlight {
  background-color: #1e999967;
}
</style>

<script>
import PaginationComponent from "@/components/PaginationComponent.vue";

export default {
  name: "ResultsTableView",
  props: ["data", "attributes", "corpora", "resultsPerPage", "loading"],
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
    PaginationComponent,
  },
  methods: {
    updatePage(currentPage) {
      this.currentPage = currentPage;
      this.$emit("updatePage", this.currentPage);
    },
    bgCheck (resultIndex, tokenIndex, range, type) {
      let classes = []
      resultIndex = resultIndex + ((this.currentPage - 1)*this.resultsPerPage)
      if (this.currentIndex == resultIndex) {
        let headIndex = this.columnHeaders.indexOf("head");
        let currentTokenHeadId = this.currentToken[headIndex];
        let startId = this.data[this.currentIndex][2];
        let tokenId
        if (type == 1) {
          tokenId = range[0] - tokenIndex + startId - 1
        }
        else if (type == 2) {
          tokenId = range[0] + tokenIndex + startId
        }
        else if (type == 3) {
          tokenId = range[1] + tokenIndex + startId + 1
        }
        if (tokenId == currentTokenHeadId) {
          classes.push("highlight")
        }
      }
      return classes
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
