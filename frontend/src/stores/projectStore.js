import { defineStore } from "pinia";
import httpApi from "@/httpApi";


export const useProjectStore = defineStore("projectData", {
  state: () => ({
  }),
  getters: {},
  actions: {
    async createApiKey(projectId) {
      let url = `/project/${projectId}/api/create`
      let response = await httpApi.post(url)
      this.queryData = await response.data;
      return this.queryData
    },
    async revokeApiKey(projectId, apiKeyId) {
      let url = `/project/${projectId}/api/${apiKeyId}/revoke`
      let response = await httpApi.post(url)
      this.queryData = await response.data;
      return this.queryData
    },
    async create(data) {
      let url = `/project`
      let response = await httpApi.post(url, data)
      this.queryData = await response.data;
      return this.queryData
    },
    async update(data) {
      let url = `/project/${data.id}`
      let response = await httpApi.post(url, data)
      this.queryData = await response.data;
      return this.queryData
    },
  },
});
