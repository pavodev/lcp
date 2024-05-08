<template>
  <div id="kwic-view">
    <table class="table" v-if="data">
      <thead>
        <tr>
          <th scope="col" v-for="(col, index) in calcAttributes" :key="index">
            <input
              type="text"
              v-model="filters[index]"
              class="form-control form-control-sm"
              :class="filterErrors[index] ? 'is-invalid' : ''"
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
            :class="[(col.class||''), (item[index] < this.roundBelow ? 'round' : '')]"
          >
            {{ col.valueType=="float" ? this.round(item[index]) : item[index] }}
            <template v-if="col.textSuffix">{{ col.textSuffix }}</template>
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
td.round {
  visibility: hidden;
}
td.round::after {
  content: '< 0.001';
  display: block;
  float: right;
  visibility: visible;
}
td.round:hover {
  visibility: visible;
}
td.round:hover::after {
  display: none;
}
</style>

<script>
import PaginationComponent from "@/components/PaginationComponent.vue";

export default {
  name: "ResultsTableView",
  props: ["data", "languages", "attributes", "corpora", "resultsPerPage", "loading", "type"],
  data() {
    let attributes = this.getImpovedAttibutes(this.attributes)
    let data = this.calculateAdditionalData(this.data)
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
      filterErrors: attributes.map(() => false),
      additionalColumData: [],
      calcData: data,
      calcAttributes: attributes,
      roundBelow: 0.001
    };
  },
  components: {
    PaginationComponent,
  },
  methods: {
    calculateAdditionalData(data) {
      if (this.data && this.attributes) {
        data = JSON.parse(JSON.stringify(this.data));
        if (this.type == "analysis") {
          let sum = data.reduce((accumulator, row) => {
            return accumulator + row.at(-1)
          }, 0);
          data = this.data.map(row => [
            ...row,
            (row.at(-1)/sum*100.).toFixed(4)
          ])
        }
        else if (this.type == "collocation") {
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
          ]);
        }
      }
      return data
    },
    getImpovedAttibutes(attributes) {
      // Add relative frequency to analysis
      if (this.attributes) {
        attributes = JSON.parse(JSON.stringify(this.attributes));
        if (this.type == "analysis") {
          attributes.at(-1)["valueType"] = "float"
          attributes.at(-1)["class"] = "text-right"
          attributes.push({
            name: "relative frequency",
            type: "aggregate",
            textSuffix: " %",
            class: "text-right",
            valueType: "float",
          })
        }
        else if (this.type == "collocation") {
          attributes[1]["valueType"] = "float"
          attributes[1]["class"] = "text-right"
          attributes[2]["valueType"] = "float"
          attributes[2]["class"] = "text-right"
          attributes.push(...[{
            name: "O/E",
            type: "aggregate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "MI",
            type: "aggregate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "MI³",
            type: "aggregate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "local-MI",
            type: "aggregate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "t-score",
            type: "aggregate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "z-score",
            type: "aggregate",
            class: "text-right",
            valueType: "float",
          }, {
            name: "simple-ll",
            type: "aggregate",
            class: "text-right",
            valueType: "float",
          }]);
        }
      }
      return attributes
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
        this.sortDirection = 1
      }
    },
    round(float) {
      if (float < this.roundBelow)
        return Number.parseFloat(float).toExponential(2);
      else
        return Math.round(1000*float) / 1000;
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

      let matchFilters = []
      this.filters.forEach((filter, index) => {
        let matchCoparator = filter.match(/^\s*(=|<|>|>=|<=|!=).*$/);
        let isRegExField = this.calcAttributes[index].valueType == "float"  // For now just float
        let match = filter.match(/^\s*(=|<|>|>=|<=|!=)\s*(-?\d+(\.\d+)?)\s*$/);
        matchFilters.push(match ? match : null)
        this.filterErrors[index] = (!match && isRegExField && matchCoparator && filter.length > 0) ? true : false
      })

      let filtered = this.calcData.filter(row => {
        let res = true
        row.forEach((data, index) => {
          let filter = null;
          if (this.calcAttributes[index].valueType == "float") {
            let match = matchFilters[index];
            if (match) {
              filter = v=>{
                let comp = [];
                if (match[1].includes("=")) comp.push(this.round(Number(v)) == Number(match[2]));
                if (match[1].includes(">")) comp.push(this.round(Number(v)) > Number(match[2]));
                if (match[1].includes("<")) comp.push(this.round(Number(v)) < Number(match[2]));
                if (match[1].startsWith("!"))
                  return !comp.reduce((x,y)=>x||y,false);
                else
                  return comp.reduce((x,y)=>x||y,false);
              };
            }
          }
          else {
            filter = v => v.toString().toLowerCase().includes(this.filters[index].toLowerCase());
          }
          // if (filter && (!data || !data.toString().toLowerCase().includes(this.filters[index].toLowerCase()))){
          if (filter && (!data || !filter(data.toString().toLowerCase()))) {
            res = false
          }
        })
        return res
      })
      let castFunction = (value) => (value||"").toString()
      if (this.sortBy && this.calcAttributes[this.sortBy] && this.calcAttributes[this.sortBy].valueType == "float"){
        castFunction = (value) => parseFloat(value||NaN)
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
  watch: {
    data(newValue) {
      this.calcData = this.calculateAdditionalData(newValue)
    },
    attributes(newValue) {
      let attributes = this.getImpovedAttibutes(newValue)
      this.calcAttributes = attributes
      this.sortBy = attributes.length - 1
      this.filters = attributes.map(() => '')
    },
  }
};
</script>
