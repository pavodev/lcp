<template>
  <div id="details-view" v-if="data">
    <table class="table mb-5">
      <tbody>
        <tr>
          <td v-for="(header, index) in columnHeaders" :key="`tr-header-${index}`">
            <th>{{ header }}</th>
          </td>
        </tr>
        <tr v-for="(token, tIndex) in sentences[1]" :key="`tr-token-${tIndex}`" :class="rowClasses(tIndex)">
          <td v-for="(column, cIndex) in columnHeaders" :key="`td-${tIndex}-${cIndex}`">
            <span v-if="column == 'head'" v-html="headToken(token, tIndex)"> </span>
            <span
              v-else
              :class="textClasses(column)"
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
    headToken(tokenData, tIndex) {
      let token = "- ROOT -"
      let headIndex = this.columnHeaders.indexOf("head")
      let lemmaIndex = this.columnHeaders.indexOf("lemma")
      let startId = this.sentences[0]
      if (headIndex && lemmaIndex) {
        let tokenId = tokenData[headIndex];
        if (tokenId) {
          token = this.sentences[1][tokenId - startId][lemmaIndex]
          let difference = tokenId - startId - tIndex;
          let arrow = "↓", tag="sub";
          if (difference<0) {
            arrow = "↑";
            tag = "sup";
            difference = Math.abs(difference);
          }
          token += ` <${tag}>${arrow}${difference}</${tag}>`;
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
      return columns["prepared"]["columnHeaders"].filter( (column) => column!="spaceAfter" );
    },
    textClasses(item) {
      let classes = [];
      if (item.indexOf('pos') > -1 || item.indexOf('label') > -1) {
        // classes.push('badge rounded-pill')
        classes.push('badge')
        classes.push('bg-secondary')
      }
      return classes
    },
    rowClasses(tIndex) {
      let classes = [];
      let startId = this.sentences[0];
      let tokenId = startId + tIndex;
      let group = this.data[1].findIndex(v => v instanceof Array ? v.includes(tokenId) : v == tokenId);
      if (group >= 0) classes.push(`tr-color-group-${group}`);
      return classes
    },
  },
};
</script>
