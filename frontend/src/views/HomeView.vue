<template>
  <div class="home">
    <div class="container">
      <div class="row mt-4">
        <div class="col">
          <Title :title="`Welcome to ${appName}`" />
        </div>
        <!-- <div class="col mt-1 text-end">
          <button
            type="button"
            class="btn btn-secondary btn-sm"
            data-bs-toggle="modal"
            data-bs-target="#newProjectModal"
          >
            <FontAwesomeIcon :icon="['fas', 'circle-plus']" class="me-1" />
            Add new project
          </button>
        </div> -->
      </div>
    </div>
    <div class="container mt-4 text-start">
      <div class="row">
        <nav>
          <div class="nav nav-tabs" id="nav-tab" role="tablist">
            <button
              v-for="(project, index) in projectsGroups"
              :key="project.id"
              class="nav-link"
              :class="index == -1 ? 'active' : ''"
              :id="`nav-${project.id}-tab`"
              data-bs-toggle="tab"
              :data-bs-target="`#nav-${project.id}`"
              type="button"
              role="tab"
              :aria-controls="`nav-${project.id}`"
              aria-selected="true"
              @click="corporaFilter = ''"
            >
              {{ project.title }}
              <span class="api-badge">({{ project.corpora.length }})</span>
              <span class="ms-1 api-badge" v-if="project.api">[API]</span>
            </button>
          </div>
        </nav>
        <div class="tab-content pt-3" id="nav-tabContent">
          <div
            v-for="(project, index) in projectsGroups"
            :key="project.id"
            class="tab-pane fade"
            :class="index == -1 ? 'active show' : ''"
            :id="`nav-${project.id}`"
            role="tabpanel"
            aria-labelledby="nav-results-tab"
          >
            <div class="row">
              <div class="col">
                <div class="input-group mb-3">
                  <span class="input-group-text" id="basic-addon1">
                    <FontAwesomeIcon :icon="['fas', 'magnifying-glass']" />
                  </span>
                  <input
                    type="text"
                    class="form-control"
                    v-model="corporaFilter"
                    placeholder="Search corpora"
                  />
                </div>
                <div v-if="corporaFilter && filterError && filterError.message" class="alert notification alert-danger">
                  {{ filterError.message }}
                </div>
              </div>
              <div v-if="index != -1" class="col-2 text-end">
                <span v-if="project.api">
                  <p class="mb-0">API Key: {{ project.api.key }}</p>
                  <p class="">Secret Key: {{ project.api.secretPart }}</p>
                  <button
                    type="button"
                    class="btn btn-secondary btn-sm mb-3"
                    @click="APIKeyRevoke(project.id, project.api.id)"
                  >
                    <FontAwesomeIcon :icon="['fas', 'trash']" class="me-1" />
                    Revoke API Key
                  </button>
                </span>
                <button
                  type="button"
                  class="btn btn-light"
                  @click="APIKeyCreate(project.id)"
                  v-else
                >
                  <FontAwesomeIcon
                    :icon="['fas', 'circle-plus']"
                    class="me-1"
                  />
                  Create API Key
                </button>
              </div>
            </div>
            <div class="row mt-2">
              <div
                class="col-4 mb-3"
                v-for="corpus in filterCorpora(project.corpora)"
                :key="corpus.id"
                @click="openCorpus(corpus)"
              >
                <div class="corpus-block">
                  <p class="title mb-0">{{ corpus.meta.name }}</p>
                  <p class="author mb-0">
                    <span v-if="corpus.meta.author"
                      >by {{ corpus.meta.author }}</span
                    >
                  </p>
                  <p class="description mt-3">
                    {{ corpus.meta.corpusDescription }}
                  </p>
                  <p class="word-count mb-0">
                    Word count:
                    <b>{{
                      nFormatter(
                        calculateSum(Object.values(corpus.token_counts))
                      )
                    }}</b>
                  </p>
                  <p class="word-count mb-0">
                    Version: <b>{{ corpus.meta.version }}</b>
                  </p>
                  <p class="word-count" v-if="corpus.partitions">
                    <span
                      class="badge text-bg-primary me-1"
                      v-for="language in corpus.partitions.values"
                      v-html="language.toUpperCase()"
                      :key="`${corpus.id}-${language}`"
                    />
                  </p>
                  <div
                    class="details-button icon-1 tooltips"
                    title="Query corpus"
                    @click.stop="openQueryWithCorpus(corpus)"
                  >
                    <FontAwesomeIcon
                      :icon="['fas', 'magnifying-glass-chart']"
                    />
                  </div>
                  <a
                    class="details-button icon-2 tooltips"
                    :href="corpus.meta.url"
                    title="Corpus webpage"
                    :disabled="!corpus.meta.url"
                    target="_blank"
                    @click.stop
                  >
                    <FontAwesomeIcon :icon="['fas', 'link']" />
                  </a>
                  <div
                    class="details-button icon-3 tooltips"
                    title="Corpus details"
                  >
                    <FontAwesomeIcon :icon="['fas', 'circle-info']" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <div
      class="modal fade"
      id="newProjectModal"
      tabindex="-1"
      aria-labelledby="newProjectModalLabel"
      aria-hidden="true"
      ref="vuemodal"
    >
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="newProjectModalLabel">New Project</h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body text-start">
            <ProjectNewView @updated="updateProjectModalData" />
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              Close
            </button>
            <button
              type="button"
              class="btn btn-primary"
              data-bs-dismiss="modal"
              @click="saveModalProject"
              :disabled="!allowProjectModalSave"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
    <div
      class="modal fade"
      id="corpusDetailsModal"
      tabindex="-1"
      aria-labelledby="corpusDetailsModalLabel"
      aria-hidden="true"
      ref="vuemodal"
    >
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="corpusDetailsModalLabel">
              Corpus details
            </h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body text-start" v-if="corpusModal">
            <div class="row">
              <div class="col-5">
                <p class="title mb-0">{{ corpusModal.meta.name }}</p>
                <p class="author mb-0" v-if="corpusModal.meta.author">
                  by {{ corpusModal.meta.author }}
                </p>
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
                  Version: {{ corpusModal.meta.version }}
                </p>
                <p class="word-count mb-0">
                  URL:
                  <a :href="corpusModal.meta.url" target="_blank">{{
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
                  <div
                    class=""
                    v-for="partition in corpusModal.partitions.values"
                    :key="partition"
                  >
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
                <CorpusGraphView :corpus="corpusModal" v-if="showGraph" />
              </div>
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

<script>
import { mapState } from "pinia";
import { useCorpusStore } from "@/stores/corpusStore";
import { useProjectStore } from "@/stores/projectStore";
import { useUserStore } from "@/stores/userStore";
import { useNotificationStore } from "@/stores/notificationStore";

import Title from "@/components/TitleComponent.vue";
import ProjectNewView from "@/components/project/NewView.vue";
import CorpusGraphView from "@/components/CorpusGraphView.vue";
import router from "@/router";
import Utils from "@/utils";
import config from "@/config";
import { setTooltips, removeTooltips } from "@/tooltips";
import { Modal } from "bootstrap";

// import { Tooltip } from "bootstrap";

export default {
  name: "HomeView",
  data() {
    return {
      corpusModal: null,
      showGraph: false,
      allowProjectModalSave: false,
      modalProjectData: null,
      appName: config.appName,
      // tooltips: [],
      corporaFilter: "",
      filterError: null
    };
  },
  components: {
    Title,
    ProjectNewView,
    CorpusGraphView
  },
  methods: {
    filterCorpora(corpora) {
      if (this.corporaFilter) {
        let rgx = null;
        // use a try/catch statement to test the regex
        try { rgx = new RegExp(this.corporaFilter, "i"); }
        catch (e) {
          if (!this.filterError || this.filterError.pattern != this.corporaFilter) {
            this.filterError = {pattern: this.corporaFilter};
            setTimeout(()=>{
              if (!this.filterError) return;
              this.filterError.message = `Invalid search pattern (${e.message})`;
            }, 1000); // allow 1s for the user to correct/complete the pattern
          }
        }
        if (rgx) {
          corpora = corpora.filter(
            (c) =>
              c.meta.name.search(rgx) > -1 ||
              c.meta.author.search(rgx) > -1
          );
          this.filterError = null;
        }
      }

      function compare(a, b) {
        if (a.meta.name < b.meta.name){
          return -1;
        }
        if (a.meta.name > b.meta.name){
          return 1;
        }
        return 0;
      }
      corpora = corpora.sort(compare)
      return corpora;
    },
    openCorpus(corpus) {
      this.corpusModal = corpus;
      let modal = new Modal(document.getElementById('corpusDetailsModal'));
      modal.show()
    },
    openQueryWithCorpus(corpus) {
      if (config.appType == "vian") {
        router.push(`/player/${corpus.meta.id}/${corpus.shortname}`);
      } else {
        router.push(`/query/${corpus.meta.id}/${corpus.shortname}`);
      }
    },
    calculateSum(array) {
      return array.reduce((accumulator, value) => {
        return accumulator + value;
      }, 0);
    },
    nFormatter: Utils.nFormatter,
    async APIKeyRevoke(projectId, apiKeyId) {
      let retval = await useProjectStore().revokeApiKey(projectId, apiKeyId);
      if (retval.result == "ok") {
        useUserStore().fetchUserData();
        useNotificationStore().add({
          type: "success",
          text: "The API key is successfully revoked",
        });
      }
    },
    async APIKeyCreate(projectId) {
      let retval = await useProjectStore().createApiKey(projectId);
      if (retval.result == "ok") {
        useUserStore().fetchUserData();
        useNotificationStore().add({
          type: "success",
          text: `The API key is successfully created. Safely store your secret key. It will be shown just this time: <b>${retval.api.secret}</b>`,
          timeout: 120,
        });
      }
    },
    updateProjectModalData(valid, data) {
      this.allowProjectModalSave = valid;
      this.modalProjectData = data;
    },
    async saveModalProject() {
      let retval = await useProjectStore().create(this.modalProjectData);
      if (retval) {
        useUserStore().fetchUserData();
        useNotificationStore().add({
          type: "success",
          text: `The project is successfully created`,
        });
      }
    },
    // setTooltips() {
    //   this.removeTooltips();tooltip
    //   const tooltipTriggerList = Array.from(
    //     document.querySelectorAll(".tooltips")
    //   );
    //   tooltipTriggerList.forEach((tooltipTriggerEl) => {
    //     let tooltipInstance = new Tooltip(tooltipTriggerEl);
    //     this.tooltips.push(tooltipInstance);
    //   });
    // },
    // removeTooltips() {
    //   this.tooltips.forEach((tooltipInstance) => {
    //     tooltipInstance.dispose();
    //   });
    //   this.tooltips = [];
    // },
  },
  computed: {
    ...mapState(useCorpusStore, ["queryData", "corpora"]),
    ...mapState(useUserStore, ["projects"]),
    projectsGroups() {
      let retval = {
        "-1": {
          id: null,
          title: "Public",
          corpora: [],
        },
      };
      let projectIds = [];
      this.projects.forEach((project) => {
        projectIds.push(project.id);
        retval[project.id] = {
          ...project,
          corpora: [],
        };
      });
      this.corpora.forEach((corpus) => {
        let project_id =
          corpus.project && projectIds.includes(corpus.project)
            ? corpus.project
            : -1;
        retval[project_id].corpora.push(corpus);
      });
      return retval;
    }
  },
  mounted() {
    this.$refs.vuemodal.addEventListener("shown.bs.modal", () => {
      this.showGraph = true;
    });
    this.$refs.vuemodal.addEventListener("hide.bs.modal", () => {
      this.showGraph = false;
    });
    // this.setTooltips();
    setTooltips();
  },
  updated() {
    // this.setTooltips();
    setTooltips();
  },
  beforeUnmount() {
    // this.removeTooltips();
    removeTooltips();
  },
};
</script>

<style scoped>
.corpus-block {
  border: 1px solid #d4d4d4;
  border-radius: 5px;
  padding: 20px;
  cursor: pointer;
  position: relative;
  height: 233px;
}
.author {
  font-size: 70%;
  height: 10px;
}
.corpus-block:hover {
  background-color: #f9f9f9;
}
.title {
  font-size: 110%;
  font-weight: bold;
}
.description {
  font-size: 90%;
  height: 70px;
  overflow: hidden;
}
.word-count {
  font-size: 80%;
}
.project-box {
  border: 1px solid #f2f2f2;
  border-radius: 3px;
}
.project-title {
  font-size: 14px;
  margin-top: 7px;
}
.api-badge {
  font-size: 80%;
  font-weight: bold;
}
.details-button {
  position: absolute;
  bottom: 10px;
  /* background-color: #2a7f62;
  padding: 3px 10px;
  border-radius: 4px;
  color: #fff; */
  color: #2a7f62;
  opacity: 0.9;
}
details-button:disabled {
  filter: grayscale(100);
  opacity: 0.5;
}
.corpus-block:hover .details-button {
  opacity: 1;
}
.details-button:hover {
  opacity: 0.7 !important;
}
.details-button.icon-1 {
  right: 0;
  bottom: 0;
  background-color: #2a7f62;
  padding: 15px 10px 10px 15px;
  color: #fff;
  border-radius: 40px 0 0;
}
.details-button.icon-2 {
  right: 55px;
}
.details-button.icon-3 {
  right: 90px;
}
</style>
