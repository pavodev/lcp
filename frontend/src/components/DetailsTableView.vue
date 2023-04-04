<template>
  <div id="details-view" v-if="data">
    <table class="table mb-5">
      <tbody>
        <tr v-for="(item, index) in columnHeaders" :key="`tr-${index}`">
          <th>{{ item }}</th>
          <td v-for="(token, tIndex) in data[3]" :key="`t${index}-${tIndex}`">
            <span v-if="item == 'head'" v-html="headToken(token)"> </span>
            <span
              v-else
              :class="textClasses(item, tIndex)"
              v-html="token[index]"
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
  name: "DetailsTableView",
  props: ["data", "corpora"],
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
      let startId = this.data[2]
      if (headIndex && lemmaIndex) {
        let tokenId = tokenData[headIndex];
        if (tokenId) {
          token = this.data[3][tokenId - startId][lemmaIndex];
        }
      }
      return token;
    },
    calcColumnHeaders() {
      let partitions = this.corpora.corpus.partitions
        ? this.corpora.corpus.partitions.values
        : [];
      let columns = this.corpora.corpus["mapping"]["layer"]["Segment"];
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
        let startId = this.data[2]
        let selectedStartId = this.data[1][0]
        let selectedEndId = this.data[1][1]
        if ((startId + index) >= selectedStartId && (startId + index) <= selectedEndId) {
          classes.push('text-bold')
        }
      }
      return classes
    },
  },
};
</script>
