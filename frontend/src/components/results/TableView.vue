<template>
  <div id="kwic-view">
    <table class="table" v-if="data">
      <thead>
        <tr>
          <th scope="col" v-for="(col, index) in attributes" :key="index">
            <input
              type="text"
              v-model="filters[index]"
              v-if="col.type != 'aggregrate'"
              class="form-control form-control-sm"
              :placeholder="`Filter by ${col.name}`"
            >
          </th>
        </tr>
        <tr>
          <th scope="col" v-for="(col, index) in attributes" :key="index" @click="sortChange(index)" :class="col.class">
            {{ col.name }}
            <span v-if="index == sortBy">
              <FontAwesomeIcon :icon="['fas', 'arrow-up']" v-if="sortDirection == 0" />
              <FontAwesomeIcon :icon="['fas', 'arrow-down']" v-else />
            </span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(item, resultIndex) in filteredData"
          :key="resultIndex"
          :data-index="resultIndex"
        >
          <td
            scope="row"
            v-for="(col, index) in attributes"
            :key="index"
            :class="col.class"
          >
            {{ item[index] }}<template v-if="col.textSuffix">{{ col.textSuffix }}</template>
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

<style scoped>
.header-form {
  text-align: center;
}
.header-left,
.text-right {
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
  props: ["data", "attributes", "corpora", "resultsPerPage", "loading", "type"],
  data() {
    let { attributes, data } = this.improvedAttrbutesData()
    return {
      popoverY: 0,
      popoverX: 0,
      currentToken: null,
      currentIndex: null,
      modalVisible: false,
      modalIndex: null,
      currentPage: 1,
      sortBy: attributes.length - 1,
      sortDirection: 1,
      filters: attributes.map(() => ''),
      additionalColumData: [],
      calcData: data,
      calcAttributes: attributes,
    };
  },
  components: {
    PaginationComponent,
  },
  methods: {
    improvedAttrbutesData() {
      // Add relative frequency to analysis
      let attributes = this.attributes
      let data = this.data
      if (this.type == "analysis" && this.attributes.at(-1).name == "frequency") {
        attributes.push({
          name: "relative frequency",
          type: "aggregrate",
          textSuffix: " %",
        })
        let sum = data.reduce((accumulator, row) => {
          return accumulator + row.at(-1)
        }, 0);
        data = this.data.map(row => [
          ...row,
          (row.at(-1)/sum*100.).toFixed(3)
        ])
      }
      else if (this.type == "collocation") {
        attributes.push(...[{
          name: "mi3",
          type: "aggregrate",
          class: "text-right",
        }, {
          name: "mi",
          type: "aggregrate",
          class: "text-right",
        }, {
          name: "lmi",
          type: "aggregrate",
          class: "text-right",
        }, {
          name: "tscore",
          type: "aggregrate",
          class: "text-right",
        }, {
          name: "zscore",
          type: "aggregrate",
          class: "text-right",
        }])
        data = this.data.map(row => [
          ...row,
          Math.log2(Math.pow(row[1], 3)/row[2]).toFixed(3),
          Math.log2(row[1]/row[2]).toFixed(3),
          (row[1]*Math.log2(row[1]/row[2])).toFixed(3),
          ((row[1] - row[2]) / Math.sqrt(row[1])).toFixed(3),
          ((row[1] - row[2]) / Math.sqrt(row[2])).toFixed(3)
        ])
      }
      return { attributes, data }
    },
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
    sortChange(index) {
      if (this.sortBy == index) {
        this.sortDirection = this.sortDirection == 0 ? 1 : 0
      }
      else {
        this.sortBy = index
        this.sortDirection = 0
      }
    }
  },
  computed: {
    // headToken() {
    //   let token = "-";
    //   let headIndex = this.columnHeaders.indexOf("head");
    //   let lemmaIndex = this.columnHeaders.indexOf("lemma");
    //   if (headIndex) {
    //     let tokenId = this.currentToken[headIndex];
    //     if (tokenId) {
    //       let startId = this.data[this.currentIndex][2];
    //       let tokenIndexInList = tokenId - startId;
    //       token = this.data[this.currentIndex][3][tokenIndexInList][lemmaIndex];
    //     }
    //   }
    //   return token;
    // },
    columnHeaders() {
      let partitions = this.corpora.corpus.partitions
        ? this.corpora.corpus.partitions.values
        : [];
      let columns = this.corpora.corpus["mapping"]["layer"][this.corpora.corpus["segment"]];
      if (partitions.length) {
        columns = columns["partitions"][partitions[0]];
      }
      return columns["prepared"]["columnHeaders"];
    },
    filteredData() {
      let filtered = this.calcData.filter(row => {
        let res = true
        row.forEach((data, index) => {
          if (this.filters[index] && !data.toString().toLowerCase().includes(this.filters[index].toLowerCase())){
            res = false
          }
        })
        return res
      })
      filtered.sort((a, b) => {
        let retval = 0
        if (a[this.sortBy] > b[this.sortBy]) {
          retval = this.sortDirection == 0 ? 1 : -1
        }
        if (a[this.sortBy] < b[this.sortBy]) {
          retval = this.sortDirection == 0 ? -1 : 1
        }
        return retval
      })
      return filtered
    },
  },
};
</script>
