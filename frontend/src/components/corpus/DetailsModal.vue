<template>
  <div class="row" id="corpus-details-modal">
    <div class="col-5">
      <div class="title mb-0" v-if="hasAccessToCorpus(corpusModal, userData)">
        <span>{{ corpusModal.meta.name }}</span>
        <div class="icon-1 btn btn-primary btn-sm horizontal-space" title="Query corpus"
          @click="openQueryWithCorpus(corpusModal, 'catchphrase')" data-bs-dismiss="modal">
          <FontAwesomeIcon :icon="['fas', 'magnifying-glass-chart']" />
        </div>
      </div>
      <!-- <p class="author mb-0" v-if="corpusModal.meta.author">
        {{ corpusModal.meta.author }}
      </p> -->
      <p class="description mt-3">
        {{ corpusModal.meta.corpusDescription }}
      </p>
      <p class="word-count mb-0">
        Word count:
        <b>{{
          calculateSum(
            Object.values(corpusModal.token_counts)
          ).toLocaleString("de-DE")
        }}</b>
      </p>
      <p class="word-count mb-0">
        Revison: {{ corpusModal.meta.revision }}
      </p>
      <p class="word-count mb-0">
        URL:
        <a :href="getURLWithProtocol(corpusModal.meta.url)" target="_blank">{{
          corpusModal.meta.url
        }}</a>
      </p>
      <p class="word-count mb-0">
        Description: {{ corpusModal.description }}
      </p>
      <span v-if="corpusModal.partitions">
        <p class="word-count" v-if="corpusModal.partitions">
          Partitions: {{ corpusModal.partitions.values.join(", ") }}
        </p>
        <div class="" v-for="partition in corpusModal.partitions.values" :key="partition">
          <p class="text-bold">{{ partition.toUpperCase() }}</p>
          <p class="word-count">
            Segments:
            {{
              corpusModal.mapping.layer.Segment.partitions[
                partition
              ].prepared.columnHeaders.join(", ")
            }}
          </p>
          <!-- <p class="word-count">
            Segments:
            {{ corpusModal.mapping.layer.Segment.partitions[partition].prepared.columnHeaders.join(", ") }}
          </p> -->
        </div>
      </span>
    </div>
    <div class="col-7">
      <CorpusGraphViewNew :corpus="corpusModal" />
    </div>
  </div>
</template>

<style>
  .description {
    font-size: 90%;
    height: 108px;
    overflow: hidden;
  }

  .word-count {
    font-size: 80%;
  }
</style>

<script>
  import CorpusGraphViewNew from "@/components/CorpusGraphViewNew.vue";
  import { useUserStore } from "@/stores/userStore";
  import { mapState } from "pinia";

  import Utils from "@/utils";

  export default {
    name: "CorpusDetailsModal",
    props: ["corpusModal"],
    methods: {
      getURLWithProtocol: Utils.getURLWithProtocol,
      hasAccessToCorpus: Utils.hasAccessToCorpus,
      calculateSum: Utils.calculateSum,
    },
    computed: {
      ...mapState(useUserStore, ["userData"]),
    },
    components: {
      CorpusGraphViewNew,
    },
  }
</script>
