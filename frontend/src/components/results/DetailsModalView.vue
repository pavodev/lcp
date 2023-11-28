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
          Dependency Graph
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
          Tabular
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
        <DepRelView :data="data" :sentences="sentences" />
      </div>
      <div
        class="tab-pane fade"
        :class="hasDepRel ? '' : 'active show'"
        id="nav-details"
        role="tabpanel"
        aria-labelledby="nav-details-tab"
      >
        <DetailsTableView :data="data" :sentences="sentences" :corpora="corpora" :isModal="true" />
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
  props: ["data", "sentences", "corpora"],
  data() {
    let deprel = false;
    for (let i in this.sentences[1]){
      let token = this.sentences[1][i]
      if (token[4]) {
        deprel = true
        break;
      }
    }
    return {
      hasDepRel: deprel,
    }
  },
  components: {
    DepRelView,
    DetailsTableView,
  },
}
</script>
