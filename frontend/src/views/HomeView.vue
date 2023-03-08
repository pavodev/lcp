<template>
  <div class="home">
    <Title :title="'Welcome to UpLORD'" />
    <div class="container mt-4 text-start">
      <div class="row">
        <!-- <p>Select corpora to query:</p> -->
        <div
          class="col-4"
          v-for="corpus in corpora"
          :key="corpus.id"
          @click="openCorpus(corpus)"
        >
          <div class="corpus-block">
            <p class="title mb-0">{{ corpus.meta.name }}</p>
            <p class="author mb-0" v-if="corpus.meta.author">by {{ corpus.meta.author }}</p>
            <p class="description mt-3">{{ corpus.meta.corpusDescription }}</p>
            <p class="word-count">Word count: <b>{{ corpus.token_counts }}</b></p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Title from "@/components/TitleComponent.vue";
import { mapState } from "pinia";
import { useCorpusStore } from "@/stores/corpusStore";

export default {
  name: "HomeView",
  components: {
    Title,
  },
  methods: {
    openCorpus(corpus) {
      console.log("Corpus", corpus);
    }
  },
  computed: {
    ...mapState(useCorpusStore, ["queryData", "corpora"]),
  },
};
</script>

<style scoped>
.corpus-block {
  border: 1px solid #d4d4d4;
  border-radius: 5px;
  padding: 20px;
  cursor: pointer;
}
.author {
  font-size: 70%;
}
.corpus-block:hover {
  background-color: #f3f3f3;
}
.title {
  font-size: 110%;
  font-weight: bold;
}
.description {
  font-size: 90%;
}
.word-count {
  font-size: 80%;
}
</style>
