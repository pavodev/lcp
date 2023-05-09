<template>
  <div id="kwic-view">
    <table class="table" v-if="data">
      <thead>
        <tr>
          <template
            v-for="(group, groupIndex) in groups"
            :key="`thead-${groupIndex}`"
          >
            <th scope="col" class="header-left">
              {{ groupIndex == 0 ? "Left context" : "Context" }}
            </th>
            <th scope="col" class="header-form">Form</th>
          </template>
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
          <template
            v-for="(group, groupIndex) in groups"
            :key="`tbody-${groupIndex}`"
          >
            <td scope="row" :class="groupIndex == 0 ? 'left-context' : ''">
              <span
                class="token"
                v-for="(token, index) in item[groupIndex*2]"
                :key="`lt-${index}`"
                :data-id="item[groups.length - 1]"
                :class="bgCheck(resultIndex, index, item, groupIndex, 1, token)"
                @mousemove="showPopover(token, resultIndex, $event)"
                @mouseleave="closePopover"
              >
                {{ token[0] }}
              </span>
            </td>
            <td scope="row" class="match-context text-bold">
              <span
                class="token"
                v-for="(token, index) in item[groupIndex*2 + 1]"
                :key="`lt-${index}`"
                :data-id="item[groups.length - 1]"
                :class="bgCheck(resultIndex, index, item, groupIndex, 2, token)"
                @mousemove="showPopover(token, resultIndex, $event)"
                @mouseleave="closePopover"
              >
                {{ token[0] }}
              </span>
            </td>
          </template>
          <!-- :class="bgCheck(resultIndex, index, item, groups.length - 1)"
          @mousemove="showPopover(token, resultIndex, $event)" -->
          <td scope="row" class="right-context">
            <span
              class="token"
              v-for="(token, index) in item[groups.length*2]"
              :key="`lt-${index}`"
              :class="bgCheck(resultIndex, index, item, groups.length - 1, 3, token)"
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
    ------
    <!-- <table class="table" v-if="data">
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
              :data-id="item[3]"
              :class="bgCheck(resultIndex, index, item[2], 1)"
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
              :data-id="item[3]"
              :class="bgCheck(resultIndex, index, item[2], 2)"
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
              :class="bgCheck(resultIndex, index, item[2], 3)"
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
    </table> -->
    <PaginationComponent
      v-if="data"
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

<style>
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
  padding-left: 2px;
  padding-right: 2px;
  display: inline-block;
  transition: 0.3s all;
  border-radius: 2px;
}
.token:hover {
  background-color: #2a7f62;
  color: #fff;
  cursor: pointer;
}
.highlight {
  background-color: #1e999967;
}
</style>

<script>
import ResultsDetailsModalView from "@/components/results/DetailsModalView.vue";
import PaginationComponent from "@/components/PaginationComponent.vue";

