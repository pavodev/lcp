<template>
  <div id="plain-table-view">
    <PaginationComponent
      v-if="data"
      class="paggination"
      :resultCount="data.length"
      :resultsPerPage="resultsPerPage"
      :currentPage="currentPage"
      @update="updatePage"
      :key="data.length"
      :loading="loading"
    />
    <table class="table" v-if="data">
      <!-- <thead>
        <tr>
          <th scope="col" style="width: 100%">Result</th>
          <th scope="col">-</th>
        </tr>
      </thead> -->
      <tbody>
        <tr
          v-for="(item, resultIndex) in results"
          :key="resultIndex"
          :data-index="resultIndex"
        >
          <button @click="copyToClip(item)">
            <FontAwesomeIcon :icon="['fas', 'copy']" />
          </button>
          <td scope="row">
            <span
              v-if="Object.keys(meta)"
              style="margin-right: 0.5em"
              @mousemove="showMeta(resultIndex, $event)"
              @mouseleave="closeMeta"
            >
              <FontAwesomeIcon :icon="['fas', 'circle-info']" />
            </span>
            <span
              v-for="(token) in item"
              :key="`form-${token.index}`"
              @mousemove="showPopover(token.token, resultIndex, $event)"
              @mouseleave="closePopover"
            >
              <span class="token" :class="[
                (currentToken && columnHeaders && currentToken[columnHeaders.indexOf('head')] == token.index ? 'highlight' : ''),
                (token.group >= 0 ? `text-bold color-group-${token.group}` : '')
              ]">{{ token.form }}</span>
              <span class="space" v-if="token.spaceAfter !== 0">&nbsp;</span>
            </span>
            <!-- <template
              v-for="(group, groupIndex) in groups"
              :key="`tbody-${groupIndex}`"
            >
              <span
                class="token"
                v-for="(token, tokenIndex) in item[groupIndex * 2]"
                :key="`rc-${tokenIndex}`"
                :class="bgCheck(resultIndex, groupIndex, tokenIndex, item, 1)"
                @mousemove="showPopover(token, resultIndex, $event)"
                @mouseleave="closePopover"
              >
                {{ token[0] }}
              </span>
              <span
                class="token"
                v-for="(token, tokenIndex) in item[groupIndex * 2 + 1]"
                :key="`form-${tokenIndex}`"
                :class="bgCheck(resultIndex, groupIndex, tokenIndex, item, 2)"
                @mousemove="showPopover(token, resultIndex, $event)"
                @mouseleave="closePopover"
              >
                {{ token[0] }}
              </span>
            </template>
            <span
              class="token"
              v-for="(token, tokenIndex) in item[groups.length * 2]"
              :key="`lt-${tokenIndex}`"
              :class="
                bgCheck(resultIndex, groups.length - 1, tokenIndex, item, 3)
              "
              @mousemove="showPopover(token, resultIndex, $event)"
              @mouseleave="closePopover"
            >
              {{ token[0] }}
            </span> -->
          </td>
          <td>
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              data-bs-toggle="modal"
              :data-bs-target="`#detailsModal${randInt}`"
              @click="showModal(resultIndex)"
            >
              Details
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <PaginationComponent
      v-if="data"
      class="paggination"
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
      <table class="table popover-table">
        <thead>
          <tr>
            <th v-for="(item, index) in columnHeaders.filter(ch=>ch!= 'spaceAfter')" :key="`th-${index}`">
              {{ item }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td v-for="(item, index) in columnHeaders.filter(ch=>ch!= 'spaceAfter')" :key="`tr-${index}`">
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
      class="popover-liri"
      v-if="currentMeta"
      :style="{top: popoverY + 'px', left: popoverX + 'px' }"
    >
      <table class="table popover-table">
        <thead>
          <tr>
            <th v-for="(_, layer) in currentMeta" :key="`th-${layer}`">
              {{ layer }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td v-for="(meta, layer) in currentMeta" :key="`tr-${layer}-value`">
              <span
                v-html="Object.entries(meta).map( ([name,value])=>`<strong>${name}:</strong> ${value}` ).join('<br>')"
              >
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div
      class="modal fade"
      :id="`detailsModal${randInt}`"
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
              <ResultsDetailsModalView
                :data="data[modalIndex]"
                :sentences="sentences[data[modalIndex][0]]"
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

<style scoped>
.paggination {
  float: right;
}
.paggination:after {
  clear: both;
  content: "";
}
.header-form {
  text-align: center;
}
.popover-table th {
  text-transform: uppercase;
  font-size: 10px;
}
.popover-table {
  margin-bottom: 0;
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
.middle-context {
  /* white-space: nowrap;
  overflow: visible;
  max-width: 0;
  width: 10%; */
  text-align: center;
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
  padding: 2px;
  border: #cbcbcb 1px solid;
  border-radius: 5px;
  z-index: 200;
}
.match-context {
  white-space: nowrap;
  text-align: center;
}
.token {
  /* padding-left: 2px;
  padding-right: 2px; */
  display: inline-block;
  transition: 0.3s all;
  border-radius: 2px;
}
.token:hover {
  background-color: #2a7f62;
  color: #fff;
  cursor: pointer;
}
.token.nospace {
  padding-right: 0px;
  margin-right: -2px; /* compensate for next token's padding-left */
}
.highlight {
  background-color: #1e999967 !important;
  color: #000 !important;
}
*[class^="color-group-"] {
  border-radius: 2px;
}
</style>

<script>
import ResultsDetailsModalView from "@/components/results/DetailsModalView.vue";
import PaginationComponent from "@/components/PaginationComponent.vue";
import { useNotificationStore } from "@/stores/notificationStore";
import Utils from "@/utils.js";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

class TokenToDisplay {
  constructor(tokenArray, index, groups, columnHeaders) {
    if (!(tokenArray instanceof Array) || tokenArray.length < 2)
      throw Error(`Invalid format for token ${JSON.stringify(tokenArray)}`);
    if (isNaN(Number(index)) || index<=0)
      throw Error(`Invalid index (${index}) for token ${JSON.stringify(tokenArray)}`);
    if (!(groups instanceof Array) || groups.find(g=>!(g instanceof Array)))
      throw Error(`Invalid groups (${JSON.stringify(groups)}) for token ${JSON.stringify(tokenArray)}`);
    columnHeaders.forEach( (header,i) => this[header] = tokenArray[i] );
    this.token = tokenArray;
    this.index = index;
    this.group = groups.findIndex( g => g.find(id=>id==index) );
  }
}

export default {
  name: "ResultsPlainTableView",
  emits: ["updatePage"],
  props: [
    "data",
    "sentences",
    "attributes",
    "meta",
    "corpora",
    "resultsPerPage",
    "loading",
  ],
  data() {
    return {
      popoverY: 0,
      popoverX: 0,
      currentToken: null,
      currentResultIndex: null,
      currentMeta: null,
      modalVisible: false,
      modalIndex: null,
      currentPage: 1,
      groups: this.data ? this.getGroups(this.data[0], true) : [],
      randInt: Math.floor(Math.random() * 1000)
    };
  },
  components: {
    ResultsDetailsModalView,
    PaginationComponent,
    FontAwesomeIcon
},
  methods: {
    // getGroups1(data) {
    //   let groups = [];
    //   let tmpGroup = [];
    //   let tokenData = JSON.parse(JSON.stringify(data));
    //   tokenData = tokenData.splice(1, tokenData.length)[0];
    //   tokenData.forEach((tokenId, idx) => {
    //     if (idx > 0 && Math.abs(tokenData[idx] - tokenData[idx - 1]) > 1) {
    //       if (tmpGroup.length > 0) {
    //         groups.push(tmpGroup.sort());
    //       }
    //       tmpGroup = [];
    //     }
    //     tmpGroup.push(tokenId);
    //   });
    //   groups.push(tmpGroup.sort());
    //   return groups;
    // },
    getGroups(data, initial=false) {
      let groups = [];
      let tmpGroup = [];
      let tokenData = JSON.parse(JSON.stringify(data));
      tokenData = tokenData.splice(1, tokenData.length).sort();
      if (initial === true) {
        tokenData = tokenData[0]
      }
      tokenData.forEach((tokenId, idx) => {
        if (idx > 0 && Math.abs(tokenData[idx] - tokenData[idx - 1]) > 1) {
          if (tmpGroup.length > 0) {
            groups.push(tmpGroup.sort());
          }
          tmpGroup = [];
        }
        tmpGroup.push(tokenId);
      });
      groups.push(tmpGroup.sort());
      return groups;
    },
    showPopover(token, resultIndex, event) {
      this.popoverY = event.clientY + 10;
      this.popoverX = event.clientX + 10;
      this.currentToken = token;
      this.currentResultIndex =
        resultIndex + (this.currentPage - 1) * this.resultsPerPage;
    },
    closePopover() {
      this.currentToken = null;
      this.currentResultIndex = null;
    },
    showMeta(resultIndex, event) {
      this.closePopover();
      resultIndex =
        resultIndex + (this.currentPage - 1) * this.resultsPerPage;
      const sentenceId = this.data[resultIndex][0];
      this.currentMeta = this.meta[sentenceId];
      this.popoverY = event.clientY + 10;
      this.popoverX = event.clientX + 10;
    },
    closeMeta() {
      this.currentMeta = null;
    },
    showModal(index) {
      this.modalIndex = index + (this.currentPage - 1) * this.resultsPerPage;
      this.modalVisible = true;
    },
    updatePage(currentPage) {
      this.currentPage = currentPage;
      this.$emit("updatePage", this.currentPage);
    },
    bgCheck(resultIndex, groupIndex, tokenIndexInResultset, range, type) {
      let classes = [];

      if (type == 2) {
        classes.push('text-bold')
        classes.push(`color-group-${groupIndex}`)
      }

      if (this.currentResultIndex == resultIndex && this.currentToken) {
        // Because of pages
        resultIndex =
          resultIndex + (this.currentPage - 1) * this.resultsPerPage;

        let sentenceId = this.data[resultIndex][0];
        let startId = this.sentences[sentenceId][0];
        let currentTokenId = 0;
        let groupStartIndex = 0;

        // Left context of resultset
        if (type == 1) {
          // Beacuse of reverse
          // if (range[groupIndex].length >= tokenIndexInResultset) {
          //   tokenIndexInResultset = range[groupIndex].length - tokenIndexInResultset - 1
          // }
          if (groupIndex > 0) {
            groupStartIndex = range[range.length - 1][groupIndex - 1].at(-1) + 1;
          }
        } else if (type == 3) {
          groupStartIndex = range[range.length - 1].at(-1).at(-1) + 1;
        } else if (type == 2) {
          groupStartIndex = range[range.length - 1][groupIndex][0];
        }

        currentTokenId = groupStartIndex + tokenIndexInResultset;
        classes.push(`TR-${currentTokenId}-L${groupStartIndex}`)

        currentTokenId = startId + groupStartIndex + tokenIndexInResultset;

        let headIndex = this.columnHeaders.indexOf("head");
        let currentTokenHeadId = this.currentToken[headIndex];
        if (currentTokenId == currentTokenHeadId) {
          classes.push("highlight");
        }
      }
      return classes;
    },
    copyToClip(item) {
      Utils.copyToClip(item);
      useNotificationStore().add({
        type: "success",
        text: "Copied to clipboard",
      });
    }
  },
  computed: {
    headToken() {
      let token = "-";
      let headIndex = this.columnHeaders.indexOf("head");
      let lemmaIndex = this.columnHeaders.indexOf("lemma");
      if (headIndex) {
        let tokenId = this.currentToken[headIndex];
        if (tokenId) {
          let sentenceId = this.data[this.currentResultIndex][0];
          let startId = this.sentences[sentenceId][0];
          let tokenIndexInList = tokenId - startId;
          token = this.sentences[sentenceId][1][tokenIndexInList][lemmaIndex];
        }
      }
      return token;
    },
    results() {
      let start = this.resultsPerPage * (this.currentPage - 1);
      let end = start + this.resultsPerPage;
      return this.data
        .filter((row, rowIndex) => {
          let sentenceId = row[0];
          return rowIndex >= start && rowIndex < end && this.sentences[sentenceId];
        })
        .map((row) => {
          let sentenceId = row[0];
          let startIndex = this.sentences[sentenceId][0];
          let tokens = this.sentences[sentenceId][1];

          let tokenData = JSON.parse(JSON.stringify(row[1])); // tokens are already gouped in sets/sequences
          tokenData = tokenData.map( tokenIdOrSet => tokenIdOrSet instanceof Array ? tokenIdOrSet : [tokenIdOrSet] );
          // Return a list of TokenToDisplay instances
          tokens = tokens.map( (token,idx) => new TokenToDisplay(token, startIndex + idx, tokenData, this.columnHeaders) );

          return tokens;
          // let range = tokenData.map( (tokensArr) =>
          //   tokensArr.map( (tokenId) => tokenId - startIndex )
          // );

          // let retval = [
          //   // Before first match
          //   // Revert when in table
          //   // tokens.filter((_, index) => index < range[0][0]).reverse(),
          //   tokens.filter((_, index) => index < range[0][0])
          // ];

          // for (let index = 0; index < range.length; index++) {
          //   retval.push(
          //     tokens.filter(
          //       (_, tokenIndex) =>
          //         tokenIndex >= range[index][0] &&
          //         tokenIndex <= range[index].at(-1)
          //     )
          //   );
          //   // Context between forms
          //   if (index + 1 < range.length) {
          //     retval.push(
          //       tokens.filter(
          //         (_, tokenIndex) =>
          //           tokenIndex > range[index].at(-1) &&
          //           tokenIndex < range[index + 1][0]
          //       )
          //     );
          //   }
          // }

          // // After last form
          // retval.push(tokens.filter((_, index) => index > range.at(-1).at(-1)));
          // retval.push(range);
          // return retval;
        });
    },
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
  },
};
</script>
