<template>
  <div id="details-view" v-if="data">
    <table class="table mb-5">
      <tbody>
        <tr>
          <td v-for="(header, index) in columnHeaders" :key="`tr-header-${index}`">
            <th>{{ header }}</th>
          </td>
        </tr>
        <tr v-for="(token, tIndex) in sentences[1]" :key="`tr-token-${tIndex}`">
          <td v-for="(column, cIndex) in columnHeaders" :key="`td-${tIndex}-${cIndex}`">
            <span v-if="column == 'head'" v-html="headToken(token)"> </span>
            <span
              v-else
              :class="textClasses(column, tIndex)"
              v-html="token[cIndex]"
            ></span>    
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style>
.table-box {
  overflow: auto;
}
</style>

<script>
export default {
  name: "ResultsDetailsTableView",
  props: ["data", "sentences", "corpora"],
  data() {
    return {
      columnHeaders: this.calcColumnHeaders()
    }
  },
  methods: {
    headToken(tokenData) {
      let token = "-"
      let headIndex = this.columnHeaders.indexOf("head")
      let lemmaIndex = this.columnHeaders.indexOf("lemma")
      let startId = this.sentences[0]
      if (headIndex && lemmaIndex) {
        let tokenId = tokenData[headIndex];
        if (tokenId) {
          token = this.sentences[1][tokenId - startId][lemmaIndex]
        }
      }
      return token;
    },
    calcColumnHeaders() {
      let partitions = this.corpora.corpus.partitions
        ? this.corpora.corpus.partitions.values
        : [];
      let columns = this.corpora.corpus["mapping"]["layer"][this.corpora.corpus["segment"]];
      if (partitions.length) {
        columns = columns["partitions"][partitions[0]];
      }
      return columns["prepared"]["columnHeaders"];
    },
    textClasses(item, index) {
      let classes = []
      if (item.indexOf('pos') > -1) {
        classes.push('badge rounded-pill')
        classes.push('bg-secondary')
      }
      if (item.indexOf('form') > -1) {
        let startId = this.sentences[0]
        let selectedStartId = this.data[1]
        let selectedEndId = this.data.at(-1)
        if ((startId + index) >= selectedStartId && (startId + index) <= selectedEndId) {
          classes.push('text-bold')
        }
      }
      return classes
    },
  },
};
</script>
