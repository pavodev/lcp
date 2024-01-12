<template>
  <div id="details-view" v-if="data">
    <table class="table mb-5" :class="isModal ? 'modal-table' : ''">
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
              v-else-if="typeof(token[cIndex]) in {string:1,number:1}"
              :class="textClasses(column)"
              v-html="token[cIndex]"
            ></span>
            <span
              v-else
              :class="objectClasses(token[cIndex])"
              v-html="objectColumn(token[cIndex])"
            > </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style>
.modal {
  width: unset !important;
  max-width: calc(100vw - 2em);
  left: 50vw;
  transform: translateX(-50%);
}
.modal-content {
  padding-left: 1em;
  padding-right: 1em;
}
.table-box {
  overflow: auto;
}
.modal-table.table {
  width: auto;
}
.object-column {
  display: block;
  height: 1.5em;
  overflow-y: hidden;
}
.object-column button {
  float: right;
  margin-top: -0.25em;
}
.object-column button::before {
  content: "▶";
}
.object-column pre {
  display: block;
  margin-top: -1.25em;
}
.object-column.unfolded {
  height: unset;
  overflow-y: visible;
}
.object-column.unfolded button::before {
  content: "▼";
}
.object-column.unfolded pre {
  margin-top: 0;
}
</style>

<script>
export default {
  name: "ResultsDetailsTableView",
  props: ["data", "sentences", "corpora", "isModal"],
  data() {
    return {
      columnHeaders: this.calcColumnHeaders()
    }
  },
  methods: {
    headToken(tokenData, tIndex) {
      let token = ""
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
    objectClasses(content) {
      if (content)
        return ['object-column'];
      else
        return [''];
    },
    objectColumn(content) {
      if (content)
        return `<button onclick="this.parentNode.classList.toggle('unfolded')"> </button>
          <pre>${JSON.stringify(content,null,2).replace(/\n/g,'<br>')}</pre>`;
      else
        return '';
    }
  },
};
</script>
