<template>
  <div id="corpus-metadata-edit">
    <div class="row">
      <div class="col-6">
        <div class="mb-3">
          <label for="corpus-name" class="form-label">Name</label>
          <input type="text" class="form-control" v-model="corpusData.meta.name" id="corpus-name" maxlength="50" />
        </div>
      </div>
      <div class="col-6">
        <div class="mb-3">
          <label for="corpus-source" class="form-label">Source</label>
          <input type="text" class="form-control" v-model="corpusData.meta.source" id="corpus-source" />
        </div>
      </div>
    </div>
    <div class="row">
      <div class="col-12">
        <div class="mb-3">
          <label for="corpus-authors" class="form-label">Authors</label>
          <input type="text" class="form-control" v-model="corpusData.meta.authors" id="corpus-authors" />
        </div>
      </div>
    </div>
    <div class="row">
      <div class="col-6">
        <div class="mb-3">
          <label for="corpus-institution" class="form-label">Provider/Institution</label>
          <input type="text" class="form-control" v-model="corpusData.meta.institution" id="corpus-institution" />
        </div>
      </div>
      <div class="col-6">
        <div class="mb-3">
          <label for="corpus-version" class="form-label">Version</label>
          <input type="text" class="form-control" v-model="corpusData.meta.version" id="corpus-version" />
        </div>
      </div>
    </div>
    <div class="row">
      <div class="col-12">
        <div class="mb-3">
          <label for="corpus-description" class="form-label">Description</label>
          <textarea class="form-control" placeholder="Corpora description" v-model="corpusData.meta.corpusDescription"
            id="corpus-description" style="height: 100px"></textarea>
        </div>
      </div>
    </div>
    <div class="row">
      <div class="col-6">
        <div class="mb-3">
          <label for="corpus-license" class="form-label">License</label>
          <div class="form-check" v-for="licence in licenses" :key="licence.name">
            <input
              class="form-check-input"
              type="radio"
              v-model="corpusData.meta.license"
              :id="licence.tag"
              :value="licence.tag"
              :selected="corpusData.meta.license === licence.tag"
            >
            <label class="form-check-label" :for="licence.tag">
              <img :src="`/licenses/${licence.tag}.png`" :alt="licence.name" class="license-img" />
              <a :href="licence.url" target="_blank">{{ licence.name }}</a>
            </label>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.license-img {
  height: 30px;
}
a {
  margin-left: 10px;
  text-decoration: none;
  color: #2a7f62;
  transition: all 0.3s;
}
a:hover {
  opacity: 0.8;
}
</style>

<script>

export default {
  name: "CorpusMetdataEdit",
  props: ["corpus"],
  data() {
    return {
      licenses: [
        {tag: "cc-by", name: "CC-BY", url: "https://creativecommons.org/licenses/by/4.0/"},
        {tag: "cc-by-sa", name: "CC-BY-SA", url: "https://creativecommons.org/licenses/by-sa/4.0/"},
        {tag: "cc-by-nc", name: "CC-BY-NC", url: "https://creativecommons.org/licenses/by-nc/4.0/"},
        {tag: "cc-by-nc-sa", name: "CC-BY-NC-SA", url: "https://creativecommons.org/licenses/by-nc-sa/4.0/"},
        {tag: "cc-by-nd", name: "CC-BY-ND", url: "https://creativecommons.org/licenses/by-nd/4.0/"},
        {tag: "cc-by-nc-nd", name: "CC-BY-NC-ND", url: "https://creativecommons.org/licenses/by-nc-nd/4.0/"},
        {tag: "cc-zero", name: "CC-0", url: "https://creativecommons.org/publicdomain/zero/1.0/"}
      ],
      corpusData: { ...this.corpus },
    }
  },
}
</script>