export default {
  name: "ResultsKWICView",
  props: [
    "data",
    "sentences",
    "attributes",
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
      modalVisible: false,
      modalIndex: null,
      currentPage: 1,
      groups: this.getGroups(this.data[0]),
    };
  },
  components: {
    ResultsDetailsModalView,
    PaginationComponent,
  },
  methods: {
    getGroups(data) {
      let groups = [];
      let tmpGroup = [];
      let tokenData = JSON.parse(JSON.stringify(data));
      tokenData = tokenData.splice(1, tokenData.length);
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
      this.currentResultIndex = resultIndex + (this.currentPage - 1) * this.resultsPerPage;
    },
    closePopover() {
      this.currentToken = null;
      this.currentResultIndex = null;
    },
    showModal(index) {
      this.modalIndex = index + (this.currentPage - 1) * this.resultsPerPage;
      this.modalVisible = true;
    },
    updatePage(currentPage) {
      this.currentPage = currentPage;
      this.$emit("updatePage", this.currentPage);
    },
    bgCheck(resultIndex, tokenIndex, range, groupIndex, type, token) {
      let classes = [];
      resultIndex = resultIndex + (this.currentPage - 1) * this.resultsPerPage;
      if (this.currentResultIndex == resultIndex && this.currentToken) {
        let headIndex = this.columnHeaders.indexOf("head");
        let currentTokenHeadId = this.currentToken[headIndex];
        // let startId = this.data[this.currentResultIndex][1];
        let sentenceId = this.data[this.currentResultIndex][0];
        let startId = this.sentences[sentenceId][0];
        // let tokenId = range[range.length - 1][groupIndex][0] + tokenIndex + startId - 6;
        // if (type == 1) {
        //   tokenId = range[0] - tokenIndex + startId - 1;
        // } else if (type == 2) {
        //   tokenId = range[0] + tokenIndex + startId;
        // } else if (type == 3) {
        //   tokenId = range[1] + tokenIndex + startId + 1;
        // }
        let indexToCurrentToken = tokenIndex + startId;
        if (type == 1) {
          indexToCurrentToken += range[range.length - 1][groupIndex].length
          if (groupIndex > 0) {
            indexToCurrentToken += range[range.length - 1][groupIndex - 1].at(-1)
          }
        }
        else if (type == 2) {
          indexToCurrentToken += range[range.length - 1][groupIndex].at(-1)
        }
        else if (type == 3) {
          indexToCurrentToken += range[range.length - 1][groupIndex].at(-1) + 1
        }
        console.log("E", resultIndex, tokenIndex, groupIndex, type, indexToCurrentToken, startId, token)
        // console.log("R", this.currentToken)
        // if (groupIndex > 0) {
        //   console.log("W", indexToCurrentToken, currentTokenHeadId, range[range.length - 1], groupIndex, tokenIndex, type)
        // }
        // groupIndex;
        // let indexToCurrentToken = range[range.length - 1][groupIndex][0];
        // console.log("T", currentTokenHeadId, tokenId, range[range.length - 1], tokenIndex, startId, this.currentResultIndex, resultIndex)
        // console.log("R", resultIndex, this.currentIndex, headIndex, currentTokenHeadId, tokenId, tokenIndex, groupIndex, range[range.length - 1][groupIndex])
        if (indexToCurrentToken == currentTokenHeadId) {
          classes.push("highlight");
        }
      }
      return classes;
    },
    // bgCheck1(resultIndex, tokenIndex, range, groupIndex, token) {
    //   this.currentToken = token;
    //   this.currentResultIndex = resultIndex + (this.currentPage - 1) * this.resultsPerPage;

    //   let classes = [];
    //   resultIndex = resultIndex + (this.currentPage - 1) * this.resultsPerPage;
    //   if (this.currentResultIndex == resultIndex && this.currentToken) {
    //     let headIndex = this.columnHeaders.indexOf("head");
    //     let currentTokenHeadId = this.currentToken[headIndex];
    //     let startId = this.data[this.currentResultIndex][1];
    //     let tokenId = range[range.length - 1][groupIndex][0] + tokenIndex + startId - 6;
    //     // if (type == 1) {
    //     //   tokenId = range[0] - tokenIndex + startId - 1;
    //     // } else if (type == 2) {
    //     //   tokenId = range[0] + tokenIndex + startId;
    //     // } else if (type == 3) {
    //     //   tokenId = range[1] + tokenIndex + startId + 1;
    //     // }
    //     // groupIndex;
    //     let indexToCurrentToken = range[range.length - 1][groupIndex][0] + tokenIndex + groupIndex + startId - 6;
    //     if (groupIndex > 0) {
    //       console.log("W", indexToCurrentToken, currentTokenHeadId, range[range.length - 1], groupIndex, tokenIndex)
    //     }
    //     // console.log("T", currentTokenHeadId, tokenId, range[range.length - 1], tokenIndex, startId, this.currentResultIndex, resultIndex, indexToCurrentToken)
    //     // console.log("R", resultIndex, this.currentIndex, headIndex, currentTokenHeadId, tokenId, tokenIndex, groupIndex, range[range.length - 1][groupIndex])
    //     if (tokenId == currentTokenHeadId) {
    //       classes.push("highlight");
    //     }
    //   }
    //   return classes;
    // },
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
      return this.data
        .filter((row, rowIndex) => {
          let start = this.resultsPerPage * (this.currentPage - 1);
          let end = start + this.resultsPerPage;
          return rowIndex >= start && rowIndex < end;
        })
        .map((row) => {
          let sentenceId = row[0];
          let startIndex = this.sentences[sentenceId][0];
          let tokens = this.sentences[sentenceId][1];
          let tokenData = this.getGroups(row)
          let range = tokenData.map(tokensArr => tokensArr.map(tokenId => tokenId - startIndex))

          let retval = [
            // Before first
            tokens.filter((_, index) => index < range[0][0]).reverse()
          ];

          for (let index=0; index < range.length; index++){
            retval.push(
              tokens.filter(
                (_, tokenIndex) =>
                  tokenIndex >= range[index][0] &&
                  tokenIndex <= range[index].at(-1)
              )
            );
            // Context between forms
            if ((index + 1) < range.length) {
              retval.push(
                  tokens.filter(
                  (_, tokenIndex) =>
                    tokenIndex > range[index].at(-1) &&
                    tokenIndex < range[index + 1][0]
                )
              )
            }
          }

          // After last form
          retval.push(tokens.filter((_, index) => index > range.at(-1).at(-1)));
          retval.push(range);
          console.log("R", retval, startIndex)
          return retval
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
