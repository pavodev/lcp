<template>
  <div id="pagination-view">
    <nav>
      <ul class="pagination">
        <li class="page-item" :class="currentPage <= 1 ? 'disabled' : ''">
          <button class="page-link" @click="previousPage">Previous</button>
        </li>
        <li
          class="page-item"
          v-for="pageNumber in pages"
          :key="`page-${pageNumber}`"
        >
          <button
            class="page-link"
            @click="setPage(pageNumber + 1)"
            :class="pageNumber + 1 == currentPage ? 'active' : ''"
          >
            {{ pageNumber + 1 }}
          </button>
        </li>
        <li class="page-item loader" v-if="loading">
          <span class="page-link">
            Loading
            <svg
              xmlns="http://www.w3.org/2000/svg"
              xmlns:xlink="http://www.w3.org/1999/xlink"
              style="
                margin: auto;
                background: #fff;
                display: inline-block;
                margin-top: -2px;
              "
              width="20px"
              height="20px"
              viewBox="0 0 100 100"
              preserveAspectRatio="xMidYMid"
            >
              <circle
                cx="50"
                cy="50"
                r="38"
                stroke-width="6"
                stroke="#1e9989"
                stroke-dasharray="59.690260418206066 59.690260418206066"
                fill="none"
                stroke-linecap="round"
              >
                <animateTransform
                  attributeName="transform"
                  type="rotate"
                  repeatCount="indefinite"
                  dur="1.7543859649122806s"
                  keyTimes="0;1"
                  values="0 50 50;360 50 50"
                ></animateTransform>
              </circle>
            </svg>
          </span>
        </li>
        <li
          class="page-item"
          :class="currentPage >= maxPages ? 'disabled' : ''"
        >
          <button class="page-link" @click="nextPage">Next</button>
        </li>
      </ul>
    </nav>
  </div>
</template>

<style scoped>
.page-item.loader .page-link:hover {
  color: var(--bs-pagination-color);
  background-color: var(--bs-pagination-bg);
}
</style>>

<script>
export default {
  name: "PaginationComponent",
  props: ["resultCount", "resultsPerPage", "currentPage", "loading"],
  data() {
    return {
      currentPageTmp: this.currentPage,
      maxPages: Math.ceil(parseFloat(this.resultCount) / this.resultsPerPage),
    };
  },
  methods: {
    previousPage() {
      this.currentPageTmp -= 1;
      if (this.currentPageTmp < 1) {
        this.currentPageTmp = 1;
      }
      this.$emit("update", this.currentPageTmp);
    },
    setPage(pageNumber) {
      this.currentPageTmp = pageNumber;
      this.$emit("update", this.currentPageTmp);
    },
    nextPage() {
      this.currentPageTmp += 1;
      if (this.currentPageTmp > this.maxPages) {
        this.currentPageTmp = this.maxPages;
      }
      this.$emit("update", this.currentPageTmp);
    },
  },
  computed: {
    pages() {
      let pages = Array.from(Array(this.maxPages).keys());
      let windowSize = 3;

      let currentPage = Math.min(
        Math.max(this.currentPage - 1, 0),
        this.maxPages - 1
      );
      let start = Math.min(Math.max(currentPage - 1, 0), this.maxPages - 1);
      let end = Math.max(Math.min(currentPage + 2, this.maxPages - 1), 0);

      if (end - start < windowSize && end == this.maxPages - 1 && start > 0) {
        start = Math.max(end - windowSize + 1, 0);
      }

      if (end - start < windowSize && end < this.maxPages) {
        end = Math.min(this.maxPages, start + windowSize);
      }

      return pages.slice(start, end);
    },
  },
};
</script>
