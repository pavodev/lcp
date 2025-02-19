<template>
  <div id="result-details-view">
    <nav>
      <div class="nav nav-tabs" id="nav-tab" role="tablist">
        <button
          class="nav-link active"
          id="nav-dependency-tab"
          data-bs-toggle="tab"
          data-bs-target="#nav-dependency"
          type="button"
          role="tab"
          aria-controls="nav-dependency"
          aria-selected="true"
          v-if="hasDepRel"
        >
          {{ $t('modal-results-tab-graph') }}
        </button>
        <button
          class="nav-link"
          :class="hasDepRel ? '' : 'active'"
          id="nav-details-tab"
          data-bs-toggle="tab"
          data-bs-target="#nav-details"
          type="button"
          role="tab"
          aria-controls="nav-details"
          aria-selected="false"
        >
          {{ $t('modal-results-tab-tabular') }}
        </button>
      </div>
    </nav>
    <div class="tab-content" id="nav-tabContent">
      <div
        class="tab-pane fade show active"
        id="nav-dependency"
        role="tabpanel"
        aria-labelledby="nav-dependency-tab"
        v-if="hasDepRel"
      >
        <DepRelView :data="data" :sentences="sentences" :columnHeaders="columnHeaders" />
      </div>
      <div
        class="tab-pane fade"
        :class="hasDepRel ? '' : 'active show'"
        id="nav-details"
        role="tabpanel"
        aria-labelledby="nav-details-tab"
      >
        <DetailsTableView :data="data" :sentences="sentences" :columnHeaders="columnHeaders" :corpora="corpora" :isModal="true" />
      </div>
    </div>
  </div>
</template>

<style scoped>
#nav-dependency,
#nav-details {
  overflow: auto;
}
</style>

<script>
import DepRelView from "@/components/DepRelView.vue";
import DetailsTableView from "@/components/results/DetailsTableView.vue";

export default {
  name: "ResultsDetailsModalView",
  props: ["data", "sentences", "languages", "corpora"],
  data() {
    let lang = (this.languages||[])[0];
    let segment = this.corpora.corpus.segment;
    let mapping = this.corpora.corpus.mapping.layer[segment];
    if (lang && "partitions" in mapping) {
      mapping = mapping.partitions[lang]
    }
    let columnHeaders = mapping.prepared.columnHeaders;
    let deprel = Object.values(columnHeaders).indexOf("head") >= 0;
    return {
      hasDepRel: deprel,
      columnHeaders: columnHeaders
    }
  },
  components: {
    DepRelView,
    DetailsTableView,
  },
}
</script>
