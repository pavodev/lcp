<template>
  <div class="home">
    <div class="container">
      <div class="row mt-4">
        <div class="col">
          <Title :title="'Welcome'" />
        </div>
        <div class="col mt-1 text-end">
          <button
            type="button"
            class="btn btn-secondary btn-sm"
            data-bs-toggle="modal"
            data-bs-target="#newProjectModal"
          >
            <FontAwesomeIcon :icon="['fas', 'circle-plus']" class="me-1" />
            Add new project
          </button>
        </div>
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
            <span v-if="index != -1">
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
                class="btn btn-secondary btn-sm"
                @click="APIKeyCreate(project.id)"
                v-else
              >
                <FontAwesomeIcon :icon="['fas', 'circle-plus']" class="me-1" />
                Create API Key
              </button>
            </span>
            <p>Corpora:</p>
            <div class="row mt-2">
              <div
                class="col-4 mb-3"
                v-for="corpus in project.corpora"
                :key="corpus.id"
                @click="openCorpus(corpus)"
                data-bs-toggle="modal"
                data-bs-target="#corpusDetailsModal"
              >
                <div class="corpus-block">
                  <p class="title mb-0">{{ corpus.meta.name }}</p>
                  <p class="author mb-0" v-if="corpus.meta.author">
                    by {{ corpus.meta.author }}
                  </p>
                  <p class="description mt-3">
                    {{ corpus.meta.corpusDescription }}
                  </p>
                  <p class="word-count mb-0">
                    Word count:
                    <b>{{
                      nFormatter(calculateSum(Object.values(corpus.token_counts)))
                    }}</b>
                  </p>
                  <p class="word-count">
                    Version: <b>{{ corpus.meta.version }}</b>
                  </p>
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
            <h5 class="modal-title" id="newProjectModalLabel">
              New Project
            </h5>
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
                <vue3-mermaid
                  v-if="showGraph"
                  :nodes="graphData"
                  type="graph TD"
                  :config="config"
                  :key="graphIndex"
                ></vue3-mermaid>
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
import Utils from "@/utils";

export default {
  name: "HomeView",
  data() {
    return {
      corpusModal: null,
      graphIndex: 0,
      showGraph: false,
      config: {
        theme: "neutral",
      },
      allowProjectModalSave: false,
      modalProjectData: null,
    };
  },
  components: {
    Title,
    ProjectNewView,
  },
  methods: {
    openCorpus(corpus) {
      this.corpusModal = corpus;
    },
    calculateSum(array) {
      return array.reduce((accumulator, value) => {
        return accumulator + value;
      }, 0);
    },
    nFormatter: Utils.nFormatter,
    async APIKeyRevoke(projectId, apiKeyId) {
      let retval = await useProjectStore().revokeApiKey(projectId, apiKeyId)
      if (retval.result == "ok") {
        useUserStore().fetchUserData();
        useNotificationStore().add({
          type: "success",
          text: "The API key is successfully revoked"
        });
      }
    },
    async APIKeyCreate(projectId) {
      let retval = await useProjectStore().createApiKey(projectId)
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
      let retval = await useProjectStore().create(this.modalProjectData)
      if (retval) {
        useUserStore().fetchUserData();
        useNotificationStore().add({
          type: "success",
          text: `The project is successfully created`,
        });
      }
    },
  },
  computed: {
    ...mapState(useCorpusStore, ["queryData", "corpora"]),
    ...mapState(useUserStore, ["projects"]),
    projectsGroups() {
      let retval = {
        "-1": {
          id: null,
          title: "No project",
          corpora: [],
        }
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
    },
    graphData() {
      let corpus = this.corpusModal;
      let data = [
        {
          id: "1",
          text: corpus.meta.name.replace(/\(/gi, "").replace(/\)/gi, ""),
          next: Object.keys(corpus.layer).map(
            (layer) => `l-${layer.toLowerCase().replace(/@/gi, "")}`
          ),
        },
      ];
      Object.keys(corpus.layer).forEach((layer, index) => {
        let next = [];
        if ("attributes" in corpus.layer[layer]) {
          Object.keys(corpus.layer[layer].attributes).forEach((attribute) => {
            let attributeId = `a-${index}-${attribute.toLowerCase()}`;
            data.push({
              id: attributeId,
              text: attribute.replace(/@/gi, ""),
              edgeType: "circle",
            });
            next.push(attributeId);
          });
        }
        if ("meta" in corpus.layer[layer]) {
          Object.keys(corpus.layer[layer].meta).forEach((meta) => {
            let metaId = `a-${index}-${meta.toLowerCase()}`;
            data.push({
              id: metaId,
              text: meta.replace(/@/gi, ""),
              edgeType: "circle",
            });
            next.push(metaId);
          });
        }
        data.push({
          id: `l-${layer.toLowerCase().replace(/@/gi, "")}`,
          text: layer.replace(/@/gi, ""),
          next: next,
        });
      });
      return data;
    },
  },
  mounted() {
    this.$refs.vuemodal.addEventListener("shown.bs.modal", () => {
      this.showGraph = true;
    });
    this.$refs.vuemodal.addEventListener("hide.bs.modal", () => {
      this.showGraph = false;
    });
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
</style>
