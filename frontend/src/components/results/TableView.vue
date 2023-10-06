<template>
  <div id="kwic-view">
    <table class="table" v-if="data">
      <thead>
        <tr>
          <th scope="col" v-for="(col, index) in calcAttributes" :key="index">
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
          <th scope="col" v-for="(col, index) in calcAttributes" :key="index" @click="sortChange(index)" :class="col.class">
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
            v-for="(col, index) in calcAttributes"
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
      if (this.data && this.attributes) {
        attributes = JSON.parse(JSON.stringify(this.attributes));
        data = JSON.parse(JSON.stringify(this.data));
        if (this.type == "analysis") {
          attributes.at(-1)["valueType"] = "float"
          attributes.at(-1)["class"] = "text-right"
          attributes.push({
            name: "relative frequency",
            type: "aggregrate",
            textSuffix: " %",
            class: "text-right",
            valueType: "float",
          })
          let sum = data.reduce((accumulator, row) => {
            return accumulator + row.at(-1)
          }, 0);
          data = this.data.map(row => [
            ...row,
            (row.at(-1)/sum*100.).toFixed(4)
          ])
        }
        else if (this.type == "collocation") {
          attributes[1]["valueType"] = "float"
          attributes[1]["class"] = "text-right"
          attributes[2]["valueType"] = "float"
          attributes[2]["class"] = "text-right"
          attributes.push(...[{
            name: "O/E",
            type: "aggregrate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "MI",
            type: "aggregrate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "MI³",
            type: "aggregrate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "local-MI",
            type: "aggregrate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "t-score",
            type: "aggregrate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "z-score",
            type: "aggregrate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "simple-ll",
            type: "aggregrate",
            class: "text-right",
            valueType: "float",
          }])
          // row[1] = O
          // row[2] = E
          data = this.data.map(row => [
            ...row,
            (row[1]/row[2]).toFixed(4),  // O/E
            Math.log2(row[1]/row[2]).toFixed(4),  // MI
            Math.log2(Math.pow(row[1], 3)/row[2]).toFixed(4),  // MI³
            (row[1]*Math.log2(row[1]/row[2])).toFixed(4),  // local-MI
            ((row[1] - row[2]) / Math.sqrt(row[1])).toFixed(4),  // t-score
            ((row[1] - row[2]) / Math.sqrt(row[2])).toFixed(4),  // z-score
            (2*(row[1]*Math.log(row[1]/row[2]) - (row[1] - row[2]))).toFixed(4),
          ])
        }
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
      let start = this.resultsPerPage * (this.currentPage - 1);
      let end = start + this.resultsPerPage;

      let filtered = this.calcData.filter(row => {
        let res = true
        row.forEach((data, index) => {
          if (this.filters[index] && !data.toString().toLowerCase().includes(this.filters[index].toLowerCase())){
            res = false
          }
        })
        return res
      })
      let castFunction = (value) => value.toString()
      if (this.sortBy && this.calcAttributes[this.sortBy] && this.calcAttributes[this.sortBy].valueType == "float"){
        castFunction = (value) => parseFloat(value)
      }
      filtered.sort((a, b) => {
        let retval = 0
        let _a = castFunction(a[this.sortBy])
        let _b = castFunction(b[this.sortBy])
        if (_a > _b) {
          retval = this.sortDirection == 0 ? 1 : -1
        }
        if (_a < _b) {
          retval = this.sortDirection == 0 ? -1 : 1
        }
        return retval
      })

      return filtered.filter((row, rowIndex) => rowIndex >= start && rowIndex < end)
    },
  },
};
</script>
